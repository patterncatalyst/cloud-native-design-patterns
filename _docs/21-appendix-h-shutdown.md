---
title: "Graceful Shutdown"
marker: "H"
label: "Appendix H"
order: 21
part: "Deep-dive appendices"
description: "Shutting a pod down without dropping work — a short protocol between the app and Kubernetes: fail readiness first, cover the deregistration race, drain HTTP and consumers inside the grace budget, and stay idempotent for the inevitable hard kill."
duration: 18 minutes
---

This appendix is the operational flip side of factor IX, disposability, from the
Cloud-Native Principles chapter. Pods are cattle: every deploy, scale-down, autoscale
event, or reschedule kills and replaces them, often many times a day. An ungraceful
exit drops in-flight requests, abandons unacked messages, and leaves work half-done —
the scatter of `5xx` blips users actually notice during an otherwise-healthy rolling
deploy. Graceful shutdown is not a single setting; it is a short protocol the app and
the platform perform together, on a clock: stop taking new work, finish what you
accepted, drain consumers and sockets, then exit before the grace period runs out.

## Disposability is a promise you have to keep

The promise is the second half of factor IX: a process should start fast *and* shut
down cleanly on demand. Cleanly means a definite sequence — stop accepting new work,
finish what you already accepted, release resources, then exit — and the platform hands
you a fixed budget to do it in. Everything below is that sequence, on both sides of the
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
  deliberately winding down. This is the distinction people get backwards: you *want*
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

## The application side

The application's job is three steps in order: flip readiness down the instant `SIGTERM`
arrives, let the HTTP server drain in-flight requests under a bounded timeout, then drain
everything else — consumers, pools, sockets — in the shutdown hook that runs after HTTP
is done. Doing the readiness flip *at the signal* rather than later is what makes it
early enough to matter.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

```java
// application.yml — enable graceful shutdown and bound the drain:
//   server.shutdown: graceful
//   spring.lifecycle.timeout-per-shutdown-phase: 15s

// flip readiness DOWN explicitly so Kubernetes stops routing first
@Component
public class ShutdownLifecycle {
    private final ApplicationEventPublisher events;
    private final Consumer<?, ?> consumer;     // Kafka consumer

    public ShutdownLifecycle(ApplicationEventPublisher e, Consumer<?, ?> c) {
        this.events = e; this.consumer = c;
    }

    @EventListener(ContextClosedEvent.class)
    public void onShutdown(ContextClosedEvent e) {
        events.publishEvent(new AvailabilityChangeEvent<>(this,
            ReadinessState.REFUSING_TRAFFIC));      // readiness → DOWN
        log.info("draining");
        consumer.wakeup();                          // stop polling; commit on close
    }
}
// HTTP drains automatically (server.shutdown=graceful);
// Kafka, the scheduler, and WebSockets you drain yourself in onShutdown.
```

```java
// application.properties — the 'graceful' profile:
//   quarkus.shutdown.timeout=15s          (runtime: wait for in-flight HTTP)
//   quarkus.shutdown.delay-enabled=true   (BUILD time — must be baked in)
//   quarkus.shutdown.delay=5s             (pre-shutdown phase: readiness DOWN)

// observe the lifecycle so the sequence is visible in the logs
@ApplicationScoped
public class ShutdownLifecycle {
    void onDelay(@Observes ShutdownDelayInitiatedEvent e) {
        Log.info("readiness now DOWN — HTTP still draining"); // SmallRye reports it
    }
    void onStop(@Observes ShutdownEvent e) {
        Log.info("draining"); consumer.close(); pool.close();   // your drain code
    }
}
// HTTP drains automatically (Quarkus 3.32+ answers instead of 503-ing);
// Kafka, the scheduler and WebSockets you drain in onStop yourself.
```

```csharp
// Program.cs — set the budget; the host honours it on SIGTERM
builder.Services.Configure<HostOptions>(o =>
{
    o.ShutdownTimeout = TimeSpan.FromSeconds(30);     // total budget
    o.BackgroundServiceExceptionBehavior =            // tolerate handler errors
        BackgroundServiceExceptionBehavior.Ignore;
});

// Flip readiness DOWN on shutdown via a mutable IHealthCheck
public class ReadinessCheck : IHealthCheck
{
    private volatile bool _ready = true;
    public void MarkUnready() => _ready = false;
    public Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext ctx, CancellationToken ct) =>
        Task.FromResult(_ready ? HealthCheckResult.Healthy() : HealthCheckResult.Unhealthy());
}

// One BackgroundService per long-running concern; StopAsync gets the drain hook
public class KafkaConsumerHost(IConsumer<string, Order> consumer,
                               ReadinessCheck readiness,
                               IHostApplicationLifetime lifetime) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            var result = consumer.Consume(ct);
            await Handle(result, ct);                 // your work
            consumer.Commit(result);                  // ack after side-effect
        }
    }
    public override async Task StopAsync(CancellationToken ct)        // ← the drain hook
    {
        readiness.MarkUnready();                      // /healthz/ready → 503
        consumer.Close();                             // commit + leave group cleanly
        await base.StopAsync(ct);                     // bounded by ShutdownTimeout
    }
}
```

