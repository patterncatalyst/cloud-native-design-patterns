using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var connString = builder.Configuration.GetConnectionString("Default")
    ?? throw new InvalidOperationException("ConnectionStrings:Default is required");

var dataSource = new NpgsqlDataSourceBuilder(connString).Build();
builder.Services.AddSingleton(dataSource);

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("saga-orchestrator"))
    .WithTracing(t => t
        .AddSource("saga")
        .AddAspNetCoreInstrumentation()
        .AddNpgsql()
        .AddOtlpExporter());

var app = builder.Build();
var db = app.Services.GetRequiredService<NpgsqlDataSource>();
var logger = app.Services.GetRequiredService<ILoggerFactory>().CreateLogger("saga");
var tracer = new ActivitySource("saga");
var shippingFail = Environment.GetEnvironmentVariable("SHIPPING_FAIL")?.Equals("true", StringComparison.OrdinalIgnoreCase) ?? false;

var steps = new[]
{
    new { Name = "charge_payment", Compensate = "refund_payment" },
    new { Name = "reserve_stock", Compensate = "release_stock" },
    new { Name = "book_shipping", Compensate = "cancel_shipping" }
};

async Task<JsonObject> ExecuteStep(string stepName, JsonObject context)
{
    if (stepName == "charge_payment")
    {
        var paymentId = $"pay-{Guid.NewGuid().ToString("N")[..8]}";
        logger.LogInformation("charged payment {PaymentId} for order {OrderId}", paymentId, context["order_id"]?.ToString());
        return new JsonObject { ["payment_id"] = paymentId, ["amount"] = context["total"]?.GetValue<double>() ?? 0 };
    }
    if (stepName == "reserve_stock")
    {
        var reservationId = $"rsv-{Guid.NewGuid().ToString("N")[..8]}";
        logger.LogInformation("reserved stock {ReservationId} for sku {Sku}", reservationId, context["sku"]?.ToString());
        return new JsonObject { ["reservation_id"] = reservationId, ["sku"] = context["sku"]?.ToString() };
    }
    if (stepName == "book_shipping")
    {
        if (shippingFail || context["fail_shipping"]?.GetValue<bool>() == true)
            throw new InvalidOperationException("shipping service unavailable");
        var shipmentId = $"shp-{Guid.NewGuid().ToString("N")[..8]}";
        logger.LogInformation("booked shipping {ShipmentId}", shipmentId);
        return new JsonObject { ["shipment_id"] = shipmentId };
    }
    if (stepName == "refund_payment")
    {
        logger.LogInformation("refunded payment {PaymentId}", context["charge_payment"]?["payment_id"]?.ToString());
        return new JsonObject { ["refunded"] = true };
    }
    if (stepName == "release_stock")
    {
        logger.LogInformation("released stock {ReservationId}", context["reserve_stock"]?["reservation_id"]?.ToString());
        return new JsonObject { ["released"] = true };
    }
    if (stepName == "cancel_shipping")
    {
        logger.LogInformation("cancelled shipping {ShipmentId}", context["book_shipping"]?["shipment_id"]?.ToString());
        return new JsonObject { ["cancelled"] = true };
    }
    return new JsonObject();
}

