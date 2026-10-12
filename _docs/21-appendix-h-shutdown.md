---
title: "Graceful Shutdown"
marker: "H"
label: "Appendix H"
order: 21
part: "Deep-dive appendices"
description: "Shutting a pod down without dropping work — a short protocol between the app and Kubernetes: fail readiness first, cover the deregistration race, drain HTTP and consumers inside the grace budget, and stay idempotent for the inevitable hard kill."
duration: 21 minutes
---

This appendix is the operational flip side of factor IX, disposability, from the
Cloud-Native Principles chapter. Pods are cattle: every deploy, scale-down, autoscale
event, or reschedule kills and replaces them, often many times a day. An ungraceful
exit drops in-flight requests, abandons unacked messages, and leaves work half-done —
the scatter of `5xx` blips users notice during an otherwise-healthy rolling
deploy. Graceful shutdown is not a single setting; it is a short protocol the app and
the platform perform together, on a clock: stop taking new work, finish what you
accepted, drain consumers and sockets, then exit before the grace period runs out.

## Disposability is a promise you have to keep

The promise is the second half of factor IX: a process should start fast *and* shut
down cleanly on demand. Cleanly means a definite sequence — stop accepting new work,
finish what you already accepted, release resources, then exit — and the platform hands
you a fixed budget to do it in. Everything in this appendix is that sequence, on both sides of the
app/Kubernetes boundary.

## What happens when Kubernetes stops a pod

When Kubernetes terminates a pod it sends `SIGTERM` to PID 1, starts the
`terminationGracePeriodSeconds` clock, and will `SIGKILL` the process if it overruns.
The subtlety that catches teams out is that removing the pod from the Service endpoints
is **asynchronous** — kube-proxy, the kubelet, and the mesh all have to catch up — so
for a moment *after* `SIGTERM`, traffic can still arrive at a pod that is already
shutting down.

{% include excalidraw.html
   file="21-shutdown-sequence"
   alt="Two lanes on a left-to-right timeline. Kubernetes: SIGTERM to PID 1, grace clock starts (default 30s), endpoint removal is asynchronous, SIGKILL if you overrun. Your pod, triggered by SIGTERM: flip readiness DOWN, preStop sleep about 5 seconds, drain HTTP plus Kafka and sockets and pools, then exit cleanly before the grace period ends. A note says readiness DOWN plus preStop keep new traffic off the dying pod during the async-removal race, and liveness must stay UP throughout."
   caption="Figure H.1 — Shutdown is a timed two-lane protocol; readiness and preStop cover the deregistration race" %}

The pod's side of the contract is five rules:

- `SIGTERM` is the signal — Kubernetes sends it to PID 1, then waits
  `terminationGracePeriodSeconds` (default 30s) before `SIGKILL`.
- **Readiness DOWN** is how you stop *new* traffic: the pod leaves the Service endpoints
  but keeps running to finish in-flight work. Do this first.
- There is a **race** — endpoint removal is asynchronous — so a short `preStop` sleep
  covers the lag while the rest of the cluster stops routing to you.
- **Liveness must stay UP** during the drain, or the kubelet restarts a pod that is
  winding down. This is the distinction people get backwards: you *want*
  readiness to fail, but you must *not* let liveness fail.
- Size the grace period **larger than your longest acceptable in-flight operation** —
  too short cuts work off mid-flight, too long stalls every deploy.

## Graceful means something different per workload

The trap is assuming "graceful shutdown" is one thing. In practice only HTTP request
draining tends to be automatic — the server stops accepting and finishes what is in
flight. Everything else you wire up yourself in the shutdown hook. **Kafka consumers**
stop polling, finish the records already in hand, commit offsets, and leave the group so
the rebalance is clean. **WebSockets** (from the WebSockets appendix) cannot be
"finished," so graceful means sending a close/go-away and leaning on client reconnection
plus the per-connection sequence and backplane. **Jobs and schedulers** stop starting
new work and either let running jobs finish or checkpoint so they resume after restart.
Underneath all of it is the safety net: because a hard `SIGKILL` is always possible,
**idempotent handlers** make a redelivered request or message harmless.

