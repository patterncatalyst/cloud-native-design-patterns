using System.Collections.Concurrent;
using System.Text.Json;
using Npgsql;
using StackExchange.Redis;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var connStr = builder.Configuration.GetConnectionString("Default")
    ?? "Host=postgres;Port=5432;Database=appdb;Username=appuser;Password=apppass";
var redisUrl = Environment.GetEnvironmentVariable("REDIS_URL") ?? "redis:6379";

var dsBuilder = new NpgsqlDataSourceBuilder(connStr);
var dataSource = dsBuilder.Build();
builder.Services.AddSingleton(dataSource);

ConnectionMultiplexer? redis = null;
try { redis = ConnectionMultiplexer.Connect(redisUrl); }
catch { /* will retry on demand */ }

builder.Services.AddSingleton(new RedisHolder(redis, redisUrl));

var app = builder.Build();
var logger = app.Logger;

const int TTL = 60;

IDatabase? GetRedis()
{
    var holder = app.Services.GetRequiredService<RedisHolder>();
    try
    {
        if (holder.Mux is null || !holder.Mux.IsConnected)
            holder.Mux = ConnectionMultiplexer.Connect(holder.Url);
        return holder.Mux.GetDatabase();
    }
    catch { return null; }
}

// --- Background tasks ---
var cts = new CancellationTokenSource();

_ = Task.Run(async () =>
{
    while (!cts.Token.IsCancellationRequested)
    {
        await Task.Delay(1000, cts.Token).ConfigureAwait(false);
        try
        {
            var db = GetRedis();
            if (db is null) continue;

            var ids = await db.SetPopAsync("metric:dirty", 100);
            if (ids.Length == 0) continue;

            await using var conn = await dataSource.OpenConnectionAsync();
            foreach (var mid in ids)
            {
                var data = await db.HashGetAllAsync($"metric:{mid}");
                if (data.Length > 0)
                {
                    var payload = JsonSerializer.Serialize(
                        data.ToDictionary(e => (string)e.Name!, e => (string)e.Value!));
                    await using var cmd = new NpgsqlCommand(
                        "INSERT INTO metrics (id, payload) VALUES ($1, $2::jsonb) " +
                        "ON CONFLICT (id) DO UPDATE SET payload = $2::jsonb, ts = NOW()", conn);
                    cmd.Parameters.AddWithValue((string)mid!);
                    cmd.Parameters.AddWithValue(payload);
                    await cmd.ExecuteNonQueryAsync();
                }
            }
            logger.LogInformation("flusher: persisted {Count} metrics", ids.Length);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "flusher error");
        }
    }
});

_ = Task.Run(async () =>
{
    while (!cts.Token.IsCancellationRequested)
    {
        await Task.Delay(5000, cts.Token).ConfigureAwait(false);
        try
        {
            var db = GetRedis();
            if (db is null) continue;

            var cutoff = DateTimeOffset.UtcNow.AddSeconds(-300).ToUnixTimeSeconds();
            await db.SortedSetRemoveRangeByScoreAsync("product:hot", 0, cutoff);
            var hotIds = await db.SortedSetRangeByRankAsync("product:hot");
            foreach (var pid in hotIds)
            {
                var ttl = await db.KeyTimeToLiveAsync($"ra:product:{pid}");
                if (ttl.HasValue && ttl.Value.TotalSeconds > 0 && ttl.Value.TotalSeconds < 10)
                {
                    await using var conn = await dataSource.OpenConnectionAsync();
                    await using var cmd = new NpgsqlCommand(
                        "SELECT id, name, price_cents FROM products WHERE id=$1", conn);
                    cmd.Parameters.AddWithValue((string)pid!);
                    await using var reader = await cmd.ExecuteReaderAsync();
                    if (await reader.ReadAsync())
                    {
                        var data = JsonSerializer.Serialize(new
                        {
                            id = reader.GetString(0),
                            name = reader.GetString(1),
                            price_cents = reader.GetInt32(2)
                        });
                        await db.StringSetAsync($"ra:product:{pid}", data, TimeSpan.FromSeconds(TTL));
                        logger.LogInformation("refresher: pre-warmed {Pid}", (string)pid!);
                    }
                }
            }
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "refresher error");
        }
    }
});

