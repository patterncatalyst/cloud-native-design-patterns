using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using StackExchange.Redis;

/// <summary>The shared Redis connection, re-established on demand so a Redis restart is survivable.</summary>
public sealed class RedisHolder(string url, ILogger<RedisHolder> logger) : IDisposable
{
    private ConnectionMultiplexer? _mux;

    public ConnectionMultiplexer? Mux => _mux;

    public IDatabase? GetDatabase()
    {
        try
        {
            if (_mux is null || !_mux.IsConnected)
                _mux = ConnectionMultiplexer.Connect(url);
            return _mux.GetDatabase();
        }
        catch (Exception ex)
        {
            logger.LogDebug(ex, "redis unavailable");
            return null;
        }
    }

    public void Dispose() => _mux?.Dispose();
}

/// <summary>
/// Write-back flusher. A failed upsert is re-queued, with exponential backoff between flush cycles and a
/// bounded number of attempts per id. After MaxFlushAttempts the id moves to metric:failed (its value stays
/// in the cache) and is logged, never dropped silently.
/// </summary>
public sealed class MetricFlusher(RedisHolder redis, IDbContextFactory<CacheContext> dbFactory, ILogger<MetricFlusher> logger)
    : BackgroundService
{
    private const int MaxFlushAttempts = 5;
    private const int FlushPeriodMs = 1000;
    private const int MaxFlushBackoffMs = 8000;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var failures = 0;
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await Task.Delay(Math.Min(FlushPeriodMs << failures, MaxFlushBackoffMs), stoppingToken);
                failures = await FlushOnceAsync(failures, stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "flusher error");
            }
        }
    }

    private async Task<int> FlushOnceAsync(int failures, CancellationToken ct)
    {
        var db = redis.GetDatabase();
        if (db is null) return failures;

        var ids = await db.SetPopAsync("metric:dirty", 100);
        if (ids.Length == 0) return failures;

        var failed = new List<RedisValue>();
        foreach (var mid in ids)
        {
            try
            {
                var data = await db.HashGetAllAsync($"metric:{mid}");
                if (data.Length > 0)
                {
                    var payload = JsonSerializer.Serialize(data.ToDictionary(e => (string)e.Name!, e => (string)e.Value!));
                    await using var ctx = await dbFactory.CreateDbContextAsync(ct);
                    await ctx.UpsertMetricAsync((string)mid!, payload, ct);
                }
                await db.HashDeleteAsync("metric:attempts", mid);
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                logger.LogError(ex, "flusher: flush failed for {Id}", (string?)mid);
                failed.Add(mid);
            }
        }

        logger.LogInformation("flusher: persisted {Count} metrics", ids.Length - failed.Count);
        if (failed.Count == 0) return 0;

        await RequeueAsync(db, failed);
        return Math.Min(failures + 1, 3);
    }

    private async Task RequeueAsync(IDatabase db, IEnumerable<RedisValue> failed)
    {
        foreach (var mid in failed)
        {
            var n = await db.HashIncrementAsync("metric:attempts", mid, 1);
            if (n >= MaxFlushAttempts)
            {
                await db.SetAddAsync("metric:failed", mid);
                await db.HashDeleteAsync("metric:attempts", mid);
                logger.LogError("flusher: giving up on {Id} after {Attempts} attempts, parked on metric:failed", (string?)mid, n);
            }
            else
            {
                await db.SetAddAsync("metric:dirty", mid);
                logger.LogWarning("flusher: re-queued {Id} (attempt {Attempt}/{Max})", (string?)mid, n, MaxFlushAttempts);
            }
        }
    }
}

/// <summary>Refresh-ahead: pre-warms hot products whose cache entry is about to expire.</summary>
public sealed class HotProductRefresher(RedisHolder redis, IDbContextFactory<CacheContext> dbFactory, ILogger<HotProductRefresher> logger)
    : BackgroundService
{
    private const int Ttl = 60;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(5));
        try
        {
            while (await timer.WaitForNextTickAsync(stoppingToken))
            {
                try
                {
                    await RefreshOnceAsync(stoppingToken);
                }
                catch (Exception ex) when (ex is not OperationCanceledException)
                {
                    logger.LogError(ex, "refresher error");
                }
            }
        }
        catch (OperationCanceledException)
        {
        }
    }

    private async Task RefreshOnceAsync(CancellationToken ct)
    {
        var db = redis.GetDatabase();
        if (db is null) return;

        var cutoff = DateTimeOffset.UtcNow.AddSeconds(-300).ToUnixTimeSeconds();
        await db.SortedSetRemoveRangeByScoreAsync("product:hot", 0, cutoff);
        foreach (var pid in await db.SortedSetRangeByRankAsync("product:hot"))
        {
            var ttl = await db.KeyTimeToLiveAsync($"ra:product:{pid}");
            if (ttl is not { TotalSeconds: > 0 and < 10 }) continue;

            var id = (string)pid!;
            await using var ctx = await dbFactory.CreateDbContextAsync(ct);
            var product = await ctx.Products.AsNoTracking().Where(p => p.Id == id)
                .Select(p => ProductDto.From(p)).FirstOrDefaultAsync(ct);
            if (product is null) continue;

            await db.StringSetAsync($"ra:product:{pid}", JsonSerializer.Serialize(product, CacheJson.Options), TimeSpan.FromSeconds(Ttl));
            logger.LogInformation("refresher: pre-warmed {Pid}", (string)pid!);
        }
    }
}

public static class CacheJson
{
    /// <summary>Cached and returned JSON uses snake_case field names (price_cents).</summary>
    public static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web)
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    };
}
