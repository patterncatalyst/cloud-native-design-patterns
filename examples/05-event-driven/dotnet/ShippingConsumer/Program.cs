using System.Runtime.InteropServices;
using System.Text.Json;
using Confluent.Kafka;
using Npgsql;
using OpenTelemetry;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var dbUrl = Environment.GetEnvironmentVariable("DATABASE_URL")
    ?? "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass";
var kafkaBootstrap = Environment.GetEnvironmentVariable("KAFKA_BOOTSTRAP") ?? "kafka:9094";
var otelEndpoint = Environment.GetEnvironmentVariable("OTEL_EXPORTER_OTLP_ENDPOINT") ?? "http://lgtm:4318";

using var tracerProvider = Sdk.CreateTracerProviderBuilder()
    .SetResourceBuilder(ResourceBuilder.CreateDefault().AddService("shipping-consumer"))
    .AddOtlpExporter(o => o.Endpoint = new Uri(otelEndpoint))
    .Build();
var tracer = tracerProvider!.GetTracer("shipping-consumer");

var dsBuilder = new NpgsqlDataSourceBuilder(dbUrl);
await using var dataSource = dsBuilder.Build();

using var cts = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) => { e.Cancel = true; cts.Cancel(); };
PosixSignalRegistration.Create(PosixSignal.SIGTERM, _ => cts.Cancel());

IConsumer<Ignore, string>? consumer = null;
for (var i = 0; i < 30; i++)
{
    try
    {
        consumer = new ConsumerBuilder<Ignore, string>(new ConsumerConfig
        {
            BootstrapServers = kafkaBootstrap,
            GroupId = "shipping-group",
            AutoOffsetReset = AutoOffsetReset.Earliest,
            EnableAutoCommit = false
        }).Build();
        consumer.Subscribe("order.placed");
        Console.WriteLine("Shipping consumer started");
        break;
    }
    catch
    {
        Console.WriteLine($"Kafka not ready, retry {i + 1}/30");
        Thread.Sleep(2000);
    }
}

if (consumer is null) { Console.WriteLine("Failed to connect to Kafka"); return; }

try
{
    while (!cts.Token.IsCancellationRequested)
    {
        ConsumeResult<Ignore, string>? cr;
        try { cr = consumer.Consume(TimeSpan.FromSeconds(1)); }
        catch (OperationCanceledException) { break; }
        catch (ConsumeException) { Thread.Sleep(1000); continue; }
        if (cr is null) continue;

        using var span = tracer.StartActiveSpan("process_shipment");
        try
        {
            using var doc = JsonDocument.Parse(cr.Message.Value);
            var orderId = doc.RootElement.GetProperty("id").GetString()!;
            span.SetAttribute("order.id", orderId);

            await using var conn = await dataSource.OpenConnectionAsync(cts.Token);
            await using var cmd = conn.CreateCommand();
            cmd.CommandText = "INSERT INTO shipments (order_id, status) VALUES ($1, $2) ON CONFLICT (order_id) DO NOTHING";
            cmd.Parameters.AddWithValue(orderId);
            cmd.Parameters.AddWithValue("scheduled");
            await cmd.ExecuteNonQueryAsync(cts.Token);

            consumer.Commit(cr);
            Console.WriteLine($"Shipment scheduled for order {orderId}");
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            Console.WriteLine($"Error processing message: {ex.Message}");
        }
    }
}
finally
{
    consumer.Close();
}
