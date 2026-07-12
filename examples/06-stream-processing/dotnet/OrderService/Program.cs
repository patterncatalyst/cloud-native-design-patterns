using System.Text.Json;
using Confluent.Kafka;
using Npgsql;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order-service"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter(o => o.Endpoint = new Uri(
            Environment.GetEnvironmentVariable("OTEL_EXPORTER_OTLP_ENDPOINT") ?? "http://lgtm:4318")));

var app = builder.Build();

var dbUrl = Environment.GetEnvironmentVariable("DATABASE_URL")
    ?? "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass";
var kafkaBootstrap = Environment.GetEnvironmentVariable("KAFKA_BOOTSTRAP") ?? "kafka:9094";

var dsBuilder = new NpgsqlDataSourceBuilder(dbUrl);
await using var dataSource = dsBuilder.Build();

IProducer<Null, string>? producer = null;
for (var i = 0; i < 30; i++)
{
    try
    {
        producer = new ProducerBuilder<Null, string>(
            new ProducerConfig { BootstrapServers = kafkaBootstrap }).Build();
        break;
    }
    catch
    {
        app.Logger.LogWarning("Kafka not ready, retry {Attempt}/30", i + 1);
        Thread.Sleep(2000);
    }
}

app.MapGet("/healthz", () => new { status = "ok" });

app.MapPost("/orders", async (HttpContext ctx) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var root = doc.RootElement;
    var merchantId = root.GetProperty("merchant_id").GetString()!;
    var sku = root.GetProperty("sku").GetString()!;
    var quantity = root.GetProperty("quantity").GetInt32();
    var total = root.GetProperty("total").GetDouble();
    var id = Guid.NewGuid().ToString();

    await using var conn = await dataSource.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "INSERT INTO orders (id, merchant_id, sku, quantity, total, status) VALUES ($1, $2, $3, $4, $5, $6)";
    cmd.Parameters.AddWithValue(id);
    cmd.Parameters.AddWithValue(merchantId);
    cmd.Parameters.AddWithValue(sku);
    cmd.Parameters.AddWithValue(quantity);
    cmd.Parameters.AddWithValue(total);
    cmd.Parameters.AddWithValue("confirmed");
    await cmd.ExecuteNonQueryAsync();

    var order = new { id, merchant_id = merchantId, sku, quantity, total, status = "confirmed" };
    var json = JsonSerializer.Serialize(order);

    if (producer is not null)
    {
        try { await producer.ProduceAsync("order.placed", new Message<Null, string> { Value = json }); }
        catch { }
    }

    return Results.Json(order, statusCode: 201);
});

app.MapGet("/orders", async () =>
{
    var orders = new List<object>();
    await using var conn = await dataSource.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "SELECT id, merchant_id, sku, quantity, total, status FROM orders ORDER BY created_at DESC LIMIT 50";
    await using var reader = await cmd.ExecuteReaderAsync();
    while (await reader.ReadAsync())
    {
        orders.Add(new
        {
            id = reader.GetString(0),
            merchant_id = reader.GetString(1),
            sku = reader.GetString(2),
            quantity = reader.GetInt32(3),
            total = reader.GetDecimal(4),
            status = reader.GetString(5)
        });
    }
    return orders;
});

app.Run();
