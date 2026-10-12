using System.Runtime.InteropServices;
using Npgsql;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var connString = builder.Configuration.GetConnectionString("Default")
    ?? throw new InvalidOperationException("ConnectionStrings:Default is required");

var dataSource = new NpgsqlDataSourceBuilder(connString).Build();
builder.Services.AddSingleton(dataSource);

// Replace ConsoleLifetime so SIGTERM doesn't stop the server immediately.
// We handle SIGTERM ourselves: flip readiness, wait the pre-stop delay so endpoints update,
// then stop the host (Kestrel stops accepting and finishes in-flight requests).
builder.Services.AddSingleton<IHostLifetime, ManualLifetime>();
builder.Services.Configure<HostOptions>(o => o.ShutdownTimeout = TimeSpan.FromSeconds(20));

var app = builder.Build();
var logger = app.Services.GetRequiredService<ILoggerFactory>().CreateLogger("order-service");

var shuttingDown = false;
var inFlight = 0;

var drainDelay = int.TryParse(Environment.GetEnvironmentVariable("DRAIN_DELAY_SECONDS"), out var d) && d >= 0 ? d : 5;

PosixSignalRegistration.Create(PosixSignal.SIGTERM, ctx =>
{
    ctx.Cancel = true;
    if (shuttingDown) return; // already draining
    shuttingDown = true;
    logger.LogInformation("SIGTERM received — readiness flipped, draining in-flight requests");
    logger.LogInformation("waiting {Delay}s for endpoints to update", drainDelay);
    _ = Task.Run(async () =>
    {
        await Task.Delay(TimeSpan.FromSeconds(drainDelay));
        logger.LogInformation("shutting down HTTP server (in_flight={InFlight})", inFlight);
        app.Lifetime.StopApplication();
    });
});

app.Lifetime.ApplicationStopped.Register(() =>
{
    dataSource.Dispose();
    logger.LogInformation("order-service shutdown complete");
});

app.MapGet("/healthz", () => new { status = "ok" });

app.MapGet("/readyz", async (NpgsqlDataSource db) =>
{
    if (shuttingDown)
        return Results.Json(new { ready = false, reason = "shutting down" }, statusCode: 503);
    try
    {
        await using var conn = await db.OpenConnectionAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT 1";
        await cmd.ExecuteScalarAsync();
        return Results.Ok(new { ready = true });
    }
    catch
    {
        return Results.Json(new { ready = false, reason = "db unreachable" }, statusCode: 503);
    }
});

app.MapPost("/orders", async (HttpContext ctx, NpgsqlDataSource db) =>
{
    if (shuttingDown)
        return Results.Json(new { error = "shutting down" }, statusCode: 503);

    Interlocked.Increment(ref inFlight);
    try
    {
        using var doc = await System.Text.Json.JsonDocument.ParseAsync(ctx.Request.Body);
        var root = doc.RootElement;
        var sku = root.GetProperty("sku").GetString()!;
        var quantity = root.GetProperty("quantity").GetInt32();

        var orderId = Guid.NewGuid().ToString();
        await using var conn = await db.OpenConnectionAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, 'confirmed')";
        cmd.Parameters.AddWithValue(orderId);
        cmd.Parameters.AddWithValue(sku);
        cmd.Parameters.AddWithValue(quantity);
        await cmd.ExecuteNonQueryAsync();

        return Results.Json(new { id = orderId, sku, quantity, status = "confirmed" }, statusCode: 201);
    }
    finally
    {
        Interlocked.Decrement(ref inFlight);
    }
});

app.MapGet("/orders", async (NpgsqlDataSource db) =>
{
    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT 50";
    await using var reader = await cmd.ExecuteReaderAsync();

    var orders = new List<object>();
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

app.MapGet("/debug/state", () =>
    new { shutting_down = shuttingDown, in_flight = inFlight, pid = Environment.ProcessId });

app.Run();

public class ManualLifetime : IHostLifetime
{
    public Task WaitForStartAsync(CancellationToken ct) => Task.CompletedTask;
    public Task StopAsync(CancellationToken ct) => Task.CompletedTask;
}
