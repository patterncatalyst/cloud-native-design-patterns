using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Npgsql;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var connString = builder.Configuration.GetConnectionString("Default")
    ?? throw new InvalidOperationException("ConnectionStrings:Default is required");

builder.Services.AddDbContext<OrdersContext>(o => o.UseNpgsql(connString));

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

builder.Services.AddHealthChecks()
    .AddDbContextCheck<OrdersContext>("database", tags: ["ready"]);

var app = builder.Build();

var serviceVersion = builder.Configuration["SERVICE_VERSION"] ?? "0.0.0";

app.MapGet("/", () => new { service = "order-service", version = serviceVersion, config_source = "environment" });

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
        var up = report.Status == HealthStatus.Healthy;
        return ctx.Response.WriteAsJsonAsync(new
        {
            status = up ? "ready" : "down",
            checks = new { database = up ? "ok" : "unreachable" },
        });
    },
});

app.MapGet("/orders", async (OrdersContext db) =>
    await db.Orders.AsNoTracking().OrderBy(o => o.Id).Select(o => OrderDto.From(o)).ToListAsync());

app.MapPost("/orders", async (string customer, decimal total, OrdersContext db, ILogger<Program> logger) =>
{
    var order = new Order { Customer = customer, Total = total };
    db.Orders.Add(order);
    await db.SaveChangesAsync();
    var dto = OrderDto.From(order);
    logger.LogInformation("order_created id={Id} customer={Customer} total={Total:F2}",
        dto.Id, dto.Customer, dto.Total);
    return TypedResults.Ok(dto);
});

app.Run();
