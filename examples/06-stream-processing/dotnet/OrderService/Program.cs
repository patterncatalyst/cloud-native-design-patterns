using System.Text.Json;
using Confluent.Kafka;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.AspNetCore.Http.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var dbUrl = builder.Configuration.GetValue("DATABASE_URL",
    "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass");
var kafkaBootstrap = builder.Configuration.GetValue("KAFKA_BOOTSTRAP", "kafka:9094");

builder.Services.AddDbContext<OrdersContext>(o => o.UseNpgsql(dbUrl));

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order-service"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddOtlpExporter(o => o.Endpoint = new Uri(
            builder.Configuration.GetValue("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318"))));

// The REST and Kafka payloads use snake_case field names (merchant_id).
builder.Services.ConfigureHttpJsonOptions(opts =>
    opts.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower);

builder.Services.AddHealthChecks();

var app = builder.Build();

IProducer<Null, string>? producer = null;
for (var i = 0; i < 30; i++)
{
    try
    {
        producer = new ProducerBuilder<Null, string>(
            new ProducerConfig { BootstrapServers = kafkaBootstrap }).Build();
        break;
    }
    catch
    {
        app.Logger.LogWarning("Kafka not ready, retry {Attempt}/30", i + 1);
        Thread.Sleep(2000);
    }
}

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

app.MapPost("/orders", async (OrderRequest request, OrdersContext db, IOptions<JsonOptions> json) =>
{
    var order = new Order
    {
        Id = Guid.NewGuid().ToString(),
        MerchantId = request.MerchantId,
        Sku = request.Sku,
        Quantity = request.Quantity,
        Total = (decimal)request.Total,
        Status = "confirmed",
    };
    db.Orders.Add(order);
    await db.SaveChangesAsync();

    var placed = new OrderPlaced(order.Id, order.MerchantId, order.Sku, order.Quantity, request.Total, order.Status);
    if (producer is not null)
    {
        try
        {
            await producer.ProduceAsync("order.placed", new Message<Null, string>
            {
                Value = JsonSerializer.Serialize(placed, json.Value.SerializerOptions),
            });
        }
        catch { }
    }

    return Results.Json(placed, statusCode: StatusCodes.Status201Created);
});

app.MapGet("/orders", async (OrdersContext db) =>
    await db.Orders.AsNoTracking().OrderByDescending(o => o.CreatedAt).Take(50)
        .Select(o => OrderDto.From(o)).ToListAsync());

app.Run();