{% include excalidraw.html
   file="21-per-workload"
   alt="Graceful shutdown means something different per workload, in four columns. HTTP REST/gRPC: stop accepting new, finish in-flight requests bounded by a timeout — the one that's automatic. Kafka consumer: stop polling, finish current records, commit offsets, leave the group. WebSocket: send a close or go-away, clients reconnect elsewhere, lean on the per-connection sequence and backplane. Jobs and scheduler: don't start new work, let running jobs finish or checkpoint progress, resume after restart. Underneath: make every handler idempotent, because a hard SIGKILL is always possible."
   caption="Figure H.2 — Only HTTP drains automatically; consumers, sockets, and jobs each need their own shutdown logic, all backed by idempotency" %}

## The application side

The application's job is a short sequence, all driven by one `SIGTERM` (Kubernetes sends
only one, then `SIGKILL` when the grace period runs out): flip readiness down the instant
the signal arrives, keep serving for a short drain delay while the endpoint removal
propagates, then stop accepting and let the HTTP server drain in-flight requests under a
bounded timeout, and finally drain everything else (consumers, pools, sockets) in the
shutdown hook that runs after HTTP is done, and exit 0. Doing the readiness flip *at the
signal* rather than later is what makes it early enough to matter. The tabs are excerpts of
`examples/21-graceful-shutdown`: a 5-second `DRAIN_DELAY_SECONDS` and a 20-second drain
bound, which together fit the 30-second grace period.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// DrainLifecycle.java (excerpt), examples/21-graceful-shutdown/spring-boot
// application.properties: server.shutdown=graceful
//                         spring.lifecycle.timeout-per-shutdown-phase=20s
//                         management.endpoint.health.group.readiness.include=readinessState,db,drain
@Component
class DrainLifecycle implements SmartLifecycle {
    @Override
    public void stop() {                             // SIGTERM: Spring stops the highest phase first
        if (!state.markShuttingDown()) return;       // one SIGTERM drives the drain
        AvailabilityChangeEvent.publish(events, this, ReadinessState.REFUSING_TRAFFIC);
        sleep(drainDelayMillis);                     // DRAIN_DELAY_SECONDS, default 5: keep serving
        // then the graceful web-server phase finishes in-flight requests, and the pool closes
    }
    @Override
    public int getPhase() { return DEFAULT_PHASE - 512; }   // before the web server's own stop
}
// A "drain" HealthIndicator reports DOWN "shutting down", so GET /readyz returns 503 while
// GET /healthz stays 200. Kafka consumers and the scheduler stop with the context.
```

```java
// ShutdownState + DrainReadinessCheck (excerpt), examples/21-graceful-shutdown/quarkus
// application.properties: quarkus.shutdown.delay-enabled=true, delay=5S, timeout=20s
@ApplicationScoped
public class ShutdownState {          // one SIGTERM starts the delay, then HTTP stops, drains
    void onDelayInitiated(@Observes ShutdownDelayInitiatedEvent event) {   // SIGTERM received
        shuttingDown.set(true);            // readiness reports DOWN; the pod keeps serving
        Log.info("SIGTERM received — readiness flipped to 503, draining...");
    }
    void onShutdown(@Observes ShutdownEvent event) {      // delay over: HTTP stops, drains
        Log.infof("shutting down HTTP server (in_flight=%d)", inFlight.get());
    }
}
@Readiness @ApplicationScoped              // /readyz = this check + the datasource check
public class DrainReadinessCheck implements HealthCheck {
    @Inject ShutdownState shutdownState;
    public HealthCheckResponse call() {
        var builder = HealthCheckResponse.named("drain");
        return shutdownState.isShuttingDown()
            ? builder.down().withData("reason", "shutting down").build()
            : builder.up().build();
    }
}
```

```csharp
// Program.cs (excerpt), examples/21-graceful-shutdown/dotnet: the default ConsoleLifetime turns
// one SIGTERM into a graceful stop; the drain is a hosted service's StoppingAsync step
builder.Services.AddSingleton<ShutdownState>();
builder.Services.AddHostedService<DrainService>();
builder.Services.Configure<HostOptions>(o => o.ShutdownTimeout = TimeSpan.FromSeconds(20));
builder.Services.AddHealthChecks()
    .AddCheck<ShutdownHealthCheck>("shutdown", tags: ["ready"])   // /readyz answers 503 once draining
    .AddDbContextCheck<OrdersContext>("database", tags: ["ready"]);