```python
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse

ready = True                     # the flag the readiness probe reads
def _drain(*_):                  # SIGTERM -> fail readiness FIRST
    global ready; ready = False  # Service stops routing new traffic
signal.signal(signal.SIGTERM, _drain)

@asynccontextmanager
async def lifespan(app):
    yield                        # --- shutdown runs after HTTP has drained ---
    await consumer.stop()        # aiokafka: finish, commit offsets, leave group
    await db.close()             # close pools, flush, release resources

app = FastAPI(lifespan=lifespan)
@app.get("/readyz")
async def readyz(): return JSONResponse({}, 200 if ready else 503)
# run: uvicorn app:app --timeout-graceful-shutdown 15   # bounds the HTTP drain
```

```cpp
// Graceful shutdown in a Drogon binary — SIGTERM + std::stop_token (C++20)
#include <stop_token>
#include <drogon/drogon.h>
std::stop_source g_stop;
std::atomic<bool> g_ready{true};                  // readiness flag
extern "C" void handle_sigterm(int) {
  g_ready.store(false);                           // fail readiness FIRST
  g_stop.request_stop();                          // cooperative stop
}
int main() {
  std::signal(SIGTERM, handle_sigterm);
  std::signal(SIGINT,  handle_sigterm);
  drogon::app().registerHandler("/readyz", [](auto, auto cb) {
    auto r = drogon::HttpResponse::newHttpResponse();
    r->setStatusCode(g_ready ? drogon::k200OK
                             : drogon::k503ServiceUnavailable);
    cb(r);
  });
  // workers receive the stop_token; consumer threads exit cleanly
  std::jthread kafka_worker(consume_loop, g_stop.get_token());
  drogon::app().run();                            // drains HTTP on signal
  kafka_worker.join();                            // joins on stop_token
  return 0;                                       // RAII unwinds remaining state
}
```

The same three moving parts appear in every stack. A `SIGTERM` handler flips the
readiness flag so the readiness endpoint returns `503` immediately — the "stop new
traffic" step, registered at the signal so it fires before anything else. The HTTP server
drains in-flight requests automatically, bounded by an explicit timeout
(`--timeout-graceful-shutdown`, `timeout-per-shutdown-phase`, `ShutdownTimeout`) so a
stuck request cannot hang the deploy. And the shutdown hook — FastAPI's `lifespan` after
the `yield`, Spring's `ContextClosedEvent`, the .NET `StopAsync`, the C++ `jthread` join
on the `stop_token` — runs once HTTP is done and is where you stop the consumer (which
commits offsets and leaves the group) and close pools. The order is the whole point:
readiness down, drain HTTP, then drain everything else.

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
        httpGet: { path: /livez, port: 8080 }
      lifecycle:
        preStop:
          exec:
            command: ["sh", "-c", "sleep 5"]   # cover async endpoint removal
```

`terminationGracePeriodSeconds` is the total budget, and it must exceed `preStop` plus
your worst-case drain plus a buffer. The readiness probe's `periodSeconds × failureThreshold`
sets how fast Kubernetes actually stops routing after you report `DOWN` — roughly ten
seconds here — which your `preStop` sleep should cover. Liveness points at a *separate*
`/livez` that stays up throughout the drain, so the kubelet does not restart a pod that is
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
actually makes the system safe, and graceful shutdown just makes the unsafe window rare.

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
A clean rollout under live load, not a green integration test, is graceful shutdown actually
working.

---
*Verification status: unverified — code and manifests transcribed and normalised from the
source decks, not yet run. The highest-risk things to confirm on a real cluster: the exact
Spring `AvailabilityChangeEvent`/`ReadinessState` wiring against the configured actuator
readiness group, the Quarkus shutdown-delay properties (note `delay-enabled` is build-time)
on the project's Quarkus version, the .NET `IHealthCheck` readiness flip landing in the
mapped `/healthz/ready`, uvicorn's `--timeout-graceful-shutdown` bounding behaviour, and the
C++ `std::jthread`/`stop_token` join completing within the grace period. The
`examples/21-shutdown/` runner moves it to verified.*
