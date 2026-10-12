using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Diagnostics.HealthChecks;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var connString = builder.Configuration.GetConnectionString("Default")
    ?? throw new InvalidOperationException("ConnectionStrings:Default is required");

builder.Services.AddDbContext<OrdersContext>(o => o.UseNpgsql(connString));

// The default console lifetime turns one SIGTERM into a graceful stop; the drain runs in
// DrainService.StoppingAsync and ShutdownTimeout bounds the whole stop.
builder.Services.AddSingleton<ShutdownState>();
builder.Services.AddHostedService<DrainService>();
builder.Services.Configure<HostOptions>(o => o.ShutdownTimeout = TimeSpan.FromSeconds(20));

builder.Services.AddHealthChecks()
    .AddCheck<ShutdownHealthCheck>("shutdown", tags: ["ready"])
    .AddDbContextCheck<OrdersContext>("database", tags: ["ready"]);

var app = builder.Build();

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    Predicate = _ => false,
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

app.MapHealthChecks("/readyz", new HealthCheckOptions
{
    Predicate = r => r.Tags.Contains("ready"),
    ResponseWriter = (ctx, report) =>
    {
        if (report.Status == HealthStatus.Healthy)
            return ctx.Response.WriteAsJsonAsync(new { ready = true });
        var reason = report.Entries.TryGetValue("shutdown", out var s) && s.Status != HealthStatus.Healthy
            ? "shutting down"
            : "db unreachable";
        return ctx.Response.WriteAsJsonAsync(new { ready = false, reason });
    },
});

app.MapPost("/orders", async (OrderRequest request, OrdersContext db, ShutdownState state) =>
{
    if (state.ShuttingDown)
        return Results.Json(new { error = "shutting down" }, statusCode: StatusCodes.Status503ServiceUnavailable);

    state.Enter();
    try
    {
        var order = new Order { Sku = request.Sku, Quantity = request.Quantity };
        db.Orders.Add(order);
        await db.SaveChangesAsync();
        return Results.Json(OrderDto.From(order), statusCode: StatusCodes.Status201Created);
    }
    finally
    {
        state.Exit();
    }
});

app.MapGet("/orders", async (OrdersContext db) =>
    await db.Orders.AsNoTracking().OrderByDescending(o => o.CreatedAt).Take(50)
        .Select(o => OrderDto.From(o)).ToListAsync());

app.MapGet("/debug/state", (ShutdownState state) =>
    new { shutting_down = state.ShuttingDown, in_flight = state.InFlight, pid = Environment.ProcessId });

app.Run();
