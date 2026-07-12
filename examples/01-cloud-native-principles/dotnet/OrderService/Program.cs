using Npgsql;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using System.Text.Json;
using System.Text.Json.Serialization;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var connString = builder.Configuration.GetConnectionString("Default")
    ?? throw new InvalidOperationException("ConnectionStrings:Default is required");

var dataSource = new NpgsqlDataSourceBuilder(connString).Build();
builder.Services.AddSingleton(dataSource);

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order-service"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddNpgsql()
        .AddOtlpExporter());

builder.Services.ConfigureHttpJsonOptions(opts =>
{
    opts.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower;
    opts.SerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
});

var app = builder.Build();

var serviceVersion = Environment.GetEnvironmentVariable("SERVICE_VERSION") ?? "0.0.0";
var logger = app.Services.GetRequiredService<ILoggerFactory>().CreateLogger("order-service");

app.MapGet("/", () => new { service = "order-service", version = serviceVersion, config_source = "environment" });

app.MapGet("/healthz", () => new { status = "ok" });

app.MapGet("/readyz", async (NpgsqlDataSource db) =>
{
    try
    {
        await using var conn = await db.OpenConnectionAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT 1";
        await cmd.ExecuteScalarAsync();
        return Results.Ok(new { status = "ready", checks = new { database = "ok" } });
    }
    catch
    {
        return Results.Ok(new { status = "down", checks = new { database = "unreachable" } });
    }
});

app.MapGet("/orders", async (NpgsqlDataSource db) =>
{
    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "SELECT id, customer, total FROM orders ORDER BY id";
    await using var reader = await cmd.ExecuteReaderAsync();

    var orders = new List<object>();
    while (await reader.ReadAsync())
    {
        orders.Add(new
        {
            id = reader.GetInt32(0),
            customer = reader.GetString(1),
            total = reader.GetDecimal(2)
        });
    }
    return orders;
});

app.MapPost("/orders", async (HttpContext ctx, NpgsqlDataSource db) =>
{
    var customer = ctx.Request.Query["customer"].ToString();
    var total = decimal.Parse(ctx.Request.Query["total"]!);

    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "INSERT INTO orders (customer, total) VALUES ($1, $2) RETURNING id, customer, total";
    cmd.Parameters.AddWithValue(customer);
    cmd.Parameters.AddWithValue(total);
    await using var reader = await cmd.ExecuteReaderAsync();
    await reader.ReadAsync();

    var order = new
    {
        id = reader.GetInt32(0),
        customer = reader.GetString(1),
        total = reader.GetDecimal(2)
    };

    logger.LogInformation("order_created id={Id} customer={Customer} total={Total:F2}",
        order.id, order.customer, order.total);

    return Results.Ok(order);
});

app.Run();