app.Lifetime.ApplicationStopping.Register(() => cts.Cancel());

// --- Helpers ---
async Task<string?> SafeCacheGet(string key)
{
    try
    {
        var db = GetRedis();
        if (db is null) return null;
        var val = await db.StringGetAsync(key);
        return val.IsNullOrEmpty ? null : (string?)val;
    }
    catch { return null; }
}

async Task SafeCacheSet(string key, string value, int ttl = TTL)
{
    try { var db = GetRedis(); if (db is not null) await db.StringSetAsync(key, value, TimeSpan.FromSeconds(ttl)); }
    catch { }
}

async Task SafeCacheDelete(string key)
{
    try { var db = GetRedis(); if (db is not null) await db.KeyDeleteAsync(key); }
    catch { }
}

app.MapGet("/healthz", () => new { status = "ok" });

// 1. Cache-aside
app.MapGet("/cache-aside/products/{pid}", async (string pid, NpgsqlDataSource db) =>
{
    var key = $"ca:product:{pid}";
    var cached = await SafeCacheGet(key);
    if (cached is not null)
    {
        var obj = JsonSerializer.Deserialize<JsonElement>(cached);
        return Results.Json(Merge("cache", obj));
    }

    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = new NpgsqlCommand("SELECT id, name, price_cents FROM products WHERE id=$1", conn);
    cmd.Parameters.AddWithValue(pid);
    await using var reader = await cmd.ExecuteReaderAsync();
    if (!await reader.ReadAsync())
        return Results.NotFound(new { error = "not found" });

    var data = new { id = reader.GetString(0), name = reader.GetString(1), price_cents = reader.GetInt32(2) };
    await SafeCacheSet(key, JsonSerializer.Serialize(data));
    return Results.Json(Merge("db", data));
});

app.MapPut("/cache-aside/products/{pid}", async (string pid, HttpContext ctx, NpgsqlDataSource db) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var name = doc.RootElement.GetProperty("name").GetString()!;
    var priceCents = doc.RootElement.GetProperty("price_cents").GetInt32();

    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = new NpgsqlCommand("UPDATE products SET name=$1, price_cents=$2 WHERE id=$3", conn);
    cmd.Parameters.AddWithValue(name);
    cmd.Parameters.AddWithValue(priceCents);
    cmd.Parameters.AddWithValue(pid);
    await cmd.ExecuteNonQueryAsync();

    await SafeCacheDelete($"ca:product:{pid}");
    return Results.Json(new { ok = true, pattern = "cache-aside", action = "invalidated" });
});

// 2. Read-through
app.MapGet("/read-through/products/{pid}", async (string pid, NpgsqlDataSource db) =>
{
    var key = $"rt:product:{pid}";
    var cached = await SafeCacheGet(key);
    if (cached is not null)
    {
        var obj = JsonSerializer.Deserialize<JsonElement>(cached);
        return Results.Json(Merge("cache", obj));
    }

    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = new NpgsqlCommand("SELECT id, name, price_cents FROM products WHERE id=$1", conn);
    cmd.Parameters.AddWithValue(pid);
    await using var reader = await cmd.ExecuteReaderAsync();
    if (!await reader.ReadAsync())
        return Results.NotFound(new { error = "not found" });

    var data = new { id = reader.GetString(0), name = reader.GetString(1), price_cents = reader.GetInt32(2) };
    await SafeCacheSet(key, JsonSerializer.Serialize(data));
    return Results.Json(Merge("db", data));
});

// 3. Write-through
app.MapGet("/write-through/products/{pid}", async (string pid, NpgsqlDataSource db) =>
{
    var key = $"wt:product:{pid}";
    var cached = await SafeCacheGet(key);
    if (cached is not null)
    {
        var obj = JsonSerializer.Deserialize<JsonElement>(cached);
        return Results.Json(Merge("cache", obj));
    }

    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = new NpgsqlCommand("SELECT id, name, price_cents FROM products WHERE id=$1", conn);
    cmd.Parameters.AddWithValue(pid);
    await using var reader = await cmd.ExecuteReaderAsync();
    if (!await reader.ReadAsync())
        return Results.NotFound(new { error = "not found" });

    var data = new { id = reader.GetString(0), name = reader.GetString(1), price_cents = reader.GetInt32(2) };
    await SafeCacheSet(key, JsonSerializer.Serialize(data));
    return Results.Json(Merge("db", data));
});

