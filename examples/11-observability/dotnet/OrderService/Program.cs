using System.Diagnostics;
using System.Diagnostics.Metrics;
using System.Text;
using System.Text.Json;
using Confluent.Kafka;
using Grpc.Net.Client;
using Npgsql;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Proto;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var dbUrl = Environment.GetEnvironmentVariable("DATABASE_URL")
    ?? "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass";
var kafkaBootstrap = Environment.GetEnvironmentVariable("KAFKA_BOOTSTRAP") ?? "kafka:9094";
var inventoryAddr = Environment.GetEnvironmentVariable("INVENTORY_ADDR") ?? "inventory:50051";
builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order-service"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddSource("order-service")
        .AddOtlpExporter())
    .WithMetrics(m => m
        .AddMeter("order-service")
        .AddOtlpExporter());

var app = builder.Build();

var dsBuilder = new NpgsqlDataSourceBuilder(dbUrl);
await using var dataSource = dsBuilder.Build();

var channel = GrpcChannel.ForAddress($"http://{inventoryAddr}",
    new GrpcChannelOptions { HttpHandler = new SocketsHttpHandler { EnableMultipleHttp2Connections = true } });
var inventoryClient = new InventoryService.InventoryServiceClient(channel);

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

var activitySource = new ActivitySource("order-service");
var meter = new Meter("order-service");
var ordersPlaced = meter.CreateCounter<long>("orders.placed");

app.MapGet("/healthz", () => new { status = "ok" });

app.MapPost("/orders", async (HttpContext ctx) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var root = doc.RootElement;
    var sku = root.GetProperty("sku").GetString()!;
    var quantity = root.GetProperty("quantity").GetInt32();
    var id = Guid.NewGuid().ToString();

    using var reserveSpan = activitySource.StartActivity("reserve-stock");
    reserveSpan?.SetTag("sku", sku);
    reserveSpan?.SetTag("quantity", quantity);

    var reply = await inventoryClient.ReserveStockAsync(
        new ReserveRequest { Sku = sku, Quantity = quantity });
    var status = reply.Confirmed ? "confirmed" : "rejected";
    reserveSpan?.SetTag("stock.confirmed", reply.Confirmed);

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
        var headers = new Headers();
        if (Activity.Current is { } activity)
        {
            var traceparent = $"00-{activity.TraceId}-{activity.SpanId}-{(activity.Recorded ? "01" : "00")}";
            headers.Add("traceparent", Encoding.UTF8.GetBytes(traceparent));
        }

        try
        {
            await producer.ProduceAsync("order.placed",
                new Message<Null, string> { Value = json, Headers = headers });
        }
        catch { }
    }

    ordersPlaced.Add(1,
        new KeyValuePair<string, object?>("sku", sku),
        new KeyValuePair<string, object?>("status", status));

    var traceId = Activity.Current?.TraceId.ToString() ?? "".PadLeft(32, '0');
    var spanId = Activity.Current?.SpanId.ToString() ?? "".PadLeft(16, '0');
    app.Logger.LogInformation("[trace_id={TraceId} span_id={SpanId}] order placed id={OrderId}",
        traceId, spanId, id);

    return Results.Json(order, statusCode: 201);
});

app.MapGet("/orders", async () =>
{
    var orders = new List<object>();
    await using var conn = await dataSource.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT 50";
    await using var reader = await cmd.ExecuteReaderAsync();
    while (await reader.ReadAsync())
    {
        orders.Add(new
        {
            id = reader.GetString(0),
            sku = reader.GetString(1),
            quantity = reader.GetInt32(2),
            status = reader.GetString(3)
        });
    }
    return orders;
});

app.Run();
