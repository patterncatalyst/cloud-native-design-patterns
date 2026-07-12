using System.Text.Json;
using Npgsql;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var connStr = builder.Configuration.GetConnectionString("Default")
    ?? "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass";

var dsBuilder = new NpgsqlDataSourceBuilder(connStr);
var dataSource = dsBuilder.Build();
builder.Services.AddSingleton(dataSource);

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddNpgsql()
        .AddOtlpExporter());

var app = builder.Build();

app.MapGet("/healthz", () => new { status = "ok" });

app.MapPost("/orders", async (HttpContext ctx, NpgsqlDataSource db) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var root = doc.RootElement;
    var sku = root.GetProperty("sku").GetString()!;
    var quantity = root.GetProperty("quantity").GetInt32();
    var orderId = Guid.NewGuid().ToString();

    await using var conn = await db.OpenConnectionAsync();
    await using var tx = await conn.BeginTransactionAsync();

    await using (var cmd = new NpgsqlCommand(
        "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, 'confirmed')", conn, tx))
    {
        cmd.Parameters.AddWithValue(orderId);
        cmd.Parameters.AddWithValue(sku);
        cmd.Parameters.AddWithValue(quantity);
        await cmd.ExecuteNonQueryAsync();
    }

    var payload = JsonSerializer.Serialize(new { id = orderId, sku, quantity, status = "confirmed" });
    await using (var cmd = new NpgsqlCommand(
        "INSERT INTO outbox (aggregate_id, event_type, payload) VALUES ($1, $2, $3::jsonb)", conn, tx))
    {
        cmd.Parameters.AddWithValue(orderId);
        cmd.Parameters.AddWithValue("order.placed");
        cmd.Parameters.AddWithValue(payload);
        await cmd.ExecuteNonQueryAsync();
    }

    await tx.CommitAsync();

    return Results.Json(new { id = orderId, sku, quantity, status = "confirmed" }, statusCode: 201);
});

app.MapGet("/orders", async (NpgsqlDataSource db, int limit = 50) =>
{
    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = new NpgsqlCommand(
        "SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT $1", conn);
    cmd.Parameters.AddWithValue(Math.Min(limit, 100));
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

app.MapGet("/outbox", async (NpgsqlDataSource db, int limit = 50) =>
{
    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = new NpgsqlCommand(
        "SELECT id, aggregate_id, event_type, payload, created_at FROM outbox ORDER BY id DESC LIMIT $1", conn);
    cmd.Parameters.AddWithValue(Math.Min(limit, 100));
    await using var reader = await cmd.ExecuteReaderAsync();

    var rows = new List<object>();
    while (await reader.ReadAsync())
    {
        rows.Add(new
        {
            id = reader.GetInt64(0),
            aggregate_id = reader.GetString(1),
            event_type = reader.GetString(2),
            payload = JsonSerializer.Deserialize<JsonElement>(reader.GetString(3)),
            created_at = reader.GetDateTime(4).ToString("o")
        });
    }
    return rows;
});

app.Run();
