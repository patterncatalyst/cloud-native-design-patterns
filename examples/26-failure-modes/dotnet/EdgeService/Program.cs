using System.Diagnostics;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");
var app = builder.Build();

var backendUrl = Environment.GetEnvironmentVariable("BACKEND_URL") ?? "http://localhost:8081";
var httpClient = new HttpClient { BaseAddress = new Uri(backendUrl) };

// --- Circuit Breaker ---
var cbState = "closed";
var cbFailureCount = 0;
var cbSuccessCount = 0;
const int CbThreshold = 5;
const int CbResetTimeout = 10;
var cbOpenedAt = 0L;
var cbTotalCalls = 0;
var cbTotalRejected = 0;
var cbLock = new object();

bool CbAllow()
{
    lock (cbLock)
    {
        if (cbState == "closed") return true;
        if (cbState == "open")
        {
            if (Stopwatch.GetElapsedTime(cbOpenedAt).TotalSeconds >= CbResetTimeout)
            {
                cbState = "half-open";
                cbSuccessCount = 0;
                return true;
            }
            return false;
        }
        return true;
    }
}

void CbRecordSuccess()
{
    lock (cbLock)
    {
        cbTotalCalls++;
        if (cbState == "half-open")
        {
            cbSuccessCount++;
            if (cbSuccessCount >= 2)
            {
                cbState = "closed";
                cbFailureCount = 0;
            }
        }
        else
        {
            cbFailureCount = 0;
        }
    }
}

void CbRecordFailure()
{
    lock (cbLock)
    {
        cbTotalCalls++;
        cbFailureCount++;
        if (cbState == "half-open")
        {
            cbState = "open";
            cbOpenedAt = Stopwatch.GetTimestamp();
        }
        else if (cbFailureCount >= CbThreshold)
        {
            cbState = "open";
            cbOpenedAt = Stopwatch.GetTimestamp();
        }
    }
}

object CbInfo()
{
    lock (cbLock)
    {
        return new
        {
            name = "backend",
            state = cbState,
            failure_count = cbFailureCount,
            threshold = CbThreshold,
            total_calls = cbTotalCalls,
            total_rejected = cbTotalRejected
        };
    }
}

// --- Bulkhead ---
var bulkheadSem = new SemaphoreSlim(5, 5);
var bulkheadRejected = 0;
var bulkheadActive = 0;

// --- Endpoints ---

app.MapGet("/healthz", () => new { status = "ok" });

// 1. With timeout
app.MapGet("/with-timeout", async () =>
{
    var sw = Stopwatch.StartNew();
    using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(2));
    try
    {
        var resp = await httpClient.GetAsync("/process", cts.Token);
        var elapsed = Math.Round(sw.Elapsed.TotalSeconds, 2);
        var body = JsonSerializer.Deserialize<JsonElement>(await resp.Content.ReadAsStringAsync());
        return Results.Json(new { status = (int)resp.StatusCode, elapsed_s = elapsed, body });
    }
    catch (OperationCanceledException)
    {
        var elapsed = Math.Round(sw.Elapsed.TotalSeconds, 2);
        return Results.Json(new { error = "timeout", elapsed_s = elapsed, pattern = "timeout" });
    }
});

// 2. With retry + exponential backoff + jitter
app.MapGet("/with-retry", async () =>
{
    var sw = Stopwatch.StartNew();
    var attempts = 0;
    string? lastError = null;
    var wait = 0.1;
    var random = new Random();

    using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(2));

    for (var attempt = 1; attempt <= 3; attempt++)
    {
        attempts = attempt;
        try
        {
            var resp = await httpClient.GetAsync("/process", cts.Token);
            if ((int)resp.StatusCode < 500)
            {
                var elapsed = Math.Round(sw.Elapsed.TotalSeconds, 2);
                var body = JsonSerializer.Deserialize<JsonElement>(await resp.Content.ReadAsStringAsync());
                return Results.Json(new { status = (int)resp.StatusCode, attempts, elapsed_s = elapsed, body });
            }
            lastError = $"HTTP {(int)resp.StatusCode}";
        }
        catch (OperationCanceledException)
        {
            lastError = "timeout";
        }

        if (attempt < 3)
        {
            var jitter = random.NextDouble() * wait * 0.5;
            await Task.Delay(TimeSpan.FromSeconds(wait + jitter));
            wait = Math.Min(wait * 2, 2.0);
        }
    }

    var finalElapsed = Math.Round(sw.Elapsed.TotalSeconds, 2);
    return Results.Json(new { error = lastError, attempts, elapsed_s = finalElapsed, pattern = "retry-exhausted" });
});

