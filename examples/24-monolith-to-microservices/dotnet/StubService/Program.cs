using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");
var app = builder.Build();

var serviceName = Environment.GetEnvironmentVariable("SERVICE_NAME") ?? "unknown";
var orders = new Dictionary<string, Dictionary<string, object>>();
var counter = 0;
var accessCounts = new Dictionary<string, int>();

app.MapGet("/healthz", () => new { status = "ok", source = serviceName });

app.MapPost("/orders", async (HttpContext ctx) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var root = doc.RootElement;
    var sku = root.GetProperty("sku").GetString()!;
    var quantity = root.GetProperty("quantity").GetInt32();
    var tenant = root.TryGetProperty("tenant", out var t) ? t.GetString() ?? "" : "";

    var oid = Interlocked.Increment(ref counter).ToString();
    var order = new Dictionary<string, object>
    {
        ["id"] = oid, ["sku"] = sku, ["quantity"] = quantity,
        ["tenant"] = tenant, ["source"] = serviceName
    };
    lock (orders) orders[oid] = order;
    return Results.Json(order, statusCode: 201);
});

app.MapGet("/orders/{orderId}", (string orderId) =>
{
    lock (accessCounts)
        accessCounts[orderId] = accessCounts.GetValueOrDefault(orderId) + 1;
    lock (orders)
    {
        if (orders.TryGetValue(orderId, out var order))
            return Results.Json(order);
    }
    return Results.Json(new { id = orderId, source = serviceName, status = "stub" });
});

app.MapGet("/access-count/{orderId}", (string orderId) =>
{
    lock (accessCounts)
        return Results.Json(new { order_id = orderId, count = accessCounts.GetValueOrDefault(orderId) });
});

app.Run();