async Task Advance(string sagaId)
{
    await using var conn = await db.OpenConnectionAsync();
    await using var tx = await conn.BeginTransactionAsync();

    await using var selCmd = conn.CreateCommand();
    selCmd.Transaction = tx;
    selCmd.CommandText = "SELECT id, status, step_index, context FROM sagas WHERE id=$1 FOR UPDATE";
    selCmd.Parameters.AddWithValue(sagaId);
    await using var reader = await selCmd.ExecuteReaderAsync();
    if (!await reader.ReadAsync() || reader.GetString(1) != "RUNNING")
    {
        await tx.CommitAsync();
        return;
    }

    var stepIndex = reader.GetInt32(2);
    var context = JsonNode.Parse(reader.GetString(3))!.AsObject();
    await reader.CloseAsync();

    if (stepIndex >= steps.Length)
    {
        await using var doneCmd = conn.CreateCommand();
        doneCmd.Transaction = tx;
        doneCmd.CommandText = "UPDATE sagas SET status='COMPLETED', updated_at=now() WHERE id=$1";
        doneCmd.Parameters.AddWithValue(sagaId);
        await doneCmd.ExecuteNonQueryAsync();
        await tx.CommitAsync();
        return;
    }

    var step = steps[stepIndex];
    using var span = tracer.StartActivity($"saga.{step.Name}");
    span?.SetTag("saga.id", sagaId);
    span?.SetTag("saga.step", step.Name);

    try
    {
        var result = await ExecuteStep(step.Name, context);
        context[step.Name] = result;

        await using var logCmd = conn.CreateCommand();
        logCmd.Transaction = tx;
        logCmd.CommandText = "INSERT INTO saga_log (saga_id, step, action, result) VALUES ($1, $2, 'execute', $3)";
        logCmd.Parameters.AddWithValue(sagaId);
        logCmd.Parameters.AddWithValue(step.Name);
        logCmd.Parameters.AddWithValue(NpgsqlTypes.NpgsqlDbType.Jsonb, result.ToJsonString());
        await logCmd.ExecuteNonQueryAsync();

        await using var updCmd = conn.CreateCommand();
        updCmd.Transaction = tx;
        updCmd.CommandText = "UPDATE sagas SET step_index=$1, context=$2, updated_at=now() WHERE id=$3";
        updCmd.Parameters.AddWithValue(stepIndex + 1);
        updCmd.Parameters.AddWithValue(NpgsqlTypes.NpgsqlDbType.Jsonb, context.ToJsonString());
        updCmd.Parameters.AddWithValue(sagaId);
        await updCmd.ExecuteNonQueryAsync();
        await tx.CommitAsync();
    }
    catch (Exception e)
    {
        logger.LogError("step {Step} failed: {Error} — starting compensation", step.Name, e.Message);
        span?.SetTag("saga.failed", true);

        await using var failLog = conn.CreateCommand();
        failLog.Transaction = tx;
        failLog.CommandText = "INSERT INTO saga_log (saga_id, step, action, result) VALUES ($1, $2, 'failed', $3)";
        failLog.Parameters.AddWithValue(sagaId);
        failLog.Parameters.AddWithValue(step.Name);
        failLog.Parameters.AddWithValue(NpgsqlTypes.NpgsqlDbType.Jsonb, JsonSerializer.Serialize(new { error = e.Message }));
        await failLog.ExecuteNonQueryAsync();

        await using var compCmd = conn.CreateCommand();
        compCmd.Transaction = tx;
        compCmd.CommandText = "UPDATE sagas SET status='COMPENSATING', updated_at=now() WHERE id=$1";
        compCmd.Parameters.AddWithValue(sagaId);
        await compCmd.ExecuteNonQueryAsync();
        await tx.CommitAsync();
    }

    await using var statusConn = await db.OpenConnectionAsync();
    await using var statusCmd = statusConn.CreateCommand();
    statusCmd.CommandText = "SELECT status FROM sagas WHERE id=$1";
    statusCmd.Parameters.AddWithValue(sagaId);
    var currentStatus = (string)(await statusCmd.ExecuteScalarAsync())!;

    if (currentStatus == "RUNNING")
        await Advance(sagaId);
    else if (currentStatus == "COMPENSATING")
        await Compensate(sagaId);
}

async Task Compensate(string sagaId)
{
    await using var conn = await db.OpenConnectionAsync();
    await using var selCmd = conn.CreateCommand();
    selCmd.CommandText = "SELECT step_index, context FROM sagas WHERE id=$1";
    selCmd.Parameters.AddWithValue(sagaId);
    await using var reader = await selCmd.ExecuteReaderAsync();
    await reader.ReadAsync();
    var stepIndex = reader.GetInt32(0);
    var context = JsonNode.Parse(reader.GetString(1))!.AsObject();
    await reader.CloseAsync();

    for (var i = stepIndex - 1; i >= 0; i--)
    {
        var step = steps[i];
        var compName = step.Compensate;
        using var span = tracer.StartActivity($"saga.{compName}");
        span?.SetTag("saga.id", sagaId);
        span?.SetTag("saga.compensate", compName);

        var result = await ExecuteStep(compName, context);

        await using var logCmd = conn.CreateCommand();
        logCmd.CommandText = "INSERT INTO saga_log (saga_id, step, action, result) VALUES ($1, $2, 'compensate', $3)";
        logCmd.Parameters.AddWithValue(sagaId);
        logCmd.Parameters.AddWithValue(compName);
        logCmd.Parameters.AddWithValue(NpgsqlTypes.NpgsqlDbType.Jsonb, result.ToJsonString());
        await logCmd.ExecuteNonQueryAsync();
    }

    await using var updCmd = conn.CreateCommand();
    updCmd.CommandText = "UPDATE sagas SET status='COMPENSATED', updated_at=now() WHERE id=$1";
    updCmd.Parameters.AddWithValue(sagaId);
    await updCmd.ExecuteNonQueryAsync();
    logger.LogInformation("saga {SagaId} fully compensated", sagaId);
}

