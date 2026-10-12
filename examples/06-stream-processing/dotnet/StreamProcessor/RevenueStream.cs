using System.Globalization;
using System.Text.Json;
using Confluent.Kafka;
using Confluent.Kafka.Admin;
using Streamiz.Kafka.Net;
using Streamiz.Kafka.Net.SerDes;
using Streamiz.Kafka.Net.Stream;
using Streamiz.Kafka.Net.Table;

// order.placed -> tumbling window per merchant -> revenue.by-merchant.
//
// The windowed aggregate is a KTable; every update to a (merchant, window) row is emitted
// downstream, so a window yields a running total that settles when the window closes.
// Consumers keep the latest record per (merchant_id, window_start).
public sealed partial class RevenueStream(IConfiguration configuration, ILoggerFactory loggerFactory, ILogger<RevenueStream> logger)
    : BackgroundService
{
    private const string Orders = "order.placed";
    private const string Revenue = "revenue.by-merchant";

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var kafkaBootstrap = configuration.GetValue("KAFKA_BOOTSTRAP", "kafka:9094");
        var windowSeconds = configuration.GetValue("WINDOW_SECONDS", 10);

        var config = new StreamConfig<StringSerDes, StringSerDes>
        {
            // application.id is also the consumer group (verify.sh looks for "stream-processor")
            ApplicationId = "stream-processor",
            BootstrapServers = kafkaBootstrap,
            AutoOffsetReset = AutoOffsetReset.Earliest,
            // Emit updated window aggregates every second instead of every 30 s (default)
            CommitIntervalMs = 1000,
            DefaultStateStoreCacheMaxBytes = 0,
            StateDir = "/tmp/kafka-streams",
            Logger = loggerFactory,
            // A record that cannot be deserialized is logged and skipped, not fatal
            DeserializationExceptionHandler = (_, record, ex) =>
            {
                LogSkippedRecord(record.Topic, record.Offset, ex.Message);
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
                LogEmitted(start, merchant, acc.Count, revenue.ToString("F2", CultureInfo.InvariantCulture));
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
        await EnsureTopic(kafkaBootstrap, Orders, stoppingToken);
        await EnsureTopic(kafkaBootstrap, Revenue, stoppingToken);

        using var stream = new KafkaStream(builder.Build(), config);
        await stream.StartAsync(stoppingToken);
        LogStarted();
        try { await Task.Delay(Timeout.Infinite, stoppingToken); }
        catch (OperationCanceledException) { }
    }

    private async Task EnsureTopic(string bootstrap, string topic, CancellationToken ct)
    {
        using var admin = new AdminClientBuilder(new AdminClientConfig { BootstrapServers = bootstrap }).Build();
        for (var attempt = 1; attempt <= 30; attempt++)
        {
            try
            {
                await admin.CreateTopicsAsync(new[]
                {
                    new TopicSpecification { Name = topic, NumPartitions = -1, ReplicationFactor = -1 },
                });
                return;
            }
            catch (CreateTopicsException e) when (e.Results.All(r => r.Error.Code == ErrorCode.TopicAlreadyExists))
            {
                return;
            }
            catch (Exception e)
            {
                LogKafkaNotReady(attempt, e.Message);
                await Task.Delay(2000, ct);
            }
        }
        throw new InvalidOperationException($"could not reach Kafka at {bootstrap}");
    }

    /// <summary>Re-keys an order event by merchant (empty key = unusable record, filtered out); the value is the order total.</summary>
    private static KeyValuePair<string, string> Rekey(string json)
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
    private Acc Add(string merchant, Acc acc, string amount)
    {
        if (decimal.TryParse(amount, NumberStyles.Float, CultureInfo.InvariantCulture, out var value))
            return new Acc { Count = acc.Count + 1, Total = acc.Total + value };
        LogInvalidTotal(merchant, amount);
        return acc;
    }

    [LoggerMessage(Level = LogLevel.Information, Message = "Stream processor started")]
    private partial void LogStarted();

    [LoggerMessage(Level = LogLevel.Information,
        Message = "emitted revenue window={Window} merchant={Merchant} count={Count} revenue={Revenue}")]
    private partial void LogEmitted(long window, string merchant, int count, string revenue);

    [LoggerMessage(Level = LogLevel.Warning, Message = "skipping undeserializable record topic={Topic} offset={Offset}: {Error}")]
    private partial void LogSkippedRecord(string topic, long offset, string error);

    [LoggerMessage(Level = LogLevel.Warning, Message = "skipping order with invalid total merchant={Merchant} total={Total}")]
    private partial void LogInvalidTotal(string merchant, string total);

    [LoggerMessage(Level = LogLevel.Warning, Message = "Kafka not ready, retry {Attempt}/30: {Error}")]
    private partial void LogKafkaNotReady(int attempt, string error);
}

public class Acc
{
    public int Count { get; set; }
    public decimal Total { get; set; }
}
