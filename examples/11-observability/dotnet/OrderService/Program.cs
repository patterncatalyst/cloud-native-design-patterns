using System.Diagnostics;
using System.Diagnostics.Metrics;
using System.Text;
using System.Text.Json;
using Confluent.Kafka;
using Grpc.Net.Client;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Proto;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var dbUrl = builder.Configuration.GetValue("DATABASE_URL",
    "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass");
var kafkaBootstrap = builder.Configuration.GetValue("KAFKA_BOOTSTRAP", "kafka:9094");
var inventoryAddr = builder.Configuration.GetValue("INVENTORY_ADDR", "inventory:50051");

builder.Services.AddDbContext<OrdersContext>(o => o.UseNpgsql(dbUrl));

builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order-service"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddSource("order-service")
        .AddOtlpExporter())
    .WithMetrics(m => m
        .AddMeter("order-service")
        .AddOtlpExporter());

builder.Services.AddHealthChecks();

var app = builder.Build();

var channel = GrpcChannel.ForAddress($"http://{inventoryAddr}",
    new GrpcChannelOptions { HttpHandler = new SocketsHttpHandler { EnableMultipleHttp2Connections = true } });
var inventoryClient = new InventoryService.InventoryServiceClient(channel);

IProducer<Null, string>? producer = null;
for (var i = 0; i < 30; i++)
{
    try
    {
        producer = new ProducerBuilder<Null, string>(
            new ProducerConfig { BootstrapServers = kafkaBootstrap }).Build();
        break;
    }
    catch { Thread.Sleep(2000); }
}

var activitySource = new ActivitySource("order-service");
var meter = new Meter("order-service");
var ordersPlaced = meter.CreateCounter<long>("orders.placed");

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

app.MapPost("/orders", async (OrderRequest request, OrdersContext db) =>
{
    var (sku, quantity) = request;
    var id = Guid.NewGuid().ToString();

    using var reserveSpan = activitySource.StartActivity("reserve-stock");
    reserveSpan?.SetTag("sku", sku);
    reserveSpan?.SetTag("quantity", quantity);

    var reply = await inventoryClient.ReserveStockAsync(
        new ReserveRequest { Sku = sku, Quantity = quantity });
    var status = reply.Confirmed ? "confirmed" : "rejected";
    reserveSpan?.SetTag("stock.confirmed", reply.Confirmed);

    var order = new Order { Id = id, Sku = sku, Quantity = quantity, Status = status };
    db.Orders.Add(order);
    await db.SaveChangesAsync();

    var dto = OrderDto.From(order);
    var json = JsonSerializer.Serialize(dto, JsonSerializerOptions.Web);

    if (producer is not null)
    {
        var headers = new Headers();
        if (Activity.Current is { } activity)
        {
            var traceparent = $"00-{activity.TraceId}-{activity.SpanId}-{(activity.Recorded ? "01" : "00")}";
            headers.Add("traceparent", Encoding.UTF8.GetBytes(traceparent));
        }

        try
        {
            await producer.ProduceAsync("order.placed",
                new Message<Null, string> { Value = json, Headers = headers });
        }
        catch { }
    }

    ordersPlaced.Add(1,
        new KeyValuePair<string, object?>("sku", sku),
        new KeyValuePair<string, object?>("status", status));

    var traceId = Activity.Current?.TraceId.ToString() ?? "".PadLeft(32, '0');
    var spanId = Activity.Current?.SpanId.ToString() ?? "".PadLeft(16, '0');
    app.Logger.LogInformation("[trace_id={TraceId} span_id={SpanId}] order placed id={OrderId}",
        traceId, spanId, id);

    return Results.Json(dto, statusCode: StatusCodes.Status201Created);
});

app.MapGet("/orders", async (OrdersContext db) =>
    await db.Orders.AsNoTracking().OrderByDescending(o => o.CreatedAt).Take(50)
        .Select(o => OrderDto.From(o)).ToListAsync());

app.Run();
