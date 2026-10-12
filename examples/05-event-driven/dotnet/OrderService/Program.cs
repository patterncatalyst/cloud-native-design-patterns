using System.Diagnostics;
using System.Text;
using System.Text.Json;
using Confluent.Kafka;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using OpenTelemetry;
using OpenTelemetry.Context.Propagation;
using OpenTelemetry.Exporter;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

// Producer spans come from this source; AddSource below makes the SDK record and export them.
var orderSource = new ActivitySource("order-service");

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
        .AddSource("order-service")
        // 4318 is the OTLP/HTTP port: the exporter defaults to gRPC, and a code-set endpoint is used as given.
        .AddOtlpExporter(o =>
        {
            var endpoint = builder.Configuration.GetValue("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318");
            o.Endpoint = new Uri(endpoint.TrimEnd('/') + "/v1/traces");
            o.Protocol = OtlpExportProtocol.HttpProtobuf;
        }));

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

app.MapPost("/orders", async (OrderRequest request, OrdersContext db) =>
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
    var json = JsonSerializer.Serialize(dto, JsonSerializerOptions.Web);

    if (producer is not null)
    {
        Activity? publish = null;
        try
        {
            // Confluent.Kafka has no built-in tracing: write the W3C traceparent into the record headers
            // so the consumers can continue this trace.
            publish = orderSource.StartActivity("order.placed publish", ActivityKind.Producer);
            publish?.SetTag("messaging.system", "kafka");
            publish?.SetTag("messaging.destination.name", "order.placed");
            var message = new Message<Null, string> { Value = json, Headers = new Headers() };
            Propagators.DefaultTextMapPropagator.Inject(
                new PropagationContext(publish?.Context ?? Activity.Current?.Context ?? default, Baggage.Current),
                message.Headers,
                (headers, key, value) => headers.Add(key, Encoding.UTF8.GetBytes(value)));
            await producer.ProduceAsync("order.placed", message);
        }
        catch (Exception ex)
        {
            publish?.SetStatus(ActivityStatusCode.Error, ex.Message);
            app.Logger.LogWarning("Kafka publish failed: {Error}", ex.Message);
        }
        finally
        {
            publish?.Dispose();
        }
    }

    return Results.Json(dto, statusCode: StatusCodes.Status201Created);
});

app.MapGet("/orders", async (OrdersContext db) =>
    await db.Orders.AsNoTracking().OrderByDescending(o => o.CreatedAt).Take(50)
        .Select(o => OrderDto.From(o)).ToListAsync());

app.Run();
