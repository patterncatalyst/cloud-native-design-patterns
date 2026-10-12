using Microsoft.Extensions.Diagnostics.HealthChecks;
using Microsoft.Extensions.Options;

/// <summary>Shutdown flag and in-flight count, shared by the endpoints, the drain service and the readiness check.</summary>
public class ShutdownState
{
    private int _inFlight;

    public bool ShuttingDown { get; private set; }
    public int InFlight => Volatile.Read(ref _inFlight);

    public void MarkShuttingDown() => ShuttingDown = true;
    public void Enter() => Interlocked.Increment(ref _inFlight);
    public void Exit() => Interlocked.Decrement(ref _inFlight);
}

/// <summary>
/// Pre-stop drain. The host runs every StoppingAsync before any StopAsync, and Kestrel stops in
/// StopAsync, so the server keeps answering during the delay. HostOptions.ShutdownTimeout bounds
/// the whole stop.
/// </summary>
public sealed class DrainService(ShutdownState state, IConfiguration config, ILogger<DrainService> logger)
    : IHostedLifecycleService
{
    public async Task StoppingAsync(CancellationToken cancellationToken)
    {
        state.MarkShuttingDown();
        var delay = TimeSpan.FromSeconds(config.GetValue("DRAIN_DELAY_SECONDS", 5));
        logger.LogInformation("SIGTERM received, readiness flipped, draining in-flight requests");
        logger.LogInformation("waiting {Delay}s for endpoints to update", delay.TotalSeconds);
        try
        {
            await Task.Delay(delay, cancellationToken);
        }
        catch (OperationCanceledException)
        {
        }
        logger.LogInformation("shutting down HTTP server (in_flight={InFlight})", state.InFlight);
    }

    public Task StartingAsync(CancellationToken cancellationToken) => Task.CompletedTask;
    public Task StartAsync(CancellationToken cancellationToken) => Task.CompletedTask;
    public Task StartedAsync(CancellationToken cancellationToken) => Task.CompletedTask;
    public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;
    public Task StoppedAsync(CancellationToken cancellationToken) => Task.CompletedTask;
}

public sealed class ShutdownHealthCheck(ShutdownState state) : IHealthCheck
{
    public Task<HealthCheckResult> CheckHealthAsync(HealthCheckContext context, CancellationToken cancellationToken = default) =>
        Task.FromResult(state.ShuttingDown
            ? HealthCheckResult.Unhealthy("shutting down")
            : HealthCheckResult.Healthy());
}
