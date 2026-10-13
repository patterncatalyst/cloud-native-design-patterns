using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Serialization;
using System.Threading.RateLimiting;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

builder.Services.AddHealthChecks();

var app = builder.Build();

var valetSecret = builder.Configuration.GetValue("VALET_SECRET", "demo-secret-do-not-use-in-prod");
var orders = new ConcurrentDictionary<string, object>();
var counter = 0;

// Per-tenant bulkhead: one concurrency limiter per tenant (System.Threading.RateLimiting), 5 permits and no queue,
// so the sixth concurrent order for a tenant is refused at once.
const int BulkheadLimit = 5;
var bulkhead = PartitionedRateLimiter.Create<string, string>(tenant =>
    RateLimitPartition.GetConcurrencyLimiter(tenant, _ => new ConcurrencyLimiterOptions
    {
        PermitLimit = BulkheadLimit,
        QueueLimit = 0,
    }));
var tenants = new ConcurrentDictionary<string, byte>();   // the limiter does not list its partitions

// Sidecar trust middleware
var openPaths = new HashSet<string> { "/healthz", "/docs", "/openapi.json" };

app.Use(async (ctx, next) =>
{
    if (openPaths.Contains(ctx.Request.Path))
    {
        await next();
        return;
    }
    var spiffe = ctx.Request.Headers["X-Forwarded-Client-Cert"].FirstOrDefault();
    if (string.IsNullOrEmpty(spiffe))
    {
        ctx.Response.StatusCode = 403;
        ctx.Response.ContentType = "application/json";
        await ctx.Response.WriteAsync("""{"detail":"no validated identity"}""");
        return;
    }
    ctx.Items["identity"] = spiffe;
    ctx.Items["subject"] = ctx.Request.Headers["X-Jwt-Claim-Sub"].FirstOrDefault() ?? "anonymous";
    await next();
});

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

app.MapPost("/orders", async (OrderRequest body, HttpContext ctx) =>
{
    tenants.TryAdd(body.Tenant, 0);
    using var lease = await bulkhead.AcquireAsync(body.Tenant);
    if (!lease.IsAcquired)   // the tenant's 5 permits are taken
        return Results.Json(new { detail = "tenant bulkhead full" }, statusCode: StatusCodes.Status429TooManyRequests);

    await Task.Delay(body.ProcessingTimeMs);   // simulated processing time
    var oid = Interlocked.Increment(ref counter).ToString();
    var order = new
    {
        id = oid,
        sku = body.Sku,
        quantity = body.Quantity,
        tenant = body.Tenant,
        identity = ctx.Items["identity"]?.ToString(),
        subject = ctx.Items["subject"]?.ToString()
    };
    orders[oid] = order;
    return Results.Json(order, statusCode: StatusCodes.Status201Created);
});

app.MapGet("/orders/{orderId}", (string orderId) =>
{
    if (orders.TryGetValue(orderId, out var order))
        return Results.Ok(order);
    return Results.NotFound(new { detail = "not found" });
});

app.MapPost("/valet-key", (HttpContext ctx) =>
{
    var resource = ctx.Request.Query["resource"].ToString();
    var operation = ctx.Request.Query["operation"].FirstOrDefault() ?? "GET";
    var expires = DateTimeOffset.UtcNow.ToUnixTimeSeconds() + 300;
    var payload = $"{resource}:{operation}:{expires}";
    var sig = ComputeHmac(valetSecret, payload);
    return Results.Ok(new { resource, operation, expires, token = sig });
});

app.MapGet("/verify-valet", (HttpContext ctx) =>
{
    var resource = ctx.Request.Query["resource"].ToString();
    var operation = ctx.Request.Query["operation"].ToString();
    var expiresStr = ctx.Request.Query["expires"].ToString();
    var token = ctx.Request.Query["token"].ToString();

    if (!long.TryParse(expiresStr, out var expires))
        return Results.Json(new { detail = "invalid expires" }, statusCode: 403);

    if (DateTimeOffset.UtcNow.ToUnixTimeSeconds() > expires)
        return Results.Json(new { detail = "expired valet key" }, statusCode: 403);

    var payload = $"{resource}:{operation}:{expires}";
    var expected = ComputeHmac(valetSecret, payload);

    if (!CryptographicOperations.FixedTimeEquals(
            Encoding.UTF8.GetBytes(token),
            Encoding.UTF8.GetBytes(expected)))
        return Results.Json(new { detail = "invalid or expired valet key" }, statusCode: 403);

    return Results.Ok(new { valid = true, resource, operation });
});

app.MapGet("/bulkhead-state", () =>
{
    var result = new Dictionary<string, object>();
    foreach (var tenant in tenants.Keys)
    {
        var available = bulkhead.GetStatistics(tenant)?.CurrentAvailablePermits ?? BulkheadLimit;
        result[tenant] = new { available, capacity = BulkheadLimit };
    }
    return result;
});

app.Run();

static string ComputeHmac(string secret, string payload)
{
    using var hmac = new HMACSHA256(Encoding.UTF8.GetBytes(secret));
    var hash = hmac.ComputeHash(Encoding.UTF8.GetBytes(payload));
    return Convert.ToHexStringLower(hash);
}

/// <summary>Inbound order. processing_ms (optional, default 10, at most 3000) simulates slow work, so the
/// per-tenant bulkhead can be seen filling up.</summary>
public record OrderRequest(
    string Sku,
    int Quantity,
    string Tenant,
    [property: JsonPropertyName("processing_ms")] int? ProcessingMs)
{
    public int ProcessingTimeMs => Math.Clamp(ProcessingMs ?? 10, 0, 3000);
}