// 3. With circuit breaker + fallback
app.MapGet("/with-breaker", async () =>
{
    if (!CbAllow())
    {
        lock (cbLock) cbTotalRejected++;
        return Results.Json(new { source = "fallback", reason = "circuit_open", breaker = cbState });
    }

    using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(2));
    try
    {
        var resp = await httpClient.GetAsync("/process", cts.Token);
        if ((int)resp.StatusCode >= 500)
        {
            CbRecordFailure();
            return Results.Json(new { source = "fallback", reason = $"upstream_{(int)resp.StatusCode}", breaker = cbState });
        }
        CbRecordSuccess();
        var body = JsonSerializer.Deserialize<JsonElement>(await resp.Content.ReadAsStringAsync());
        return Results.Json(new { source = "live", body, breaker = cbState });
    }
    catch (Exception)
    {
        CbRecordFailure();
        return Results.Json(new { source = "fallback", reason = "upstream_unreachable", breaker = cbState });
    }
});

// 4. Deadline propagation
app.MapGet("/with-deadline", async (HttpContext ctx) =>
{
    var budgetMs = 1000;
    var budgetParam = ctx.Request.Query["budget_ms"].FirstOrDefault();
    if (budgetParam is not null && int.TryParse(budgetParam, out var parsed))
        budgetMs = parsed;

    var sw = Stopwatch.StartNew();
    const int edgeOverhead = 50;
    var remaining = budgetMs - edgeOverhead;

    if (remaining < 50)
    {
        return Results.Json(new
        {
            error = "deadline_exceeded",
            reason = "insufficient budget at edge",
            budget_ms = budgetMs,
            remaining_ms = remaining
        });
    }

    using var cts = new CancellationTokenSource(remaining);
    var req = new HttpRequestMessage(HttpMethod.Get, "/process");
    req.Headers.Add("X-Deadline-Ms", remaining.ToString());

    try
    {
        var resp = await httpClient.SendAsync(req, cts.Token);
        var elapsed = Math.Round(sw.Elapsed.TotalSeconds, 2);
        var body = JsonSerializer.Deserialize<JsonElement>(await resp.Content.ReadAsStringAsync());
        return Results.Json(new
        {
            status = (int)resp.StatusCode,
            budget_ms = budgetMs,
            remaining_ms = remaining,
            elapsed_s = elapsed,
            body
        });
    }
    catch (OperationCanceledException)
    {
        var elapsed = Math.Round(sw.Elapsed.TotalSeconds, 2);
        return Results.Json(new
        {
            error = "deadline_exceeded",
            reason = "timed out waiting for backend",
            budget_ms = budgetMs,
            elapsed_s = elapsed
        });
    }
});

// 5. Bulkhead — bounded concurrency
app.MapGet("/with-bulkhead", async () =>
{
    if (!bulkheadSem.Wait(0))
    {
        Interlocked.Increment(ref bulkheadRejected);
        return Results.Json(new { error = "bulkhead_full", pattern = "bulkhead", active = bulkheadActive });
    }

    Interlocked.Increment(ref bulkheadActive);
    try
    {
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(2));
        var resp = await httpClient.GetAsync("/process", cts.Token);
        var body = JsonSerializer.Deserialize<JsonElement>(await resp.Content.ReadAsStringAsync());
        return Results.Json(new { status = (int)resp.StatusCode, body, active_slots = bulkheadActive });
    }
    catch (OperationCanceledException)
    {
        return Results.Json(new { error = "timeout", active_slots = bulkheadActive });
    }
    finally
    {
        Interlocked.Decrement(ref bulkheadActive);
        bulkheadSem.Release();
    }
});

// State endpoints
app.MapGet("/breaker-state", () => CbInfo());

app.MapGet("/bulkhead-state", () => new
{
    max_concurrent = 5,
    active = bulkheadActive,
    rejected = bulkheadRejected
});

app.Run();
