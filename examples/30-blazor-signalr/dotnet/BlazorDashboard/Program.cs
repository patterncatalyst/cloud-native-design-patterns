using System.Text.Json;
using BlazorDashboard;
using BlazorDashboard.Components;
using BlazorDashboard.Hubs;
using Microsoft.AspNetCore.SignalR;
using Npgsql;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var dbUrl = Environment.GetEnvironmentVariable("DATABASE_URL")
    ?? "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass";
var redisConn = Environment.GetEnvironmentVariable("REDIS_URL") ?? "redis:6379";

builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

builder.Services.AddSignalR()
    .AddStackExchangeRedis(redisConn, options =>
        options.Configuration.ChannelPrefix =
            StackExchange.Redis.RedisChannel.Literal("cndp-signalr"));

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("blazor-dashboard"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddSource("blazor-dashboard")
        .AddOtlpExporter());

var dsBuilder = new NpgsqlDataSourceBuilder(dbUrl);
await using var dataSource = dsBuilder.Build();

var app = builder.Build();

app.UseStaticFiles();
app.UseAntiforgery();

app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.MapHub<OrderHub>("/hubs/orders");

app.MapGet("/healthz", () => new { status = "ok" });

app.MapGet("/orders", async () =>
{
    var orders = new List<OrderDto>();
    await using var conn = await dataSource.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT 50";
    await using var reader = await cmd.ExecuteReaderAsync();
    while (await reader.ReadAsync())
    {
        orders.Add(new OrderDto(
            reader.GetString(0), reader.GetString(1),
            reader.GetInt32(2), reader.GetString(3)));
    }
    return orders;
});

app.MapPost("/orders", async (HttpContext ctx, IHubContext<OrderHub> hub) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var root = doc.RootElement;
    var sku = root.GetProperty("sku").GetString()!;
    var quantity = root.GetProperty("quantity").GetInt32();
    var id = Guid.NewGuid().ToString();

    await using var conn = await dataSource.OpenConnectionAsync();
    await using var cmd = conn.CreateCommand();
    cmd.CommandText = "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4)";
    cmd.Parameters.AddWithValue(id);
    cmd.Parameters.AddWithValue(sku);
    cmd.Parameters.AddWithValue(quantity);
    cmd.Parameters.AddWithValue("confirmed");
    await cmd.ExecuteNonQueryAsync();

    var order = new OrderDto(id, sku, quantity, "confirmed");
    await hub.Clients.Group("dashboard").SendAsync("OrderPlaced", order);

    return Results.Json(order, statusCode: 201);
});

app.Run();
