using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8081");

var dbUrl = builder.Configuration.GetValue("DATABASE_URL",
    "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass");
builder.Services.AddDbContext<OrdersContext>(o => o.UseNpgsql(dbUrl));

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order-api"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter(o => o.Endpoint = new Uri(
            builder.Configuration.GetValue("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318"))));

builder.Services.AddHealthChecks();

var app = builder.Build();

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

app.MapGet("/orders", async (int? limit, OrdersContext db) =>
{
    var lim = limit is > 0 ? limit.Value : 50;
    return await db.Orders.AsNoTracking().OrderBy(o => o.Id).Take(lim).Select(o => OrderDto.From(o)).ToListAsync();
});

app.MapGet("/orders/{orderId}", async (string orderId, OrdersContext db) =>
    await db.Orders.AsNoTracking().Where(o => o.Id == orderId).Select(o => OrderDto.From(o)).FirstOrDefaultAsync()
        is { } order
        ? Results.Json(order)
        : Results.NotFound());

app.Run();