app.MapPut("/write-through/products/{pid}", async (string pid, HttpContext ctx, NpgsqlDataSource db) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var name = doc.RootElement.GetProperty("name").GetString()!;
    var priceCents = doc.RootElement.GetProperty("price_cents").GetInt32();

    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = new NpgsqlCommand("UPDATE products SET name=$1, price_cents=$2 WHERE id=$3", conn);
    cmd.Parameters.AddWithValue(name);
    cmd.Parameters.AddWithValue(priceCents);
    cmd.Parameters.AddWithValue(pid);
    await cmd.ExecuteNonQueryAsync();

    await using var cmd2 = new NpgsqlCommand("SELECT id, name, price_cents FROM products WHERE id=$1", conn);
    cmd2.Parameters.AddWithValue(pid);
    await using var reader = await cmd2.ExecuteReaderAsync();
    if (await reader.ReadAsync())
    {
        var data = new { id = reader.GetString(0), name = reader.GetString(1), price_cents = reader.GetInt32(2) };
        await SafeCacheSet($"wt:product:{pid}", JsonSerializer.Serialize(data));
    }
    return Results.Json(new { ok = true, pattern = "write-through", action = "set" });
});

// 4. Write-around
app.MapPost("/write-around/events", async (HttpContext ctx, NpgsqlDataSource db) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var id = doc.RootElement.GetProperty("id").GetString()!;
    var type = doc.RootElement.GetProperty("type").GetString()!;
    var payload = doc.RootElement.TryGetProperty("payload", out var p) ? p.GetRawText() : "{}";

    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = new NpgsqlCommand(
        "INSERT INTO events (id, type, payload) VALUES ($1, $2, $3::jsonb)", conn);
    cmd.Parameters.AddWithValue(id);
    cmd.Parameters.AddWithValue(type);
    cmd.Parameters.AddWithValue(payload);
    await cmd.ExecuteNonQueryAsync();

    return Results.Json(new { ok = true, pattern = "write-around", action = "db-only" });
});

app.MapGet("/write-around/events/{eid}", async (string eid, NpgsqlDataSource db) =>
{
    var key = $"wa:event:{eid}";
    var cached = await SafeCacheGet(key);
    if (cached is not null)
    {
        var obj = JsonSerializer.Deserialize<JsonElement>(cached);
        return Results.Json(Merge("cache", obj));
    }

    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = new NpgsqlCommand("SELECT id, type, payload FROM events WHERE id=$1", conn);
    cmd.Parameters.AddWithValue(eid);
    await using var reader = await cmd.ExecuteReaderAsync();
    if (!await reader.ReadAsync())
        return Results.NotFound(new { error = "not found" });

    var data = new
    {
        id = reader.GetString(0),
        type = reader.GetString(1),
        payload = JsonSerializer.Deserialize<JsonElement>(reader.GetString(2))
    };
    await SafeCacheSet(key, JsonSerializer.Serialize(data));
    return Results.Json(Merge("db", data));
});

// 5. Write-back (write-behind)
app.MapPut("/write-back/metrics/{mid}", async (string mid, HttpContext ctx) =>
{
    using var doc = await JsonDocument.ParseAsync(ctx.Request.Body);
    var value = doc.RootElement.GetProperty("value").GetDouble();
    var tags = doc.RootElement.TryGetProperty("tags", out var t) ? t.GetRawText() : "{}";

    var db = GetRedis();
    if (db is null)
        return Results.Json(new { error = "cache unavailable" }, statusCode: 503);

    await db.HashSetAsync($"metric:{mid}", [
        new HashEntry("value", value.ToString()),
        new HashEntry("tags", tags)
    ]);
    await db.SetAddAsync("metric:dirty", mid);
    return Results.Json(new { ok = true, pattern = "write-back", action = "cached-for-flush" });
});

