using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var app = builder.Build();

var valetSecret = Environment.GetEnvironmentVariable("VALET_SECRET") ?? "demo-secret-do-not-use-in-prod";
var orders = new ConcurrentDictionary<string, object>();
var counter = 0;
var bulkheadLimit = 5;
var semaphores = new ConcurrentDictionary<string, SemaphoreSlim>();

SemaphoreSlim GetTenantSem(string tenant) =>
    semaphores.GetOrAdd(tenant, _ => new SemaphoreSlim(bulkheadLimit, bulkheadLimit));

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

app.MapGet("/healthz", () => new { status = "ok" });

app.MapPost("/orders", async (HttpContext ctx) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var root = doc.RootElement;
    var sku = root.GetProperty("sku").GetString()!;
    var quantity = root.GetProperty("quantity").GetInt32();
    var tenant = root.GetProperty("tenant").GetString()!;

    var sem = GetTenantSem(tenant);
    await sem.WaitAsync();
    try
    {
        await Task.Delay(10);
        var oid = Interlocked.Increment(ref counter).ToString();
        var order = new
        {
            id = oid,
            sku,
            quantity,
            tenant,
            identity = ctx.Items["identity"]?.ToString(),
            subject = ctx.Items["subject"]?.ToString()
        };
        orders[oid] = order;
        ctx.Response.StatusCode = 201;
        return Results.Json(order, statusCode: 201);
    }
    finally
    {
        sem.Release();
    }
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
    foreach (var (tenant, sem) in semaphores)
    {
        result[tenant] = new { available = sem.CurrentCount, capacity = bulkheadLimit };
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
