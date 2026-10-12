using System.Globalization;
using System.Text.Json;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Caching.Hybrid;
using StackExchange.Redis;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var connStr = builder.Configuration.GetConnectionString("Default")
    ?? "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass";
var redisUrl = builder.Configuration.GetValue("REDIS_URL", "redis:6379");
const int TTL = 60;

// A factory for the background services; request handlers get a scoped context made by the same factory.
builder.Services.AddDbContextFactory<CacheContext>(o => o.UseNpgsql(connStr));
builder.Services.AddScoped(sp => sp.GetRequiredService<IDbContextFactory<CacheContext>>().CreateDbContext());

// Read-through goes through HybridCache (in-process L1, Redis L2). The other strategies spell out the
// cache steps on a plain Redis client, because the strategy itself is the lesson.
builder.Services.AddStackExchangeRedisCache(o => o.Configuration = redisUrl);
builder.Services.AddHybridCache(o => o.DefaultEntryOptions = new HybridCacheEntryOptions
{
    Expiration = TimeSpan.FromSeconds(TTL),
    LocalCacheExpiration = TimeSpan.FromSeconds(TTL),
});

builder.Services.AddSingleton(sp => new RedisHolder(redisUrl, sp.GetRequiredService<ILogger<RedisHolder>>()));
builder.Services.AddHostedService<MetricFlusher>();
builder.Services.AddHostedService<HotProductRefresher>();

// Request and response bodies use snake_case field names (price_cents).
builder.Services.ConfigureHttpJsonOptions(opts => opts.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower);
builder.Services.AddHealthChecks();

var app = builder.Build();

var redis = app.Services.GetRequiredService<RedisHolder>();

async Task<string?> SafeCacheGet(string key)
{
    try
    {
        var db = redis.GetDatabase();
        if (db is null) return null;
        var val = await db.StringGetAsync(key);
        return val.IsNullOrEmpty ? null : (string?)val;
    }
    catch { return null; }
}

async Task SafeCacheSet(string key, string value, int ttl = TTL)
{
    try { var db = redis.GetDatabase(); if (db is not null) await db.StringSetAsync(key, value, TimeSpan.FromSeconds(ttl)); }
    catch { }
}

async Task SafeCacheDelete(string key)
{
    try { var db = redis.GetDatabase(); if (db is not null) await db.KeyDeleteAsync(key); }
    catch { }
}

/// <summary>Cache-aside read of one product: the explicit get, load, set steps, tagged with where the answer came from.</summary>
async Task<IResult> CachedProduct(string prefix, string pid, CacheContext db, Func<Task>? onRead = null)
{
    if (onRead is not null) await onRead();
    var key = $"{prefix}:product:{pid}";
    var cached = await SafeCacheGet(key);
    if (cached is not null)
        return Results.Json(Merge("cache", JsonSerializer.Deserialize<JsonElement>(cached)));

    var product = await db.Products.AsNoTracking().Where(p => p.Id == pid)
        .Select(p => ProductDto.From(p)).FirstOrDefaultAsync();
    if (product is null)
        return Results.NotFound(new { error = "not found" });

    await SafeCacheSet(key, JsonSerializer.Serialize(product, CacheJson.Options));
    return Results.Json(Merge("db", product));
}

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

// 1. Cache-aside
app.MapGet("/cache-aside/products/{pid}", (string pid, CacheContext db) => CachedProduct("ca", pid, db));

app.MapPut("/cache-aside/products/{pid}", async (string pid, ProductUpdate update, CacheContext db) =>
{
    await db.Products.Where(p => p.Id == pid)
        .ExecuteUpdateAsync(s => s.SetProperty(p => p.Name, update.Name).SetProperty(p => p.PriceCents, update.PriceCents));

    await SafeCacheDelete($"ca:product:{pid}");
    return Results.Json(new { ok = true, pattern = "cache-aside", action = "invalidated" });
});

// 2. Read-through: HybridCache runs the loader on a miss and stores the result in L1 and Redis.
app.MapGet("/read-through/products/{pid}", async (string pid, CacheContext db, HybridCache cache) =>
{
    var key = $"rt:product:{pid}";
    var source = "cache";
    var product = await cache.GetOrCreateAsync<ProductDto?>(key, async ct =>
    {
        source = "db";
        return await db.Products.AsNoTracking().Where(p => p.Id == pid)
            .Select(p => ProductDto.From(p)).FirstOrDefaultAsync(ct);
    });

    if (product is null)
    {
        await cache.RemoveAsync(key);
        return Results.NotFound(new { error = "not found" });
    }
    return Results.Json(Merge(source, product));
});

// 3. Write-through
app.MapGet("/write-through/products/{pid}", (string pid, CacheContext db) => CachedProduct("wt", pid, db));

app.MapPut("/write-through/products/{pid}", async (string pid, ProductUpdate update, CacheContext db) =>
{
    await db.Products.Where(p => p.Id == pid)
        .ExecuteUpdateAsync(s => s.SetProperty(p => p.Name, update.Name).SetProperty(p => p.PriceCents, update.PriceCents));

    var product = await db.Products.AsNoTracking().Where(p => p.Id == pid)
        .Select(p => ProductDto.From(p)).FirstOrDefaultAsync();
    if (product is not null)
        await SafeCacheSet($"wt:product:{pid}", JsonSerializer.Serialize(product, CacheJson.Options));
    return Results.Json(new { ok = true, pattern = "write-through", action = "set" });
});