app.MapGet("/write-back/metrics/{mid}", async (string mid, NpgsqlDataSource dbSource) =>
{
    var cache = GetRedis();
    if (cache is not null)
    {
        var data = await cache.HashGetAllAsync($"metric:{mid}");
        if (data.Length > 0)
        {
            var payload = data.ToDictionary(e => (string)e.Name!, e => (string)e.Value!);
            var result = new Dictionary<string, object> { ["source"] = "cache", ["id"] = mid };
            foreach (var kv in payload) result[kv.Key] = kv.Value;
            return Results.Json(result);
        }
    }

    await using var conn = await dbSource.OpenConnectionAsync();
    await using var cmd = new NpgsqlCommand("SELECT id, payload FROM metrics WHERE id=$1", conn);
    cmd.Parameters.AddWithValue(mid);
    await using var reader = await cmd.ExecuteReaderAsync();
    if (!await reader.ReadAsync())
        return Results.NotFound(new { error = "not found" });

    return Results.Json(new
    {
        source = "db",
        id = reader.GetString(0),
        payload = JsonSerializer.Deserialize<JsonElement>(reader.GetString(1))
    });
});

app.MapGet("/write-back/flush-status", async (NpgsqlDataSource dbSource) =>
{
    int dirtyCount = -1;
    try
    {
        var cache = GetRedis();
        if (cache is not null) dirtyCount = (int)await cache.SetLengthAsync("metric:dirty");
    }
    catch { }

    await using var conn = await dbSource.OpenConnectionAsync();
    await using var cmd = new NpgsqlCommand("SELECT count(*) FROM metrics", conn);
    var dbCount = (long)(await cmd.ExecuteScalarAsync())!;

    return Results.Json(new { dirty_keys = dirtyCount, persisted_rows = dbCount });
});

// 6. Refresh-ahead
app.MapGet("/refresh-ahead/products/{pid}", async (string pid, NpgsqlDataSource db) =>
{
    var key = $"ra:product:{pid}";
    try
    {
        var cache = GetRedis();
        if (cache is not null)
            await cache.SortedSetAddAsync("product:hot", pid, DateTimeOffset.UtcNow.ToUnixTimeSeconds());
    }
    catch { }

    var cached = await SafeCacheGet(key);
    if (cached is not null)
    {
        var obj = JsonSerializer.Deserialize<JsonElement>(cached);
        return Results.Json(Merge("cache", obj));
    }

    await using var conn = await db.OpenConnectionAsync();
    await using var cmd = new NpgsqlCommand("SELECT id, name, price_cents FROM products WHERE id=$1", conn);
    cmd.Parameters.AddWithValue(pid);
    await using var reader = await cmd.ExecuteReaderAsync();
    if (!await reader.ReadAsync())
        return Results.NotFound(new { error = "not found" });

    var data = new { id = reader.GetString(0), name = reader.GetString(1), price_cents = reader.GetInt32(2) };
    await SafeCacheSet(key, JsonSerializer.Serialize(data));
    return Results.Json(Merge("db", data));
});

// Debug
app.MapGet("/cache-keys", async () =>
{
    try
    {
        var holder = app.Services.GetRequiredService<RedisHolder>();
        if (holder.Mux is null) return Results.Json(new { keys = Array.Empty<string>(), error = "cache unavailable" });
        var server = holder.Mux.GetServer(holder.Mux.GetEndPoints()[0]);
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
static Dictionary<string, object> Merge(string source, object data)
{
    var result = new Dictionary<string, object> { ["source"] = source };
    if (data is JsonElement je)
    {
        foreach (var prop in je.EnumerateObject())
            result[prop.Name] = prop.Value.ValueKind switch
            {
                JsonValueKind.Number => (object)prop.Value.GetInt32(),
                JsonValueKind.String => prop.Value.GetString()!,
                _ => prop.Value.Clone()
            };
    }
    else
    {
        foreach (var prop in data.GetType().GetProperties())
            result[prop.Name] = prop.GetValue(data)!;
    }
    return result;
}

public class RedisHolder(ConnectionMultiplexer? mux, string url)
{
    public ConnectionMultiplexer? Mux { get; set; } = mux;
    public string Url { get; } = url;
}
