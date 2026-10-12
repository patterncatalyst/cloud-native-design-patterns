using BlazorDashboard;
using BlazorDashboard.Components;
using BlazorDashboard.Hubs;
using Microsoft.AspNetCore.SignalR;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var dbUrl = builder.Configuration.GetValue("DATABASE_URL",
    "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass");
var redisConn = builder.Configuration.GetValue("REDIS_URL", "redis:6379");

builder.Services.AddDbContext<OrdersContext>(o => o.UseNpgsql(dbUrl));

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

builder.Services.AddHealthChecks();

var app = builder.Build();

app.UseStaticFiles();
app.UseAntiforgery();

app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.MapHub<OrderHub>("/hubs/orders");

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

app.MapGet("/orders", async (OrdersContext db) =>
    await db.Orders.AsNoTracking().OrderByDescending(o => o.CreatedAt).Take(50)
        .Select(o => OrderDto.From(o)).ToListAsync());

app.MapPost("/orders", async (OrderRequest request, OrdersContext db, IHubContext<OrderHub> hub) =>
{
    var order = new Order
    {
        Id = Guid.NewGuid().ToString(),
        Sku = request.Sku,
        Quantity = request.Quantity,
        Status = "confirmed",
    };
    db.Orders.Add(order);
    await db.SaveChangesAsync();

    var dto = OrderDto.From(order);
    await hub.Clients.Group("dashboard").SendAsync("OrderPlaced", dto);

    return Results.Json(dto, statusCode: StatusCodes.Status201Created);
});

app.Run();