// Resume any RUNNING sagas on startup
await using (var conn = await db.OpenConnectionAsync())
{
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "SELECT id FROM sagas WHERE status='RUNNING'";
    await using var reader = await cmd.ExecuteReaderAsync();
    var runningIds = new List<string>();
    while (await reader.ReadAsync())
        runningIds.Add(reader.GetString(0));
    await reader.CloseAsync();

    foreach (var id in runningIds)
    {
        logger.LogInformation("resuming saga {SagaId}", id);
        await Advance(id);
    }
}

app.MapGet("/healthz", () => new { status = "ok" });

app.MapPost("/sagas", async (HttpContext ctx) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var root = doc.RootElement;
    var orderId = root.GetProperty("order_id").GetString()!;
    var sku = root.GetProperty("sku").GetString()!;
    var total = root.GetProperty("total").GetDouble();
    var failShipping = root.TryGetProperty("fail_shipping", out var fs) && fs.GetBoolean();

    var sagaId = Guid.NewGuid().ToString();
    var context = new JsonObject { ["order_id"] = orderId, ["sku"] = sku, ["total"] = total };
    if (failShipping) context["fail_shipping"] = true;

    await using var conn = await db.OpenConnectionAsync();
    await using var insCmd = conn.CreateCommand();
    insCmd.CommandText = "INSERT INTO sagas (id, status, step_index, context) VALUES ($1, 'RUNNING', 0, $2)";
    insCmd.Parameters.AddWithValue(sagaId);
    insCmd.Parameters.AddWithValue(NpgsqlTypes.NpgsqlDbType.Jsonb, context.ToJsonString());
    await insCmd.ExecuteNonQueryAsync();

    await Advance(sagaId);

    await using var selConn = await db.OpenConnectionAsync();
    await using var selCmd = selConn.CreateCommand();
    selCmd.CommandText = "SELECT id, status, step_index, context FROM sagas WHERE id=$1";
    selCmd.Parameters.AddWithValue(sagaId);
    await using var reader = await selCmd.ExecuteReaderAsync();
    await reader.ReadAsync();

    ctx.Response.StatusCode = 201;
    return Results.Json(new
    {
        id = reader.GetString(0),
        status = reader.GetString(1),
        step_index = reader.GetInt32(2),
        context = JsonNode.Parse(reader.GetString(3))
    }, statusCode: 201);
});

app.MapGet("/sagas/{sagaId}", async (string sagaId) =>
{
    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "SELECT id, status, step_index, context FROM sagas WHERE id=$1";
    cmd.Parameters.AddWithValue(sagaId);
    await using var reader = await cmd.ExecuteReaderAsync();
    if (!await reader.ReadAsync())
        return Results.NotFound(new { error = "not found" });

    return Results.Ok(new
    {
        id = reader.GetString(0),
        status = reader.GetString(1),
        step_index = reader.GetInt32(2),
        context = JsonNode.Parse(reader.GetString(3))
    });
});

app.MapGet("/sagas/{sagaId}/log", async (string sagaId) =>
{
    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "SELECT step, action, result FROM saga_log WHERE saga_id=$1 ORDER BY id";
    cmd.Parameters.AddWithValue(sagaId);
    await using var reader = await cmd.ExecuteReaderAsync();

    var logs = new List<object>();
    while (await reader.ReadAsync())
    {
        logs.Add(new
        {
            step = reader.GetString(0),
            action = reader.GetString(1),
            result = reader.IsDBNull(2) ? null : JsonNode.Parse(reader.GetString(2))
        });
    }
    return logs;
});

app.Run();
