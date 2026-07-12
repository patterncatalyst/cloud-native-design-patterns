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
    var sku = root.GetProperty("sku").GetString()!;
    var quantity = root.GetProperty("quantity").GetInt32();
    var id = Guid.NewGuid().ToString();

    await using var conn = await dataSource.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4)";
    cmd.Parameters.AddWithValue(id);
    cmd.Parameters.AddWithValue(sku);
    cmd.Parameters.AddWithValue(quantity);
    cmd.Parameters.AddWithValue("confirmed");
    await cmd.ExecuteNonQueryAsync();

    var order = new { id, sku, quantity, status = "confirmed" };
    var json = JsonSerializer.Serialize(order);

    if (producer is not null)
    {
        try
        {
            await producer.ProduceAsync("order.placed",
                new Message<Null, string> { Value = json });
        }
        catch (Exception ex)
        {
            app.Logger.LogWarning("Kafka publish failed: {Error}", ex.Message);
        }
    }

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
