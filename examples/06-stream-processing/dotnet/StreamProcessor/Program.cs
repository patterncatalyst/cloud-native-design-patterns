using System.Globalization;
using System.Runtime.InteropServices;
using System.Text.Json;
using Streamiz.Kafka.Net;
using Streamiz.Kafka.Net.SerDes;
using Streamiz.Kafka.Net.Stream;
using Streamiz.Kafka.Net.Table;
using OpenTelemetry;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

// order.placed -> tumbling window per merchant -> revenue.by-merchant.
//
// The windowed aggregate is a KTable; every update to a (merchant, window) row is emitted
// downstream, so a window yields a running total that settles when the window closes.
// Consumers keep the latest record per (merchant_id, window_start).

const string Orders = "order.placed";
const string Revenue = "revenue.by-merchant";

var kafkaBootstrap = Environment.GetEnvironmentVariable("KAFKA_BOOTSTRAP") ?? "kafka:9094";
var otelEndpoint = Environment.GetEnvironmentVariable("OTEL_EXPORTER_OTLP_ENDPOINT") ?? "http://lgtm:4318";
var windowSeconds = int.Parse(Environment.GetEnvironmentVariable("WINDOW_SECONDS") ?? "10");

using var tracerProvider = Sdk.CreateTracerProviderBuilder()
    .SetResourceBuilder(ResourceBuilder.CreateDefault().AddService("stream-processor"))
    .AddOtlpExporter(o => o.Endpoint = new Uri(otelEndpoint))
    .Build();

var config = new StreamConfig<StringSerDes, StringSerDes>
{
    // application.id is also the consumer group (verify.sh looks for "stream-processor")
    ApplicationId = "stream-processor",
    BootstrapServers = kafkaBootstrap,
    AutoOffsetReset = Confluent.Kafka.AutoOffsetReset.Earliest,
    // Emit updated window aggregates every second instead of every 30 s (default)
    CommitIntervalMs = 1000,
    DefaultStateStoreCacheMaxBytes = 0,
    StateDir = "/tmp/kafka-streams",
    // A record that cannot be deserialized is logged and skipped, not fatal
    DeserializationExceptionHandler = (_, record, ex) =>
    {
        Console.WriteLine($"WARN skipping undeserializable record topic={record.Topic} offset={record.Offset}: {ex.Message}");
        return ExceptionHandlerResponse.CONTINUE;
    },
};

var builder = new StreamBuilder();

builder.Stream<string, string>(Orders)
    .Map((_, json, _) => Rekey(json))
    .Filter((merchant, _, _) => merchant.Length > 0)
    .GroupByKey()
    .WindowedBy(TumblingWindowOptions.Of(TimeSpan.FromSeconds(windowSeconds), TimeSpan.Zero))
    .Aggregate(
        () => new Acc(),
        (merchant, amount, acc) => Add(merchant, acc, amount),
        RocksDbWindows.As<string, Acc>("revenue-store")
            .WithKeySerdes(new StringSerDes())
            .WithValueSerdes(new JsonSerDes<Acc>()))
    .ToStream()
    .Map((window, acc, _) =>
    {
        var merchant = window.Key;
        var start = window.Window.StartMs / 1000;
        var revenue = Math.Round(acc.Total, 2, MidpointRounding.AwayFromZero) + 0.00m; // scale 2, like BigDecimal
        Console.WriteLine(string.Format(CultureInfo.InvariantCulture,
            "emitted revenue window={0} merchant={1} count={2} revenue={3:F2}",
            start, merchant, acc.Count, revenue));
        var json = JsonSerializer.Serialize(new Dictionary<string, object>
        {
            ["window_start"] = start,
            ["window_end"] = start + windowSeconds,
            ["merchant_id"] = merchant,
            ["order_count"] = acc.Count,
            ["revenue"] = revenue,
        });
        return KeyValuePair.Create(merchant, json);
    })
    .To<StringSerDes, StringSerDes>(Revenue);

// Streamiz needs the source topic to size the repartition topic. Its clients default to
// allow.auto.create.topics=false, so neither topic is created on first use: create both
// up front (the broker defaults apply).
await EnsureTopic(kafkaBootstrap, Orders);
await EnsureTopic(kafkaBootstrap, Revenue);

var stream = new KafkaStream(builder.Build(), config);

using var cts = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) => { e.Cancel = true; cts.Cancel(); };
PosixSignalRegistration.Create(PosixSignal.SIGTERM, _ => cts.Cancel());

await stream.StartAsync(cts.Token);
Console.WriteLine("Stream processor started");
try { await Task.Delay(Timeout.Infinite, cts.Token); }
catch (OperationCanceledException) { }
stream.Dispose();

static async Task EnsureTopic(string bootstrap, string topic)
{
    using var admin = new Confluent.Kafka.AdminClientBuilder(
        new Confluent.Kafka.AdminClientConfig { BootstrapServers = bootstrap }).Build();
    for (var attempt = 1; attempt <= 30; attempt++)
    {
        try
        {
            await admin.CreateTopicsAsync(new[]
            {
                new Confluent.Kafka.Admin.TopicSpecification { Name = topic, NumPartitions = -1, ReplicationFactor = -1 },
            });
            return;
        }
        catch (Confluent.Kafka.Admin.CreateTopicsException e)
            when (e.Results.All(r => r.Error.Code == Confluent.Kafka.ErrorCode.TopicAlreadyExists))
        {
            return;
        }
        catch (Exception e)
        {
            Console.WriteLine($"Kafka not ready, retry {attempt}/30: {e.Message}");
            await Task.Delay(2000);
        }
    }
    throw new InvalidOperationException($"could not reach Kafka at {bootstrap}");
}

/// <summary>Re-keys an order event by merchant (empty key = unusable record, filtered out); the value is the order total.</summary>
static KeyValuePair<string, string> Rekey(string json)
{
    try
    {
        using var doc = JsonDocument.Parse(json);
        var merchant = doc.RootElement.GetProperty("merchant_id").GetString() ?? "";
        var amount = doc.RootElement.TryGetProperty("total", out var t) && t.ValueKind != JsonValueKind.Null
            ? t.ToString() : "0";
        return KeyValuePair.Create(merchant, amount);
    }
    catch (Exception)
    {
        return KeyValuePair.Create("", "");
    }
}

/// <summary>A total that is not a number skips the record instead of killing the stream thread.</summary>
static Acc Add(string merchant, Acc acc, string amount)
{
    if (decimal.TryParse(amount, NumberStyles.Float, CultureInfo.InvariantCulture, out var value))
        return new Acc { Count = acc.Count + 1, Total = acc.Total + value };
    Console.WriteLine($"WARN skipping order with invalid total merchant={merchant} total={amount}");
    return acc;
}

public class Acc
{
    public int Count { get; set; }
    public decimal Total { get; set; }
}
