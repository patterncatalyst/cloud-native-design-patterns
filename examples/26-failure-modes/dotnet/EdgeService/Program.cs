using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.Extensions.Http.Resilience;
using Polly;
using Polly.CircuitBreaker;
using Polly.RateLimiting;
using Polly.Registry;
using Polly.Timeout;
using System.Diagnostics;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://+:8080");

var backendUrl = builder.Configuration.GetValue("BACKEND_URL", "http://localhost:8081");
builder.Services.AddHttpClient<BackendClient>(c => c.BaseAddress = new Uri(backendUrl));
builder.Services.AddHealthChecks();

// Polly v8 pipelines, one per pattern; each gives up on a single call after 2 s.
var breakerState = new CircuitBreakerStateProvider();
builder.Services.AddResiliencePipeline<string, HttpResponseMessage>("timeout", p => p
    .AddTimeout(TimeSpan.FromSeconds(2)));
builder.Services.AddResiliencePipeline<string, HttpResponseMessage>("retry", p => p
    .AddRetry(new HttpRetryStrategyOptions          // a 5xx, a timeout or a connection failure is retried
    {
        MaxRetryAttempts = 2,
        Delay = TimeSpan.FromMilliseconds(100),
        BackoffType = DelayBackoffType.Exponential,
        UseJitter = true,
        MaxDelay = TimeSpan.FromSeconds(2),
    })
    .AddTimeout(TimeSpan.FromSeconds(2)));
builder.Services.AddResiliencePipeline<string, HttpResponseMessage>("breaker", p => p
    .AddCircuitBreaker(new HttpCircuitBreakerStrategyOptions
    {
        FailureRatio = 1.0,                         // 5 failed calls out of 5 open it
        MinimumThroughput = 5,
        SamplingDuration = TimeSpan.FromSeconds(30),
        BreakDuration = TimeSpan.FromSeconds(10),   // then one trial call decides
        StateProvider = breakerState,
    })
    .AddTimeout(TimeSpan.FromSeconds(2)));
builder.Services.AddResiliencePipeline<string, HttpResponseMessage>("bulkhead", p => p
    .AddConcurrencyLimiter(permitLimit: 5, queueLimit: 0)   // the sixth call is refused at once
    .AddTimeout(TimeSpan.FromSeconds(2)));

var app = builder.Build();

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});

// 1. Timeout
app.MapGet("/with-timeout", async (BackendClient backend, ResiliencePipelineProvider<string> pipelines) =>
{
    var sw = Stopwatch.StartNew();
    try
    {
        var resp = await pipelines.GetPipeline<HttpResponseMessage>("timeout").ExecuteAsync(backend.ProcessAsync);
        return Results.Json(new { status = (int)resp.StatusCode, elapsed_s = Elapsed(sw), body = await BodyAsync(resp) });
    }
    catch (TimeoutRejectedException)
    {
        return Results.Json(new { error = "timeout", elapsed_s = Elapsed(sw), pattern = "timeout" });
    }
});

// 2. Retry with exponential backoff and jitter
app.MapGet("/with-retry", async (BackendClient backend, ResiliencePipelineProvider<string> pipelines) =>
{
    var sw = Stopwatch.StartNew();
    var attempts = 0;
    try
    {
        var resp = await pipelines.GetPipeline<HttpResponseMessage>("retry").ExecuteAsync(ct =>
        {
            attempts++;
            return backend.ProcessAsync(ct);
        });
        if ((int)resp.StatusCode < 500)
            return Results.Json(new { status = (int)resp.StatusCode, attempts, elapsed_s = Elapsed(sw), body = await BodyAsync(resp) });
        return Results.Json(new { error = $"HTTP {(int)resp.StatusCode}", attempts, elapsed_s = Elapsed(sw), pattern = "retry-exhausted" });
    }
    catch (Exception e) when (e is TimeoutRejectedException or HttpRequestException)
    {
        return Results.Json(new { error = "timeout", attempts, elapsed_s = Elapsed(sw), pattern = "retry-exhausted" });
    }
});

