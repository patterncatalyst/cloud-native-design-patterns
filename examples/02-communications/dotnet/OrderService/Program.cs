using System.Text.Json;
using Confluent.Kafka;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Proto;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var dbUrl = builder.Configuration.GetValue("DATABASE_URL",
    "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass");
var kafkaBootstrap = builder.Configuration.GetValue("KAFKA_BOOTSTRAP", "kafka:9094");
var inventoryAddr = builder.Configuration.GetValue("INVENTORY_ADDR", "inventory:50051");

builder.Services.AddDbContext<OrdersContext>(o => o.UseNpgsql(dbUrl));

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order-service"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter(o => o.Endpoint = new Uri(
            builder.Configuration.GetValue("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318"))));

builder.Services
    .AddGraphQLServer()
    .AddQueryType<Query>();

builder.Services.AddHealthChecks();
// gRPC client factory: the channel and its HTTP/2 handler are managed like any typed HttpClient.
builder.Services.AddGrpcClient<Inventory.InventoryClient>(o => o.Address = new Uri($"http://{inventoryAddr}"))
    .ConfigurePrimaryHttpMessageHandler(() => new SocketsHttpHandler { EnableMultipleHttp2Connections = true });

var app = builder.Build();

IProducer<Null, string>? producer = null;
for (var i = 0; i < 30; i++)
{
    try
    {
        producer = new ProducerBuilder<Null, string>(
            new ProducerConfig { BootstrapServers = kafkaBootstrap }).Build();
        break;
    }
    catch { Thread.Sleep(2000); }
}

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

app.MapPost("/orders", async (HttpContext ctx, OrdersContext db, Inventory.InventoryClient inventoryClient) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var root = doc.RootElement;

    var sku = root.TryGetProperty("sku", out var skuProp) ? skuProp.GetString() ?? "" : "";
    var quantity = root.TryGetProperty("quantity", out var qtyProp) && qtyProp.ValueKind == JsonValueKind.Number
        ? qtyProp.GetInt32() : 0;

    if (string.IsNullOrEmpty(sku))
        return Results.Json(new { detail = "sku must not be empty" }, statusCode: 422);
    if (quantity <= 0)
        return Results.Json(new { detail = "quantity must be > 0" }, statusCode: 422);

    var reply = await inventoryClient.ReserveStockAsync(
        new ReserveRequest { Sku = sku, Quantity = quantity });
    var order = new Order
    {
        Id = Guid.NewGuid().ToString(),
        Sku = sku,
        Quantity = quantity,
        Status = reply.Reserved ? "confirmed" : "rejected",
    };
    db.Orders.Add(order);
    await db.SaveChangesAsync();

    var dto = OrderDto.From(order);
    if (producer is not null)
    {
        try { await producer.ProduceAsync("order.placed", new Message<Null, string> { Value = JsonSerializer.Serialize(dto) }); }
        catch { }
    }

    return Results.Json(dto, statusCode: 201);
});

app.MapGet("/orders", async (string? after, int? limit, OrdersContext db) =>
{
    var lim = limit is > 0 ? limit.Value : 50;
    var query = db.Orders.AsNoTracking();
    if (!string.IsNullOrEmpty(after))
        query = query.Where(o => o.Id.CompareTo(after) > 0);

    var orders = await query.OrderBy(o => o.Id).Take(lim).Select(o => OrderDto.From(o)).ToListAsync();
    string? nextCursor = orders.Count == lim ? orders[^1].Id : null;
    return new { items = orders, next_cursor = nextCursor };
});

app.MapGraphQL("/graphql");

app.Run();

public class Query
{
    public Task<List<OrderDto>> GetOrders(OrdersContext db, int limit = 50) =>
        db.Orders.AsNoTracking().OrderBy(o => o.Id).Take(limit).Select(o => OrderDto.From(o)).ToListAsync();

    public Task<OrderDto?> GetOrder(OrdersContext db, string id) =>
        db.Orders.AsNoTracking().Where(o => o.Id == id).Select(o => OrderDto.From(o)).FirstOrDefaultAsync();
}
