using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using System.Text.Json;
using Confluent.Kafka;
using StackExchange.Redis;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var legacyUrl = builder.Configuration.GetValue("LEGACY_URL", "http://legacy:8080");
var redisUrl = builder.Configuration.GetValue("REDIS_URL", "redis:6379");
var kafkaBootstrap = builder.Configuration.GetValue("KAFKA_BOOTSTRAP", "kafka:9094");
const int CacheTtl = 60;

builder.Services.AddHttpClient<LegacyClient>(c => c.BaseAddress = new Uri(legacyUrl));
builder.Services.AddHealthChecks();

var app = builder.Build();
var logger = app.Logger;

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

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

app.MapGet("/orders/{orderId}", async (string orderId, LegacyClient legacy) =>
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

    var body = (await legacy.GetOrderAsync(orderId)).Body;
    logger.LogInformation("CACHE_MISS order_id={OrderId}", orderId);

    try
    {
        if (redis is not null)
            await redis.GetDatabase().StringSetAsync(cacheKey, body, TimeSpan.FromSeconds(CacheTtl));
    }
    catch { }

    return Results.Json(JsonSerializer.Deserialize<JsonElement>(body));
});

app.MapPost("/orders", async (HttpContext ctx, LegacyClient legacy) =>
{
    var reqBody = await new StreamReader(ctx.Request.Body).ReadToEndAsync();
    var reply = await legacy.PostOrderAsync(reqBody);
    var body = reply.Body;
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

    ctx.Response.StatusCode = reply.StatusCode;
    ctx.Response.ContentType = "application/json";
    await ctx.Response.WriteAsync(body);
});

app.MapGet("/events", () =>
{
    lock (publishedEvents) return Results.Json(publishedEvents.ToList());
});

app.Run();

public record LegacyReply(int StatusCode, string Body);

/// <summary>Typed client for the legacy order API; the factory manages the handler lifetime.</summary>
public class LegacyClient(HttpClient http)
{
    public Task<LegacyReply> GetOrderAsync(string orderId) =>
        SendAsync(http.GetAsync($"/orders/{orderId}"));

    public Task<LegacyReply> PostOrderAsync(string json) =>
        SendAsync(http.PostAsync("/orders", new StringContent(json, System.Text.Encoding.UTF8, "application/json")));

    private static async Task<LegacyReply> SendAsync(Task<HttpResponseMessage> request)
    {
        using var resp = await request;
        return new LegacyReply((int)resp.StatusCode, await resp.Content.ReadAsStringAsync());
    }
}
