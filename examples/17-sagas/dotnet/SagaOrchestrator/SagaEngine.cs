using System.Text.Json.Nodes;
using Microsoft.EntityFrameworkCore;

/// <summary>
/// Orchestrates the saga: each Advance commits one step (state, context and log row in one transaction),
/// a failed step switches the saga to COMPENSATING and the completed steps are undone in reverse.
/// </summary>
public sealed partial class SagaEngine(
    IDbContextFactory<SagaContext> dbFactory, IConfiguration config, ILogger<SagaEngine> logger)
{
    private static readonly System.Diagnostics.ActivitySource Tracer = new("saga");
    private readonly bool _shippingFail = config.GetValue("SHIPPING_FAIL", false);

    private static readonly (string Name, string Compensate)[] Steps =
    [
        ("charge_payment", "refund_payment"),
        ("reserve_stock", "release_stock"),
        ("book_shipping", "cancel_shipping"),
    ];

    public async Task AdvanceAsync(string sagaId, CancellationToken ct = default)
    {
        string status;
        await using (var db = await dbFactory.CreateDbContextAsync(ct))
        {
            await using var tx = await db.Database.BeginTransactionAsync(ct);

            // The row lock serialises concurrent advances of the same saga.
            var saga = (await db.Sagas.FromSql($"SELECT * FROM sagas WHERE id = {sagaId} FOR UPDATE").ToListAsync(ct))
                .SingleOrDefault();
            if (saga is not { Status: "RUNNING" })
            {
                await tx.CommitAsync(ct);
                return;
            }

            if (saga.StepIndex >= Steps.Length)
            {
                saga.Status = "COMPLETED";
                saga.UpdatedAt = DateTime.UtcNow;
                await db.SaveChangesAsync(ct);
                await tx.CommitAsync(ct);
                return;
            }

            var step = Steps[saga.StepIndex];
            using var span = Tracer.StartActivity($"saga.{step.Name}");
            span?.SetTag("saga.id", sagaId);
            span?.SetTag("saga.step", step.Name);

            try
            {
                var result = ExecuteStep(step.Name, saga.Context);
                saga.Context[step.Name] = result;
                db.Log.Add(new SagaLogEntry { SagaId = sagaId, Step = step.Name, Action = "execute", Result = result.DeepClone().AsObject() });
                saga.StepIndex++;
            }
            catch (Exception e)
            {
                LogStepFailed(step.Name, e.Message);
                span?.SetTag("saga.failed", true);
                db.Log.Add(new SagaLogEntry
                {
                    SagaId = sagaId, Step = step.Name, Action = "failed",
                    Result = new JsonObject { ["error"] = e.Message },
                });
                saga.Status = "COMPENSATING";
            }

            saga.UpdatedAt = DateTime.UtcNow;
            await db.SaveChangesAsync(ct);
            await tx.CommitAsync(ct);
            status = saga.Status;
        }

        if (status == "RUNNING")
            await AdvanceAsync(sagaId, ct);
        else if (status == "COMPENSATING")
            await CompensateAsync(sagaId, ct);
    }

    private async Task CompensateAsync(string sagaId, CancellationToken ct)
    {
        await using var db = await dbFactory.CreateDbContextAsync(ct);
        var saga = await db.Sagas.SingleAsync(s => s.Id == sagaId, ct);

        for (var i = saga.StepIndex - 1; i >= 0; i--)
        {
            var compName = Steps[i].Compensate;
            using var span = Tracer.StartActivity($"saga.{compName}");
            span?.SetTag("saga.id", sagaId);
            span?.SetTag("saga.compensate", compName);

            var result = ExecuteStep(compName, saga.Context);
            db.Log.Add(new SagaLogEntry { SagaId = sagaId, Step = compName, Action = "compensate", Result = result });
            await db.SaveChangesAsync(ct);
        }

        saga.Status = "COMPENSATED";
        saga.UpdatedAt = DateTime.UtcNow;
        await db.SaveChangesAsync(ct);
        LogCompensated(sagaId);
    }

    /// <summary>Re-drives sagas that were RUNNING when the process stopped.</summary>
    public async Task ResumeRunningAsync(CancellationToken ct)
    {
        List<string> runningIds;
        await using (var db = await dbFactory.CreateDbContextAsync(ct))
            runningIds = await db.Sagas.Where(s => s.Status == "RUNNING").Select(s => s.Id).ToListAsync(ct);

        foreach (var id in runningIds)
        {
            LogResuming(id);
            await AdvanceAsync(id, ct);
        }
    }

    private JsonObject ExecuteStep(string stepName, JsonObject context)
    {
        switch (stepName)
        {
            case "charge_payment":
                var paymentId = $"pay-{Guid.NewGuid().ToString("N")[..8]}";
                LogCharged(paymentId, context["order_id"]?.ToString());
                return new JsonObject { ["payment_id"] = paymentId, ["amount"] = context["total"]?.GetValue<double>() ?? 0 };
            case "reserve_stock":
                var reservationId = $"rsv-{Guid.NewGuid().ToString("N")[..8]}";
                LogReserved(reservationId, context["sku"]?.ToString());
                return new JsonObject { ["reservation_id"] = reservationId, ["sku"] = context["sku"]?.ToString() };
            case "book_shipping":
                if (_shippingFail || context["fail_shipping"]?.GetValue<bool>() == true)
                    throw new InvalidOperationException("shipping service unavailable");
                var shipmentId = $"shp-{Guid.NewGuid().ToString("N")[..8]}";
                LogBooked(shipmentId);
                return new JsonObject { ["shipment_id"] = shipmentId };
            case "refund_payment":
                LogRefunded(context["charge_payment"]?["payment_id"]?.ToString());
                return new JsonObject { ["refunded"] = true };
            case "release_stock":
                LogReleased(context["reserve_stock"]?["reservation_id"]?.ToString());
                return new JsonObject { ["released"] = true };
            case "cancel_shipping":
                LogCancelled(context["book_shipping"]?["shipment_id"]?.ToString());
                return new JsonObject { ["cancelled"] = true };
            default:
                return new JsonObject();
        }
    }

    [LoggerMessage(Level = LogLevel.Information, Message = "charged payment {PaymentId} for order {OrderId}")]
    private partial void LogCharged(string paymentId, string? orderId);

    [LoggerMessage(Level = LogLevel.Information, Message = "reserved stock {ReservationId} for sku {Sku}")]
    private partial void LogReserved(string reservationId, string? sku);

    [LoggerMessage(Level = LogLevel.Information, Message = "booked shipping {ShipmentId}")]
    private partial void LogBooked(string shipmentId);

    [LoggerMessage(Level = LogLevel.Information, Message = "refunded payment {PaymentId}")]
    private partial void LogRefunded(string? paymentId);

    [LoggerMessage(Level = LogLevel.Information, Message = "released stock {ReservationId}")]
    private partial void LogReleased(string? reservationId);

    [LoggerMessage(Level = LogLevel.Information, Message = "cancelled shipping {ShipmentId}")]
    private partial void LogCancelled(string? shipmentId);

    [LoggerMessage(Level = LogLevel.Error, Message = "step {Step} failed: {Error} — starting compensation")]
    private partial void LogStepFailed(string step, string error);

    [LoggerMessage(Level = LogLevel.Information, Message = "saga {SagaId} fully compensated")]
    private partial void LogCompensated(string sagaId);

    [LoggerMessage(Level = LogLevel.Information, Message = "resuming saga {SagaId}")]
    private partial void LogResuming(string sagaId);
}

/// <summary>Runs the resume pass before the server starts taking requests.</summary>
public sealed class SagaResumeService(SagaEngine engine) : IHostedService
{
    public Task StartAsync(CancellationToken cancellationToken) => engine.ResumeRunningAsync(cancellationToken);
    public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;
}
