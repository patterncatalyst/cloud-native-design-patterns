using System.Diagnostics;
using System.Text;
using System.Text.Json;
using Confluent.Kafka;
using Npgsql;
using OpenTelemetry;
using OpenTelemetry.Context.Propagation;
using OpenTelemetry.Exporter;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

// Producer spans come from this source; AddSource below makes the SDK record and export them.
var orderSource = new ActivitySource("order-service");

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order-service"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddSource("order-service")
        // 4318 is the OTLP/HTTP port: the exporter defaults to gRPC, and a code-set endpoint is used as given.
        .AddOtlpExporter(o =>
        {
            var endpoint = Environment.GetEnvironmentVariable("OTEL_EXPORTER_OTLP_ENDPOINT") ?? "http://lgtm:4318";
            o.Endpoint = new Uri(endpoint.TrimEnd('/') + "/v1/traces");
            o.Protocol = OtlpExportProtocol.HttpProtobuf;
        }));

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
        Activity? publish = null;
        try
        {
            // Confluent.Kafka has no built-in tracing: write the W3C traceparent into the record headers
            // so the consumers can continue this trace.
            publish = orderSource.StartActivity("order.placed publish", ActivityKind.Producer);
            publish?.SetTag("messaging.system", "kafka");
            publish?.SetTag("messaging.destination.name", "order.placed");
            var message = new Message<Null, string> { Value = json, Headers = new Headers() };
            Propagators.DefaultTextMapPropagator.Inject(
                new PropagationContext(publish?.Context ?? Activity.Current?.Context ?? default, Baggage.Current),
                message.Headers,
                (headers, key, value) => headers.Add(key, Encoding.UTF8.GetBytes(value)));
            await producer.ProduceAsync("order.placed", message);
        }
        catch (Exception ex)
        {
            publish?.SetStatus(ActivityStatusCode.Error, ex.Message);
            app.Logger.LogWarning("Kafka publish failed: {Error}", ex.Message);
        }
        finally
        {
            publish?.Dispose();
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
