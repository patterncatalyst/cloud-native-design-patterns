using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using Npgsql;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var connStr = builder.Configuration.GetConnectionString("Default")
    ?? "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass";

builder.Services.AddDbContext<OrdersContext>(o => o.UseNpgsql(connStr));

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddNpgsql()
        .AddOtlpExporter());

builder.Services.ConfigureHttpJsonOptions(opts =>
    opts.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower);

builder.Services.AddHealthChecks();

var app = builder.Build();

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

// The order and its outbox row commit in one SaveChangesAsync, which is one transaction.
app.MapPost("/orders", async (OrderRequest request, OrdersContext db) =>
{
    var order = new Order
    {
        Id = Guid.NewGuid().ToString(),
        Sku = request.Sku,
        Quantity = request.Quantity,
        Status = "confirmed",
    };
    var dto = OrderDto.From(order);
    db.Orders.Add(order);
    db.Outbox.Add(new OutboxEvent
    {
        AggregateId = order.Id,
        EventType = "order.placed",
        Payload = JsonSerializer.SerializeToElement(dto, JsonSerializerOptions.Web),
    });
    await db.SaveChangesAsync();

    return Results.Json(dto, statusCode: StatusCodes.Status201Created);
});

app.MapGet("/orders", async (OrdersContext db, int limit = 50) =>
    await db.Orders.AsNoTracking().OrderByDescending(o => o.CreatedAt).Take(Math.Min(limit, 100))
        .Select(o => OrderDto.From(o)).ToListAsync());

app.MapGet("/outbox", async (OrdersContext db, int limit = 50) =>
    await db.Outbox.AsNoTracking().OrderByDescending(e => e.Id).Take(Math.Min(limit, 100))
        .Select(e => OutboxDto.From(e)).ToListAsync());

app.Run();