// app.MapHealthChecks("/healthz") always 200, "/readyz" runs the "ready" checks; app.Run();

public sealed class DrainService(ShutdownState state, IConfiguration config, ILogger<DrainService> logger)
    : IHostedLifecycleService
{
    // Every StoppingAsync runs before any StopAsync, and Kestrel stops in StopAsync:
    // the server keeps answering during the delay, then drains in-flight requests.
    public async Task StoppingAsync(CancellationToken cancellationToken)
    {
        state.MarkShuttingDown();                                          // 1. readiness fails first
        var delay = TimeSpan.FromSeconds(config.GetValue("DRAIN_DELAY_SECONDS", 5));
        logger.LogInformation("SIGTERM received, readiness flipped, draining in-flight requests");
        try { await Task.Delay(delay, cancellationToken); }                // 2. serve on: endpoints update
        catch (OperationCanceledException) { }
        logger.LogInformation("shutting down HTTP server (in_flight={InFlight})", state.InFlight);
    }                                                                      // 3. Kestrel stops accepting, finishes
    // 4. the DbContext pool is disposed with the host; the other lifecycle methods return Task.CompletedTask
}
```

```python
# main.py (excerpt), examples/21-graceful-shutdown/python
import asyncio, signal
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
DRAIN_DELAY_SECONDS = 5        # lets endpoint removal propagate (the preStop sleep)
shutting_down, uvicorn_sigterm, loop = False, None, None
def handle_sigterm(signum, frame):
    global shutting_down
    if shutting_down: return     # one SIGTERM drives the whole drain
    shutting_down = True         # fail readiness now, keep serving for the preStop delay
    loop.call_soon_threadsafe(loop.call_later, DRAIN_DELAY_SECONDS,
                              uvicorn_sigterm, signum, frame)   # then uvicorn drains HTTP
@asynccontextmanager
async def lifespan(app):
    global uvicorn_sigterm, loop # uvicorn's handler is already installed: chain to it
    loop = asyncio.get_running_loop()
    uvicorn_sigterm = signal.signal(signal.SIGTERM, handle_sigterm)
    yield                        # --- runs after uvicorn has drained HTTP ---
    await db_pool.close()        # close pools, flush, release resources
