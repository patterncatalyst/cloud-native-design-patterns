using System.Diagnostics;
using System.Text;
using System.Text.Json;
using Confluent.Kafka;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using OpenTelemetry;
using OpenTelemetry.Context.Propagation;

/// <summary>
/// Idempotent consumer of order.placed. A redelivered message finds the row (existence check) or loses the
/// race to the unique index on order_id (backstop); both count as processed and the offset is committed.
/// </summary>
public sealed partial class NotificationWorker(IServiceScopeFactory scopes, IConfiguration config, ILogger<NotificationWorker> logger)
    : BackgroundService
{
    public const string SourceName = "notification-consumer";
    private static readonly ActivitySource Source = new(SourceName);

    protected override Task ExecuteAsync(CancellationToken stoppingToken) =>
        Task.Run(() => ConsumeAsync(stoppingToken), stoppingToken);

    private async Task ConsumeAsync(CancellationToken stoppingToken)
    {
        using var consumer = new ConsumerBuilder<Ignore, string>(new ConsumerConfig
        {
            BootstrapServers = config.GetValue("KAFKA_BOOTSTRAP", "kafka:9094"),
            GroupId = "notification-group",
            AutoOffsetReset = AutoOffsetReset.Earliest,
            EnableAutoCommit = false,
        }).Build();
        consumer.Subscribe("order.placed");
        LogStarted();

        try
        {
            while (!stoppingToken.IsCancellationRequested)
            {
                ConsumeResult<Ignore, string>? cr;
                try { cr = consumer.Consume(stoppingToken); }
                catch (OperationCanceledException) { break; }
                catch (ConsumeException) { await Task.Delay(1000, stoppingToken); continue; }
                if (cr is null) continue;

                // Continue the producer's trace: read the W3C traceparent that order-service wrote into the record headers.
                var parent = Propagators.DefaultTextMapPropagator.Extract(
                    default,
                    cr.Message.Headers,
                    (headers, key) => headers is null
                        ? Array.Empty<string>()
                        : headers.Where(h => h.Key == key)
                                 .Select(h => h.GetValueBytes())
                                 .Where(b => b is not null)
                                 .Select(b => Encoding.UTF8.GetString(b!)));
                Baggage.Current = parent.Baggage;
                using var span = Source.StartActivity("send_notification", ActivityKind.Consumer, parent.ActivityContext);
                span?.SetTag("messaging.system", "kafka");
                span?.SetTag("messaging.destination.name", "order.placed");
                try
                {
                    using var doc = JsonDocument.Parse(cr.Message.Value);
                    var orderId = doc.RootElement.GetProperty("id").GetString()!;
                    span?.SetTag("order.id", orderId);

                    if (await HandleAsync(orderId, stoppingToken))
                        LogDone(orderId);
                    else
                        LogDuplicate(orderId);

                    consumer.Commit(cr);
                }
                catch (Exception ex) when (ex is not OperationCanceledException)
                {
                    span?.SetStatus(ActivityStatusCode.Error, ex.Message);
                    LogFailed(ex.Message);
                }
            }
        }
        finally
        {
            consumer.Close();
        }
    }

    /// <returns>true when this call recorded the row, false when it already existed.</returns>
    private async Task<bool> HandleAsync(string orderId, CancellationToken ct)
    {
        await using var scope = scopes.CreateAsyncScope();
        var db = scope.ServiceProvider.GetRequiredService<NotificationsContext>();

        if (await db.Notifications.AnyAsync(x => x.OrderId == orderId, ct))
            return false;

        db.Notifications.Add(new Notification { OrderId = orderId, Channel = "email" });
        try
        {
            await db.SaveChangesAsync(ct);
            return true;
        }
        catch (DbUpdateException ex) when (ex.InnerException is PostgresException { SqlState: PostgresErrorCodes.UniqueViolation })
        {
            return false;
        }
    }

    [LoggerMessage(Level = LogLevel.Information, Message = "Notification consumer started")]
    private partial void LogStarted();

    [LoggerMessage(Level = LogLevel.Information, Message = "Notification sent for order {OrderId}")]
    private partial void LogDone(string orderId);

    [LoggerMessage(Level = LogLevel.Information, Message = "Notification already sent for order {OrderId}")]
    private partial void LogDuplicate(string orderId);

    [LoggerMessage(Level = LogLevel.Error, Message = "Error processing message: {Error}")]
    private partial void LogFailed(string error);
}