// 4. Write-around
app.MapPost("/write-around/events", async (EventRequest request, CacheContext db) =>
{
    db.Events.Add(new EventRecord
    {
        Id = request.Id,
        Type = request.Type,
        Payload = request.Payload ?? JsonSerializer.SerializeToElement(new { }),
    });
    await db.SaveChangesAsync();

    return Results.Json(new { ok = true, pattern = "write-around", action = "db-only" });
});

app.MapGet("/write-around/events/{eid}", async (string eid, CacheContext db) =>
{
    var key = $"wa:event:{eid}";
    var cached = await SafeCacheGet(key);
    if (cached is not null)
        return Results.Json(Merge("cache", JsonSerializer.Deserialize<JsonElement>(cached)));

    var evt = await db.Events.AsNoTracking().Where(e => e.Id == eid)
        .Select(e => EventDto.From(e)).FirstOrDefaultAsync();
    if (evt is null)
        return Results.NotFound(new { error = "not found" });

    await SafeCacheSet(key, JsonSerializer.Serialize(evt, CacheJson.Options));
    return Results.Json(Merge("db", evt));
});

// 5. Write-back (write-behind)
app.MapPut("/write-back/metrics/{mid}", async (string mid, MetricRequest request) =>
{
    var db = redis.GetDatabase();
    if (db is null)
        return Results.Json(new { error = "cache unavailable" }, statusCode: StatusCodes.Status503ServiceUnavailable);

    await db.HashSetAsync($"metric:{mid}", [
        new HashEntry("value", request.Value.ToString(CultureInfo.InvariantCulture)),
        new HashEntry("tags", request.Tags?.GetRawText() ?? "{}")
    ]);
    await db.SetAddAsync("metric:dirty", mid);
    // 202: queued in the cache, not yet durable in Postgres
    return Results.Json(new { ok = true, pattern = "write-back", action = "cached-for-flush" },
        statusCode: StatusCodes.Status202Accepted);
});

app.MapGet("/write-back/metrics/{mid}", async (string mid, CacheContext db) =>
{
    var cache = redis.GetDatabase();
    if (cache is not null)
    {
        var data = await cache.HashGetAllAsync($"metric:{mid}");
        if (data.Length > 0)
        {
            var result = new Dictionary<string, object> { ["source"] = "cache", ["id"] = mid };
            foreach (var entry in data) result[(string)entry.Name!] = (string)entry.Value!;
            return Results.Json(result);
        }
    }

    var row = await db.Metrics.AsNoTracking().FirstOrDefaultAsync(m => m.Id == mid);
    return row is null
        ? Results.NotFound(new { error = "not found" })
        : Results.Json(new { source = "db", id = row.Id, payload = row.Payload });
});

app.MapGet("/write-back/flush-status", async (CacheContext db) =>
{
    int dirtyCount = -1;
    try
    {
        var cache = redis.GetDatabase();
        if (cache is not null) dirtyCount = (int)await cache.SetLengthAsync("metric:dirty");
    }
    catch { }

    return Results.Json(new { dirty_keys = dirtyCount, persisted_rows = await db.Metrics.LongCountAsync() });
});

// 6. Refresh-ahead
app.MapGet("/refresh-ahead/products/{pid}", (string pid, CacheContext db) =>
    CachedProduct("ra", pid, db, async () =>
    {
        try
        {
            var cache = redis.GetDatabase();
            if (cache is not null)
                await cache.SortedSetAddAsync("product:hot", pid, DateTimeOffset.UtcNow.ToUnixTimeSeconds());
        }
        catch { }
    }));

// Debug
app.MapGet("/cache-keys", async () =>
{
    try
    {
        redis.GetDatabase();
        var mux = redis.Mux;
        if (mux is null) return Results.Json(new { keys = Array.Empty<string>(), error = "cache unavailable" });
        var server = mux.GetServer(mux.GetEndPoints()[0]);
        var keys = new List<string>();
        await foreach (var key in server.KeysAsync())
            keys.Add(key.ToString());
        keys.Sort();
        return Results.Json(new { keys });
    }
    catch
    {
        return Results.Json(new { keys = Array.Empty<string>(), error = "cache unavailable" });
    }
});

app.Run();

// --- Helpers ---
/// <summary>Flattens a cached or loaded document into one JSON object led by its "source".</summary>
static Dictionary<string, object> Merge(string source, object data)
{
    var element = data is JsonElement je ? je : JsonSerializer.SerializeToElement(data, CacheJson.Options);
    var result = new Dictionary<string, object> { ["source"] = source };
    foreach (var prop in element.EnumerateObject())
        result[prop.Name] = prop.Value.ValueKind switch
        {
            JsonValueKind.Number => prop.Value.GetInt32(),
            JsonValueKind.String => prop.Value.GetString()!,
            _ => prop.Value.Clone()
        };
    return result;
}