app = FastAPI(lifespan=lifespan)
@app.get("/readyz")
async def readyz(): return JSONResponse({}, 503 if shutting_down else 200)
# run: uvicorn main:app --timeout-graceful-shutdown 20   # bounds the HTTP drain
```

```cpp
// order-service (excerpt), examples/21-graceful-shutdown/cpp: one SIGTERM drives the drain
std::atomic<bool> g_shutting_down{false};     // /readyz answers 503 once it is set
std::atomic<int>  g_in_flight{0};             // RAII InFlightGuard: one per request
extern "C" void sigterm_handler(int) {        // async-signal-safe: one atomic store
  g_shutting_down.store(true, std::memory_order_release);
}
void shutdown_watcher() {                     // outside signal context
  while (!g_shutting_down.load(std::memory_order_acquire))
    std::this_thread::sleep_for(50ms);        // (also returns on g_watcher_stop)
  const int delay = std::atoi(env("DRAIN_DELAY_SECONDS", "5"));
  std::this_thread::sleep_for(std::chrono::seconds(delay));    // endpoints update
  const auto deadline = std::chrono::steady_clock::now() + 20s; // bounded in-flight wait
  while (g_in_flight.load() > 0 && std::chrono::steady_clock::now() < deadline)
    std::this_thread::sleep_for(100ms);
  app().quit();                               // stop the listeners: run() returns
}
int main() {
  app().registerBeginningAdvice([] { std::signal(SIGTERM, sigterm_handler); });  // after init
  std::thread watcher(shutdown_watcher);      // ... handlers, addListener("0.0.0.0", 8080)
  app().run();  g_watcher_stop.store(true);  watcher.join();
  g_pool.reset();                             // close the database connections; exit 0
}
```

```go
// main.go (excerpt), examples/21-graceful-shutdown/go: one SIGTERM drives the drain
const shutdownTimeout = 20 * time.Second // drain delay + this stays under the 30s grace
func main() {
	// ... pgx pool, s := &server{pool: pool}; GET /readyz answers 503 once s.shuttingDown
	httpServer := &http.Server{Addr: ":8080", Handler: mux}
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGTERM, syscall.SIGINT)
	defer stop()
	go httpServer.ListenAndServe()
	<-ctx.Done()               // 1. the single SIGTERM
	stop()                     //    a later signal terminates at once
	s.shuttingDown.Store(true) //    readiness fails first, the server keeps serving
	time.Sleep(drainDelay())   // 2. DRAIN_DELAY_SECONDS (5s): endpoints update
	shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
	defer cancel()             // 3. stop accepting, finish in-flight requests
	if err := httpServer.Shutdown(shutdownCtx); err != nil {
		slog.Error("shutdown incomplete", "err", err, "in_flight", s.inFlight.Load())
	}
}                             // 4. deferred pool.Close(), exit 0
```

The same moving parts appear in every stack. A `SIGTERM` handler flips the readiness flag
so the readiness endpoint returns `503` immediately (the "stop new traffic" step,
registered at the signal so it fires before anything else), while `/healthz` stays `200`.
Each runtime's default handler would start the shutdown at once, so the examples take the
signal themselves: a `sun.misc.Signal` handler on the JVM, `PosixSignalRegistration` with a
manual host lifetime in .NET, an async-signal-safe atomic store and a watcher thread in
C++, `signal.NotifyContext` in Go. After `DRAIN_DELAY_SECONDS` (the in-process form of a
`preStop` sleep) the service stops accepting and the HTTP server drains in-flight requests,
bounded by an explicit timeout (`--timeout-graceful-shutdown`, `timeout-per-shutdown-phase`,
`quarkus.shutdown.timeout`, `ShutdownTimeout`, the `Shutdown` context, the C++ deadline) so a
stuck request cannot hang the deploy. In Python the readiness handler takes the place of
uvicorn's own, so it keeps uvicorn's handler and chains to it: the single `SIGTERM` flips
readiness, and after the drain delay the handler hands over to uvicorn, which then drains. A
handler installed at import time, before uvicorn starts, would replace uvicorn's for good and
the server would never drain. And the shutdown hook (FastAPI's `lifespan` after the
`yield`, a Spring `ContextClosedEvent` listener, a Quarkus `ShutdownEvent` observer, a .NET
hosted service's `StopAsync`, the C++ code after `run()` returns) runs once HTTP is done and
is where you stop the consumer (which commits offsets and leaves the group) and close pools
before the process exits 0. The order is the whole point: readiness down, drain delay, drain
HTTP, then drain everything else.

## The Kubernetes side

The platform half of the contract is the same whatever language the service is written
in — three knobs that have to agree with the application's timing.

```yaml
# deployment.yaml — give the pod time to deregister and drain
spec:
  terminationGracePeriodSeconds: 30        # >= preStop + drain + buffer
  containers:
    - name: order-service
      readinessProbe:                      # flips the pod out of the Service
        httpGet: { path: /readyz, port: 8080 }
        periodSeconds: 5
        failureThreshold: 2                # ~10s to stop routing after DOWN
      livenessProbe:                       # must NOT fail during the drain
        httpGet: { path: /healthz, port: 8080 }
      lifecycle:
        preStop:
          exec:
            command: ["sh", "-c", "sleep 5"]   # cover async endpoint removal
