using System.Runtime.InteropServices;
using System.Text.Json;
using Confluent.Kafka;
using OpenTelemetry;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var kafkaBootstrap = Environment.GetEnvironmentVariable("KAFKA_BOOTSTRAP") ?? "kafka:9094";
var otelEndpoint = Environment.GetEnvironmentVariable("OTEL_EXPORTER_OTLP_ENDPOINT") ?? "http://lgtm:4318";
var windowSeconds = int.Parse(Environment.GetEnvironmentVariable("WINDOW_SECONDS") ?? "300");

using var tracerProvider = Sdk.CreateTracerProviderBuilder()
    .SetResourceBuilder(ResourceBuilder.CreateDefault().AddService("stream-processor"))
    .AddOtlpExporter(o => o.Endpoint = new Uri(otelEndpoint))
    .Build();
var tracer = tracerProvider!.GetTracer("stream-processor");

using var cts = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) => { e.Cancel = true; cts.Cancel(); };
PosixSignalRegistration.Create(PosixSignal.SIGTERM, _ => cts.Cancel());

var windows = new Dictionary<long, Dictionary<string, (int count, double total)>>();

long GetWindowStart(long epochSeconds) => epochSeconds / windowSeconds * windowSeconds;

IConsumer<Ignore, string>? consumer = null;
for (var i = 0; i < 30; i++)
{
    try
    {
        consumer = new ConsumerBuilder<Ignore, string>(new ConsumerConfig
        {
            BootstrapServers = kafkaBootstrap,
            GroupId = "stream-processor",
            AutoOffsetReset = AutoOffsetReset.Earliest,
            EnableAutoCommit = false
        }).Build();
        consumer.Subscribe("order.placed");
        Console.WriteLine("Stream processor started");
        break;
    }
    catch
    {
        Console.WriteLine($"Kafka not ready, retry {i + 1}/30");
        Thread.Sleep(2000);
    }
}

if (consumer is null) { Console.WriteLine("Failed to connect to Kafka"); return; }

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

if (producer is null) { Console.WriteLine("Failed to create Kafka producer"); return; }

try
{
    while (!cts.Token.IsCancellationRequested)
    {
        ConsumeResult<Ignore, string>? cr;
        try { cr = consumer.Consume(TimeSpan.FromSeconds(1)); }
        catch (OperationCanceledException) { break; }
        catch (ConsumeException) { Thread.Sleep(1000); continue; }
        if (cr is null)
        {
            FlushExpiredWindows(producer, tracer);
            continue;
        }

        using var span = tracer.StartActiveSpan("process_order");
        try
        {
            using var doc = JsonDocument.Parse(cr.Message.Value);
            var root = doc.RootElement;
            var merchantId = root.GetProperty("merchant_id").GetString()!;
            var orderTotal = root.GetProperty("total").GetDouble();

            var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            var windowStart = GetWindowStart(now);

            if (!windows.TryGetValue(windowStart, out var merchants))
            {
                merchants = new Dictionary<string, (int count, double total)>();
                windows[windowStart] = merchants;
            }

            var current = merchants.GetValueOrDefault(merchantId);
            merchants[merchantId] = (current.count + 1, current.total + orderTotal);

            consumer.Commit(cr);
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            Console.WriteLine($"Error processing: {ex.Message}");
        }

        FlushExpiredWindows(producer, tracer);
    }
}
finally
{
    FlushAllWindows(producer, tracer);
    consumer.Close();
    producer.Flush(TimeSpan.FromSeconds(5));
}

void FlushExpiredWindows(IProducer<Null, string> p, Tracer t)
{
    var currentWindow = GetWindowStart(DateTimeOffset.UtcNow.ToUnixTimeSeconds());
    var expired = windows.Keys.Where(w => w < currentWindow).ToList();
    foreach (var ws in expired)
    {
        if (windows.Remove(ws, out var merchants))
            EmitWindow(p, t, ws, merchants);
    }
}

void FlushAllWindows(IProducer<Null, string> p, Tracer t)
{
    foreach (var (ws, merchants) in windows)
        EmitWindow(p, t, ws, merchants);
    windows.Clear();
}

void EmitWindow(IProducer<Null, string> p, Tracer t, long windowStart, Dictionary<string, (int count, double total)> merchants)
{
    var windowEnd = windowStart + windowSeconds;
    foreach (var (merchantId, (count, total)) in merchants)
    {
        using var span = t.StartActiveSpan("emit_aggregate");
        var agg = new
        {
            window_start = windowStart,
            window_end = windowEnd,
            merchant_id = merchantId,
            order_count = count,
            revenue = Math.Round(total, 2)
        };
        var json = JsonSerializer.Serialize(agg);
        try
        {
            p.Produce("revenue.by-merchant", new Message<Null, string> { Value = json });
            Console.WriteLine($"Emitted aggregate: {merchantId} count={count} revenue={total:F2} window=[{windowStart},{windowEnd})");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Failed to emit aggregate: {ex.Message}");
        }
    }
}
