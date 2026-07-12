using System.Text.Json;
using Confluent.Kafka;
using Grpc.Net.Client;
using Npgsql;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Proto;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var dbUrl = Environment.GetEnvironmentVariable("DATABASE_URL")
    ?? "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass";
var kafkaBootstrap = Environment.GetEnvironmentVariable("KAFKA_BOOTSTRAP") ?? "kafka:9094";
var inventoryAddr = Environment.GetEnvironmentVariable("INVENTORY_ADDR") ?? "inventory:50051";

var dsBuilder = new NpgsqlDataSourceBuilder(dbUrl);
var dataSource = dsBuilder.Build();
builder.Services.AddSingleton(dataSource);

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order-service"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter(o => o.Endpoint = new Uri(
            Environment.GetEnvironmentVariable("OTEL_EXPORTER_OTLP_ENDPOINT") ?? "http://lgtm:4318")));

builder.Services
    .AddGraphQLServer()
    .AddQueryType<Query>();

var app = builder.Build();

var channel = GrpcChannel.ForAddress($"http://{inventoryAddr}",
    new GrpcChannelOptions { HttpHandler = new SocketsHttpHandler { EnableMultipleHttp2Connections = true } });
var inventoryClient = new Inventory.InventoryClient(channel);

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

app.MapGet("/healthz", () => new { status = "ok" });

app.MapPost("/orders", async (HttpContext ctx) =>
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
    var status = reply.Reserved ? "confirmed" : "rejected";
    var id = Guid.NewGuid().ToString();

    await using var conn = await dataSource.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4)";
    cmd.Parameters.AddWithValue(id);
    cmd.Parameters.AddWithValue(sku);
    cmd.Parameters.AddWithValue(quantity);
    cmd.Parameters.AddWithValue(status);
    await cmd.ExecuteNonQueryAsync();

    var order = new { id, sku, quantity, status };
    var json = JsonSerializer.Serialize(order);
    if (producer is not null)
    {
        try { await producer.ProduceAsync("order.placed", new Message<Null, string> { Value = json }); }
        catch { }
    }

    return Results.Json(order, statusCode: 201);
});

app.MapGet("/orders", async (string? after, int? limit) =>
{
    var lim = limit is > 0 ? limit.Value : 50;
    var orders = new List<OrderDto>();
    await using var conn = await dataSource.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();

    if (!string.IsNullOrEmpty(after))
    {
        cmd.CommandText = "SELECT id, sku, quantity, status FROM orders WHERE id > $1 ORDER BY id LIMIT $2";
        cmd.Parameters.AddWithValue(after);
        cmd.Parameters.AddWithValue(lim);
    }
    else
    {
        cmd.CommandText = "SELECT id, sku, quantity, status FROM orders ORDER BY id LIMIT $1";
        cmd.Parameters.AddWithValue(lim);
    }

    await using var reader = await cmd.ExecuteReaderAsync();
    while (await reader.ReadAsync())
    {
        orders.Add(new OrderDto
        {
            Id = reader.GetString(0),
            Sku = reader.GetString(1),
            Quantity = reader.GetInt32(2),
            Status = reader.GetString(3)
        });
    }

    string? nextCursor = orders.Count == lim ? orders[^1].Id : null;
    return new { items = orders, next_cursor = nextCursor };
});

app.MapGraphQL("/graphql");

app.Run();

public class OrderDto
{
    public string Id { get; set; } = "";
    public string Sku { get; set; } = "";
    public int Quantity { get; set; }
    public string Status { get; set; } = "";
}

public class Query
{
    public async Task<List<OrderDto>> GetOrders(NpgsqlDataSource ds, int limit = 50)
    {
        var orders = new List<OrderDto>();
        await using var conn = await ds.OpenConnectionAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT id, sku, quantity, status FROM orders ORDER BY id LIMIT $1";
        cmd.Parameters.AddWithValue(limit);
        await using var reader = await cmd.ExecuteReaderAsync();
        while (await reader.ReadAsync())
        {
            orders.Add(new OrderDto
            {
                Id = reader.GetString(0),
                Sku = reader.GetString(1),
                Quantity = reader.GetInt32(2),
                Status = reader.GetString(3)
            });
        }
        return orders;
    }

    public async Task<OrderDto?> GetOrder(NpgsqlDataSource ds, string id)
    {
        await using var conn = await ds.OpenConnectionAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT id, sku, quantity, status FROM orders WHERE id = $1";
        cmd.Parameters.AddWithValue(id);
        await using var reader = await cmd.ExecuteReaderAsync();
        if (await reader.ReadAsync())
        {
            return new OrderDto
            {
                Id = reader.GetString(0),
                Sku = reader.GetString(1),
                Quantity = reader.GetInt32(2),
                Status = reader.GetString(3)
            };
        }
        return null;
    }
}