```

`terminationGracePeriodSeconds` is the total budget, and it must exceed `preStop` plus
your worst-case drain plus a buffer. The readiness probe's `periodSeconds × failureThreshold`
sets how fast Kubernetes stops routing after you report `DOWN` — roughly ten
seconds here — which your `preStop` sleep should cover. Liveness points at a *separate*
`/healthz` that stays up throughout the drain, so the kubelet does not restart a pod that is
cleanly winding down. The `preStop` sleep looks crude, but it is the pragmatic fix for the
asynchronous-deregistration race; align its duration with the probe timing rather than
picking an arbitrary number.

## Beyond HTTP: messages, sockets, jobs

The shutdown hook is where the non-HTTP drains live, and the Kafka one is worth doing
carefully because it connects to at-least-once delivery from the Event-Driven chapter:
stop polling, finish the records in hand, **commit offsets** on the way out to minimise
redelivery, and **leave the group** so the rebalance is fast. WebSockets cannot be
finished, so graceful there means handing the client off — send a close/go-away and let
it reconnect to another pod, exactly what the WebSockets appendix's reconnection design
enables. Jobs and schedulers stop starting new work and checkpoint so they resume after
restart. And the philosophical anchor of the whole appendix: you *cannot* guarantee a
graceful exit, because the kubelet will sometimes `SIGKILL` you — so idempotency is what
makes the system safe, and graceful shutdown just makes the unsafe window rare.

## Graceful shutdown checklist

Read it as an ordered runbook:

- Handle `SIGTERM`; flip readiness **DOWN first** so the Service stops routing before you
  stop accepting.
- Add a short `preStop` sleep to cover asynchronous endpoint removal; keep **liveness UP**
  throughout the drain.
- Drain in-flight HTTP, commit consumer offsets, close sockets and pools — all bounded by
  `terminationGracePeriodSeconds`.
- Make the work **idempotent** so the inevitable occasional `SIGKILL` is survivable.
- **Test it under a real `SIGTERM` during a rolling deploy** — not just a happy-path
  integration test.

References: the Quarkus lifecycle guide and Markus Eisele's "Quarkus Graceful Shutdown"
(2026); uvicorn's `--timeout-graceful-shutdown`.

### Cross-check it yourself

The one test teams skip is the only one that proves the recipe: a real `SIGTERM` mid-request
during a rollout. Put steady traffic on the service with `hey` (a modest concurrency for a
minute or two), and while it runs, trigger a rolling restart — `kubectl rollout restart
deployment/order-service`. The pass condition is simple and binary: `hey`'s summary shows
**zero non-2xx responses** across the restart. If you see a cluster of `5xx` or connection
resets timed to the restart, walk the protocol backwards — the usual culprit is readiness
not flipping early enough, or a `preStop`/grace-period that is shorter than the real drain.
For the Kafka path, restart a consumer pod mid-stream and confirm from the broker that the
group rebalanced quickly and offsets advanced — no long stall, no large redelivery spike.
A clean rollout under live load, not a green integration test, is evidence that graceful shutdown
works.

---
*Verification status: verified — [`examples/21-graceful-shutdown/`](https://github.com/patterncatalyst/cloud-native-design-patterns/tree/main/examples/21-graceful-shutdown/) passes 17/17 checks in each of the six languages on Docker Engine (2026-10-10)
(one SIGTERM, readiness flip to 503, the drain log lines, exit code 0 inside the grace period, a `docker stop` timing check, restart recovery, and orders persisting across the restart. In-flight request draining is not checked by the script).*
