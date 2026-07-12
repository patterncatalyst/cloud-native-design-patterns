using Npgsql;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8081");

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order-api"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter(o => o.Endpoint = new Uri(
            Environment.GetEnvironmentVariable("OTEL_EXPORTER_OTLP_ENDPOINT") ?? "http://lgtm:4318")));

var app = builder.Build();

var dbUrl = Environment.GetEnvironmentVariable("DATABASE_URL")
    ?? "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass";
var dsBuilder = new NpgsqlDataSourceBuilder(dbUrl);
await using var dataSource = dsBuilder.Build();

app.MapGet("/healthz", () => new { status = "ok" });

app.MapGet("/orders", async (int? limit) =>
{
    var lim = limit is > 0 ? limit.Value : 50;
    var orders = new List<object>();
    await using var conn = await dataSource.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "SELECT id, sku, quantity, status FROM orders ORDER BY id LIMIT $1";
    cmd.Parameters.AddWithValue(lim);
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

app.MapGet("/orders/{orderId}", async (string orderId) =>
{
    await using var conn = await dataSource.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "SELECT id, sku, quantity, status FROM orders WHERE id = $1";
    cmd.Parameters.AddWithValue(orderId);
    await using var reader = await cmd.ExecuteReaderAsync();
    if (await reader.ReadAsync())
    {
        return Results.Json(new
        {
            id = reader.GetString(0),
            sku = reader.GetString(1),
            quantity = reader.GetInt32(2),
            status = reader.GetString(3)
        });
    }
    return Results.NotFound();
});

app.Run();
