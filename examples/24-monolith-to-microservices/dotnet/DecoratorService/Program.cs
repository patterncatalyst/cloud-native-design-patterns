using System.Text.Json;
using Confluent.Kafka;
using StackExchange.Redis;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");
var app = builder.Build();
var logger = app.Logger;

var legacyUrl = Environment.GetEnvironmentVariable("LEGACY_URL") ?? "http://legacy:8080";
var redisUrl = Environment.GetEnvironmentVariable("REDIS_URL") ?? "redis:6379";
var kafkaBootstrap = Environment.GetEnvironmentVariable("KAFKA_BOOTSTRAP") ?? "kafka:9094";
const int CacheTtl = 60;

var httpClient = new HttpClient { BaseAddress = new Uri(legacyUrl) };

ConnectionMultiplexer? redis = null;
for (var i = 0; i < 10; i++)
{
    try { redis = ConnectionMultiplexer.Connect(redisUrl); break; }
    catch { Thread.Sleep(2000); }
}

IProducer<Null, string>? producer = null;
for (var i = 0; i < 30; i++)
{
    try
    {
        producer = new ProducerBuilder<Null, string>(
            new ProducerConfig { BootstrapServers = kafkaBootstrap }).Build();
        producer.Flush(TimeSpan.FromSeconds(1));
        logger.LogInformation("Kafka producer connected");
        break;
    }
    catch
    {
        logger.LogWarning("Kafka not ready, retry {Attempt}/30", i + 1);
        Thread.Sleep(2000);
    }
}

var publishedEvents = new List<Dictionary<string, object>>();

app.MapGet("/healthz", () => new { status = "ok" });

app.MapGet("/orders/{orderId}", async (string orderId) =>
{
    var cacheKey = $"order:{orderId}";
    try
    {
        if (redis is not null)
        {
            var cached = await redis.GetDatabase().StringGetAsync(cacheKey);
            if (!cached.IsNullOrEmpty)
            {
                logger.LogInformation("CACHE_HIT order_id={OrderId}", orderId);
                return Results.Json(JsonSerializer.Deserialize<JsonElement>((string)cached!));
            }
        }
    }
    catch { }

    var resp = await httpClient.GetAsync($"/orders/{orderId}");
    var body = await resp.Content.ReadAsStringAsync();
    logger.LogInformation("CACHE_MISS order_id={OrderId}", orderId);

    try
    {
        if (redis is not null)
            await redis.GetDatabase().StringSetAsync(cacheKey, body, TimeSpan.FromSeconds(CacheTtl));
    }
    catch { }

    return Results.Json(JsonSerializer.Deserialize<JsonElement>(body));
});

app.MapPost("/orders", async (HttpContext ctx) =>
{
    var reqBody = await new StreamReader(ctx.Request.Body).ReadToEndAsync();
    var resp = await httpClient.PostAsync("/orders",
        new StringContent(reqBody, System.Text.Encoding.UTF8, "application/json"));
    var body = await resp.Content.ReadAsStringAsync();
    var data = JsonSerializer.Deserialize<JsonElement>(body);

    var orderId = data.TryGetProperty("id", out var idProp) ? idProp.GetString() ?? "" : "";
    var evt = new Dictionary<string, object> { ["event"] = "order.placed", ["order_id"] = orderId };
    using var reqDoc = JsonDocument.Parse(reqBody);
    foreach (var prop in reqDoc.RootElement.EnumerateObject())
        evt[prop.Name] = prop.Value.Clone();

    lock (publishedEvents) publishedEvents.Add(evt);

    if (producer is not null)
    {
        try
        {
            producer.Produce("order.placed", new Message<Null, string> { Value = JsonSerializer.Serialize(evt) });
            logger.LogInformation("EVENT order.placed → Kafka order_id={OrderId}", orderId);
        }
        catch (Exception ex)
        {
            logger.LogWarning("Kafka publish failed: {Error}", ex.Message);
        }
    }

    ctx.Response.StatusCode = (int)resp.StatusCode;
    ctx.Response.ContentType = "application/json";
    await ctx.Response.WriteAsync(body);
});

app.MapGet("/events", () =>
{
    lock (publishedEvents) return Results.Json(publishedEvents.ToList());
});

app.Run();