// 3. Circuit breaker with a fallback
app.MapGet("/with-breaker", async (BackendClient backend, ResiliencePipelineProvider<string> pipelines) =>
{
    try
    {
        var resp = await pipelines.GetPipeline<HttpResponseMessage>("breaker").ExecuteAsync(backend.ProcessAsync);
        if ((int)resp.StatusCode >= 500)
            return Results.Json(new { source = "fallback", reason = $"upstream_{(int)resp.StatusCode}", breaker = State(breakerState) });
        return Results.Json(new { source = "live", body = await BodyAsync(resp), breaker = State(breakerState) });
    }
    catch (BrokenCircuitException)
    {
        return Results.Json(new { source = "fallback", reason = "circuit_open", breaker = State(breakerState) });
    }
    catch (Exception e) when (e is TimeoutRejectedException or HttpRequestException)
    {
        return Results.Json(new { source = "fallback", reason = "upstream_unreachable", breaker = State(breakerState) });
    }
});

// 4. Deadline propagation
app.MapGet("/with-deadline", async (BackendClient backend, int? budget_ms) =>
{
    var budgetMs = budget_ms ?? 1000;
    var sw = Stopwatch.StartNew();
    var remaining = budgetMs - 50;   // edge overhead

    if (remaining < 50)
        return Results.Json(new { error = "deadline_exceeded", reason = "insufficient budget at edge", budget_ms = budgetMs, remaining_ms = remaining });

    using var cts = new CancellationTokenSource(remaining);
    try
    {
        var resp = await backend.ProcessAsync(cts.Token, remaining);
        return Results.Json(new { status = (int)resp.StatusCode, budget_ms = budgetMs, remaining_ms = remaining, elapsed_s = Elapsed(sw), body = await BodyAsync(resp) });
    }
    catch (OperationCanceledException)
    {
        return Results.Json(new { error = "deadline_exceeded", reason = "timed out waiting for backend", budget_ms = budgetMs, elapsed_s = Elapsed(sw) });
    }
});

// 5. Bulkhead: at most 5 calls in flight
app.MapGet("/with-bulkhead", async (BackendClient backend, ResiliencePipelineProvider<string> pipelines) =>
{
    try
    {
        var resp = await pipelines.GetPipeline<HttpResponseMessage>("bulkhead").ExecuteAsync(backend.ProcessAsync);
        return Results.Json(new { status = (int)resp.StatusCode, body = await BodyAsync(resp) });
    }
    catch (RateLimiterRejectedException)
    {
        return Results.Json(new { error = "bulkhead_full", pattern = "bulkhead" }, statusCode: StatusCodes.Status429TooManyRequests);
    }
    catch (TimeoutRejectedException)
    {
        return Results.Json(new { error = "timeout" });
    }
});

// State endpoints
app.MapGet("/breaker-state", () => new { name = "backend", state = State(breakerState) });
app.MapGet("/bulkhead-state", () => new { max_concurrent = 5 });

app.Run();

static double Elapsed(Stopwatch sw) => Math.Round(sw.Elapsed.TotalSeconds, 2);

static async Task<JsonElement> BodyAsync(HttpResponseMessage resp) =>
    JsonSerializer.Deserialize<JsonElement>(await resp.Content.ReadAsStringAsync());

/// <summary>closed, open or half-open.</summary>
static string State(CircuitBreakerStateProvider provider) => provider.CircuitState switch
{
    CircuitState.Closed => "closed",
    CircuitState.HalfOpen => "half-open",
    _ => "open",
};

/// <summary>Typed client for the backend; the factory manages the handler lifetime.</summary>
public class BackendClient(HttpClient http)
{
    public ValueTask<HttpResponseMessage> ProcessAsync(CancellationToken ct) => new(ProcessAsync(ct, null));

    /// <param name="deadlineMs">When set, sent as X-Deadline-Ms so the backend can reject work it cannot finish.</param>
    public Task<HttpResponseMessage> ProcessAsync(CancellationToken ct, int? deadlineMs)
    {
        var request = new HttpRequestMessage(HttpMethod.Get, "/process");
        if (deadlineMs is { } ms)
            request.Headers.Add("X-Deadline-Ms", ms.ToString());
        return http.SendAsync(request, ct);
    }
}
