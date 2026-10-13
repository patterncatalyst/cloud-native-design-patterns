---
title: "Failure Modes"
marker: "M"
label: "Appendix M"
order: 26
part: "Deep-dive appendices"
description: "The synthesis appendix — a taxonomy of how distributed systems fail (partition, split-brain, partial, gray, amplification, cascading) and the defensive toolkit mapped to each: timeouts and deadlines, retry with backoff and jitter, circuit breakers, bulkheads, load shedding, quorum, and the mesh."
duration: 24 minutes
---

This is the synthesis appendix. It pulls together error handling, graceful shutdown,
observability, and the resilience patterns scattered across the book and points them at
the specific ways distributed systems fail. If you keep one thing from it, keep the matrix
at the end, which maps each failure mode to the patterns that defend it. The reframe that
organises everything: we are not trying to *prevent* failure — across a network that is
impossible — we are trying to *bound* it and recover. That shifts every question from "how
do we stop failures" to "how do we contain and survive them."

## Distributed systems fail differently

The single most important conceptual shift for a developer moving from monoliths is
**partial failure**. In a single process, a function call returns or throws, synchronously,
in-process. Across a network there is a whole spectrum in between — including the two worst
cases: the call that *hangs* indefinitely, and the call that *succeeded on the server but
whose response was lost*, leaving the client unsure whether retrying is safe. Two further
properties make distributed failure hard: failures are **correlated** (one failure causes
others), and some are **actively deceptive** (a component that reports healthy while serving
errors). Everything that follows comes from accepting this and designing to bound it.

## A taxonomy of failure modes

The failures sort into three families, and the defensive toolkit sits
underneath them.

{% include excalidraw.html
   file="25-failure-taxonomy"
   alt="Three families feed into a distributed system: NETWORK (partition, split-brain: alive but cannot talk), COMPONENT (partial, gray failure: some fail, some lie), and LOAD (amplification, cascading: a failure feeds on itself). The defensive toolkit answers them: timeouts, retries, circuit breakers, bulkheads, load shedding, fallback, quorum, Istio, graceful shutdown, observability."
   caption="Figure M.1 — Three families of distributed failure, over the defensive toolkit that addresses them" %}

**Network** failures are partition and split-brain — nodes are alive but cannot talk.
**Component** failures are partial and gray — some dependencies fail outright, some degrade
and are perceived differently by different observers. **Load** failures are amplification and
cascading — a failure feeds on itself or spreads to neighbours. It restates the maxim from the
first chapter: all management is risk management — you manage the *distribution* of failures,
not their existence.

## Network partition

A partition is **not a crash**. Every node is healthy and running; the network between them is
what failed — which is exactly what makes partitions so confusing to debug, since each
component looks fine in isolation.

{% include excalidraw.html
   file="25-network-partition"
   alt="Three nodes on the left form a majority partition A; two nodes on the right form a minority partition B; the link between them is down. Note: every node is healthy and only the network failed, and CAP forces a choice between consistency and availability while partitioned."
   caption="Figure M.2 — A network partition: healthy nodes that cannot reach each other" %}

This is where CAP becomes concrete: while partitioned you must choose to stay **consistent**
(the minority side refuses writes, sacrificing availability) or **available** (both sides
accept writes, sacrificing consistency and reconciling later). Kubernetes itself uses etcd,
which chooses consistency — the minority side of a control-plane partition stops accepting
writes. Address it with quorum/consensus, idempotent writes (so a retried write after the heal
is safe), and a design that tolerates partitions and reconciles.

## Split-brain

Split-brain is the catastrophic outcome of a partition in a system that elects a leader. Both
sides lose contact, each assumes the other died, each promotes itself — and now two primaries
accept conflicting writes, leaving divergent state with no clean merge on heal.

{% include excalidraw.html
   file="25-split-brain"
   alt="A partition where each side has self-elected a leader that accepts writes, producing two primaries with conflicting writes. The cure noted is quorum: an action needs a majority, so a minority partition cannot act."
   caption="Figure M.3 — Split-brain: a partition elects two leaders; quorum is the only real cure" %}

The prevention is **quorum**: an action requires a majority (N/2 + 1) to agree, so a minority
partition mathematically cannot act — it knows it is the minority and steps down. This is why
cluster sizes are odd (3, 5, 7): to always have a clear majority. Fencing tokens
(monotonically increasing IDs that let a resource reject a stale leader's writes) and leases
are complementary, and etcd/Raft give the Kubernetes control plane this property out of the
box. As the matrix will show, quorum is the *only* answer to split-brain — no amount of
retrying or circuit-breaking helps when the problem is two leaders.

## Partial failure

This is the slide for developers moving from monoliths. In-process, the order and inventory
services are function calls in one process — if one is "down," the process is down.
Distributed, the order service calls inventory (healthy), payment (down), and shipping (slow),
and must make a **per-dependency decision** for each.

{% include excalidraw.html
   file="25-partial-failure"
   alt="An order service makes one decision per dependency: use the result from a healthy inventory service, fall back or fail for a down payment service, and time out then fall back for a slow shipping service."
   caption="Figure M.4 — Partial failure: each dependency needs its own use / fall-back / time-out decision" %}

The mistake behind most production incidents is treating a remote call like a local one — no
timeout, no fallback, no circuit breaker — so a single down dependency hangs the caller. The
next several patterns are precisely the per-dependency defences: timeouts, circuit breakers,
fallbacks, and bulkheads.

## Gray failure

Gray failure is the mode that defeats naive health checking. The classic shape: a node is slow
or dropping a fraction of requests, but its liveness probe — a trivial `GET /healthz` — still
returns `200`, so Kubernetes keeps it in rotation and the load balancer keeps sending it
traffic.

{% include excalidraw.html
   file="25-gray-failure"
   alt="A pod that is slow or dropping 5% of requests has a liveness probe that still returns 200, so the probe sees it as healthy, while real client traffic sees errors and latency — differential observability."
   caption="Figure M.5 — Gray failure: the probe sees healthy, the client sees errors" %}

This is **differential observability** — the observer that *decides* (the probe) sees something
different from the observer that *matters* (the client). The fixes are all about observing from
the right vantage point: deep health checks that exercise real dependencies, RED metrics
measured on actual traffic, SLO burn-rate alerts, and — critically — Istio outlier detection,
which ejects a host from the pool when it returns consecutive errors, regardless of what the
host's own probe claims.

## Amplification loops and retry storms

Amplification is a positive feedback loop in which the system's own defensive behaviour —
retrying — becomes the attack. Two effects compound: retries **multiply** across layers (a
gateway that retries 3×, calling a service that retries 3×, calling another that retries 3×,
turns one request into 27 at the bottom), and they **synchronise** (every client that failed at
the same moment retries at the same moment).

{% include excalidraw.html
   file="25-amplification"
   alt="One client request hits a gateway that retries three times, then a service that retries three times, then a service that retries three times, producing 27 requests at the bottom of the stack."
   caption="Figure M.6 — Amplification: retries multiply across layers and synchronise into a thundering herd" %}

The result can be **metastable** — the system stays collapsed even after the original trigger is
gone, because the retry load alone sustains the failure. Breaking it requires backoff with
jitter (de-synchronise), a retry budget (cap retries to a small percentage of live traffic),
retrying at exactly *one* layer, and a circuit breaker. This is the same dynamic as the
retry-storm figure in the Error Handling appendix, here generalised across layers.

## Cascading failure

Cascading failure is how a single slow dependency takes down an entire system. A slow database
fills the calling service's request threads (or async tasks, or connection pool) with waiters;
with its resources exhausted, that service now fails for *all* callers, not just those touching
the database; its callers' resources then fill waiting on it; and the wave climbs the graph to
the user-facing edge.

{% include excalidraw.html
   file="25-cascading"
   alt="A slow database blocks Service C's threads, which exhausts its resources so it fails for all callers, which fills Service B's pool, which takes down the edge — the failure propagates up the graph."
   caption="Figure M.7 — Cascading failure: one slow dependency exhausts resources up the whole call graph" %}

The amplifiers are synchronous call chains and unbounded resources (unbounded queues, unbounded
thread pools, no timeouts). Each defensive pattern breaks one link: timeouts stop threads
blocking forever, bulkheads isolate the pool so the slow calls can't consume all of it, circuit
breakers stop calling the slow dependency entirely, and load shedding rejects excess work at the
edge before it enters the system.

## The defensive toolkit

**No pattern in the toolkit is sufficient alone** — several interact, and production
resilience is their composition. Retry without a circuit breaker amplifies; a circuit breaker without a fallback
just fails faster; a bulkhead without a timeout still lets threads block within its pool. The
patterns here each get a diagram and per-language code; the platform-level pieces (Istio,
shutdown, observability) sit underneath the application-level ones.

## Timeouts and deadline propagation

Two ideas. First, **every remote call must have a timeout** — the default in many HTTP clients
is infinite, which is exactly how one slow dependency hangs a whole service. Second, **deadline
propagation**: the original deadline travels with the request, and each hop subtracts the time
it used and passes the remainder downstream; when too little budget remains to plausibly finish,
the downstream fails immediately rather than starting work that will be thrown away.

{% include excalidraw.html
   file="25-timeouts-deadline"
   alt="A 1000ms deadline at the edge travels through Service A (uses 200ms, 800 left), Service B (uses 300ms, 500 left), to the database, which decides whether enough budget remains to start."
   caption="Figure M.8 — Deadline propagation: the budget travels and shrinks; too little left means fail now" %}

gRPC does this natively with deadlines; for HTTP you carry the remaining budget in a header
convention like `X-Deadline-Ms` and honour it at each hop.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// examples/26-failure-modes/spring-boot/edge-service: BackendClient.java and EdgeController.java (condensed excerpts)
// Every call through the shared RestClient gives up after 2 s.
var factory = new SimpleClientHttpRequestFactory();
factory.setConnectTimeout(Duration.ofSeconds(2));
factory.setReadTimeout(Duration.ofSeconds(2));
this.rest = builder.baseUrl(backendUrl).requestFactory(factory).build();

// /with-deadline: the backend gets what is left of the caller's budget.
int remaining = budgetMs - 50;   // edge overhead
if (remaining < 50) {
    result.put("error", "deadline_exceeded");
    result.put("reason", "insufficient budget at edge");
    return result;
}
var budgeted = new SimpleClientHttpRequestFactory();
budgeted.setReadTimeout(Duration.ofMillis(remaining));
var response = RestClient.builder().requestFactory(budgeted).build().get()
        .uri(backendUrl + "/process")
        .header("X-Deadline-Ms", String.valueOf(remaining))
        .retrieve()
        .toEntity(Map.class);
```

```java
// examples/26-failure-modes/quarkus/edge-service: application.properties and EdgeResource.java (condensed excerpts)
// quarkus.rest-client.backend.url=${BACKEND_URL:http://backend:8081}
// quarkus.rest-client.backend.read-timeout=2000        <- every call gives up after 2 s

@GET
@Path("with-deadline")
public Map<String, Object> withDeadline(@RestQuery("budget_ms") @DefaultValue("1000") int budgetMs) {
    int remaining = budgetMs - 50;   // edge overhead
    if (remaining < 50) {
        return Map.of("error", "deadline_exceeded", "reason", "insufficient budget at edge");
    }
    // The budget is per request, so this client gets its own read timeout.
    BackendClient budgeted = QuarkusRestClientBuilder.newBuilder()
            .baseUri(URI.create(backendUrl))
            .readTimeout(remaining, TimeUnit.MILLISECONDS)
            .build(BackendClient.class);
    var response = budgeted.process(String.valueOf(remaining));   // @RestHeader("X-Deadline-Ms")
    return Map.of("status", response.getStatus(), "body", response.readEntity(Map.class));
}
```

```csharp
// examples/26-failure-modes/dotnet/EdgeService/Program.cs (condensed excerpts)
// A Polly pipeline caps a call at 2 s; TimeoutRejectedException reports it.
builder.Services.AddResiliencePipeline<string, HttpResponseMessage>("timeout", p => p
    .AddTimeout(TimeSpan.FromSeconds(2)));

app.MapGet("/with-timeout", async (BackendClient backend, ResiliencePipelineProvider<string> pipelines) =>
{
    try
    {
        var resp = await pipelines.GetPipeline<HttpResponseMessage>("timeout").ExecuteAsync(backend.ProcessAsync);
        return Results.Json(new { status = (int)resp.StatusCode, body = await BodyAsync(resp) });
    }
    catch (TimeoutRejectedException)
    {
        return Results.Json(new { error = "timeout", pattern = "timeout" });
    }
});

// /with-deadline: the remaining budget bounds the call and travels as X-Deadline-Ms.
using var cts = new CancellationTokenSource(remaining);
var resp = await backend.ProcessAsync(cts.Token, remaining);
```

```python
# examples/26-failure-modes/python/edge-service/main.py (condensed excerpts)
# One client for the process; every call gives up after 2 s (0.5 s to connect).
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=httpx.Timeout(2.0, connect=0.5)) as client:
        app.state.client = client
        yield


@app.get("/with-deadline")
async def with_deadline(budget_ms: int = Query(default=1000)):
    remaining = budget_ms - 50  # edge overhead
    if remaining < 50:
        return {"error": "deadline_exceeded", "reason": "insufficient budget at edge"}
    try:
        r = await client().get(
            "/process",
            headers={"X-Deadline-Ms": str(remaining)},             # propagate the budget
            timeout=httpx.Timeout(remaining / 1000.0, connect=0.5),
        )
        return {"status": r.status_code, "body": r.json()}
    except httpx.TimeoutException:
        return {"error": "deadline_exceeded", "reason": "timed out waiting for backend"}
```

```cpp
// examples/26-failure-modes/cpp/edge-service/src/main.cpp (condensed excerpts)
// Drogon's async HttpClient: the coroutine suspends while it waits, and the timeout is per call.
Task<Reply> get_backend(double timeout_s, std::string deadline_ms = {}) {
    auto client = HttpClient::newHttpClient(g_backend);
    auto req = HttpRequest::newHttpRequest();
    req->setPath("/process");
    if (!deadline_ms.empty()) req->addHeader("X-Deadline-Ms", deadline_ms);   // propagate the budget
    try {
        auto resp = co_await client->sendRequestCoro(req, timeout_s);
        Reply reply;
        reply.status = static_cast<int>(resp->getStatusCode());
        if (auto json = resp->getJsonObject()) reply.body = *json;
        co_return reply;
    } catch (const HttpException&) {
        co_return Reply{};   // status 0: timed out or unreachable
    }
}

// /with-timeout: co_await get_backend(2.0)
// /with-deadline: int remaining = budget_ms - 50; ... co_await get_backend(remaining / 1000.0, std::to_string(remaining))
```

```go
// examples/26-failure-modes/go/edge-service/cmd/server/main.go (condensed excerpts)
// call2s is one backend call that gives up after 2 s; a 5xx comes back as a statusError.
func call2s(ctx context.Context) ([]byte, error) {
	ctx, cancel := context.WithTimeout(ctx, 2*time.Second)
	defer cancel()
	code, body, err := callBackend(ctx, nil)
	if err != nil {
		return nil, err
	}
	if code >= 500 {
		return nil, statusError{code}
	}
	return body, nil
}

// /with-deadline: the remaining budget bounds the call and travels as X-Deadline-Ms.
remaining := budget - 50 // edge overhead
ctx, cancel := context.WithTimeout(r.Context(), time.Duration(remaining)*time.Millisecond)
defer cancel()
code, body, err := callBackend(ctx, map[string]string{"X-Deadline-Ms": strconv.Itoa(remaining)})
```

## Retry with exponential backoff and jitter

Retry is the most abused resilience pattern, because the naive version — retry immediately, a
fixed number of times, at every layer — is exactly how the amplification storm forms. The
correct version has four properties: **exponential backoff** (100ms, 200ms, 400ms), **jitter**
(randomness so clients don't synchronise), a **cap** on both attempts and total time, and a
**retry budget** (retries may never exceed, say, 10% of live traffic).

{% include excalidraw.html
   file="25-retry-backoff"
   alt="Three attempts with growing, jittered waits between them — about 100ms plus jitter, then about 200ms plus jitter — capped at three attempts."
   caption="Figure M.9 — Retry done right: exponential backoff, jitter, a hard cap, idempotent calls only" %}

It applies to **idempotent operations only** — retrying a non-idempotent `POST` without an
idempotency key can double-charge a customer — and it is **always paired with a circuit
breaker**, so once a dependency is clearly down you stop retrying entirely.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// examples/26-failure-modes/spring-boot/edge-service: BackendClient.java and application.properties (condensed excerpts)
/** Retried on a 5xx or a timeout with exponential backoff and jitter; counts every attempt. */
@Retry(name = "backend")
public ResponseEntity<Map> processWithRetry(AtomicInteger attempts) {
    attempts.incrementAndGet();
    return process();
}

// Resilience4j reads the policy from configuration, not from the code:
// resilience4j.retry.instances.backend.max-attempts=3
// resilience4j.retry.instances.backend.wait-duration=100ms
// resilience4j.retry.instances.backend.enable-exponential-backoff=true
// resilience4j.retry.instances.backend.exponential-backoff-multiplier=2
// resilience4j.retry.instances.backend.exponential-max-wait-duration=2s
// resilience4j.retry.instances.backend.enable-randomized-wait=true
// resilience4j.retry.instances.backend.randomized-wait-factor=0.5
// resilience4j.retry.instances.backend.retry-exceptions=\
//     org.springframework.web.client.HttpServerErrorException,org.springframework.web.client.ResourceAccessException
```

```java
// examples/26-failure-modes/quarkus/edge-service/src/main/java/com/cndp/edge/Backend.java (condensed excerpt)
// SmallRye Fault Tolerance: the annotations are CDI interceptors, so the resource calls through this bean.
/** Retried on a 5xx or a timeout: 3 attempts, 100 ms doubling to 2 s, with up to 50 ms of jitter. */
@Retry(maxRetries = 2, delay = 100, jitter = 50,
        retryOn = {WebApplicationException.class, ProcessingException.class})
@ExponentialBackoff(factor = 2, maxDelay = 2000)
public Response processWithRetry(AtomicInteger attempts) {
    attempts.incrementAndGet();
    return client.process();   // the REST client throws WebApplicationException on a 4xx or 5xx
}
```

```csharp
// examples/26-failure-modes/dotnet/EdgeService/Program.cs (condensed excerpts)
// Polly v8 with the HTTP retry options from Microsoft.Extensions.Http.Resilience:
// a 5xx, a timeout or a connection failure is retried.
builder.Services.AddResiliencePipeline<string, HttpResponseMessage>("retry", p => p
    .AddRetry(new HttpRetryStrategyOptions
    {
        MaxRetryAttempts = 2,
        Delay = TimeSpan.FromMilliseconds(100),
        BackoffType = DelayBackoffType.Exponential,
        UseJitter = true,
        MaxDelay = TimeSpan.FromSeconds(2),
    })
    .AddTimeout(TimeSpan.FromSeconds(2)));   // each attempt gets 2 s

var attempts = 0;
var resp = await pipelines.GetPipeline<HttpResponseMessage>("retry").ExecuteAsync(ct =>
{
    attempts++;
    return backend.ProcessAsync(ct);
});
```

```python
# examples/26-failure-modes/python/edge-service/main.py (condensed excerpt)
# tenacity: 3 attempts, 100 ms doubling to 2 s with jitter; a 5xx or a transport error is retried.
@app.get("/with-retry")
async def with_retry():
    attempts = 0
    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=0.1, max=2.0, jitter=0.05),
            retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
            reraise=True,
        ):
            with attempt:
                attempts = attempt.retry_state.attempt_number
                r = await client().get("/process")
                r.raise_for_status()
        return {"status": r.status_code, "attempts": attempts, "body": r.json()}
    except (httpx.HTTPStatusError, httpx.TransportError):
        return {"attempts": attempts, "pattern": "retry-exhausted"}
```

```cpp
// examples/26-failure-modes/cpp/edge-service/src/main.cpp (condensed excerpt)
// 3 attempts, waits from 100 ms doubling to 2 s with up to 50% jitter; a 5xx or no answer is retried.
// sleepCoro suspends the handler, so the event-loop thread serves other requests during the wait.
app().registerHandler("/with-retry", [](HttpRequestPtr) -> Task<HttpResponsePtr> {
    thread_local std::mt19937 rng{std::random_device{}()};
    auto wait = 0.1;
    Reply reply;
    int attempt = 1;
    for (;; ++attempt) {
        reply = co_await get_backend(2.0);
        if ((reply.status != 0 && reply.status < 500) || attempt == 3) break;
        co_await sleepCoro(trantor::EventLoop::getEventLoopOfCurrentThread(),
                           wait + std::uniform_real_distribution<>(0.0, wait * 0.5)(rng));
        wait = std::min(wait * 2, 2.0);
    }
    Json::Value v;
    v["attempts"] = attempt;
    co_return json(v);
}, {Get});
```

```go
// examples/26-failure-modes/go/edge-service/cmd/server/main.go (condensed excerpt)
// cenkalti/backoff v7: 100 ms doubling to 2 s, each wait randomised by up to 50%, at most 3 tries.
bo := backoff.NewExponentialBackOff()
bo.InitialInterval = 100 * time.Millisecond
bo.MaxInterval = 2 * time.Second

var attempts int
body, err := backoff.Retry(r.Context(), func() ([]byte, error) {
	attempts++
	return call2s(r.Context()) // a 5xx comes back as a statusError and is retried
}, backoff.WithBackOff(bo), backoff.WithMaxTries(3), backoff.WithMaxElapsedTime(15*time.Second))

if err != nil {
	if re := backoff.AsRetryError(err); re != nil {
		err = re.LastErr // the failure the caller cares about, not the stop reason
	}
}
```

## Circuit breaker

The circuit breaker is the pattern that most directly stops cascading and amplification. It is
a three-state machine. **Closed**: calls pass through and failures are counted over a rolling
window. When the failure ratio crosses the threshold it trips to **Open**: calls fail
immediately without attempting the downstream, which gives the caller a fast answer and gives
the struggling dependency room to recover. After a reset timeout it goes **Half-Open** and
allows a few trial calls; if they succeed it closes, if they fail it re-opens.

{% include excalidraw.html
   file="25-circuit-breaker"
   alt="A three-state machine: CLOSED (calls pass, count failures) trips to OPEN (fail fast, don't call) when failures exceed the threshold; after a reset timeout OPEN moves to HALF-OPEN (a few trial calls); a successful trial returns to CLOSED, a failed trial returns to OPEN."
   caption="Figure M.10 — The circuit breaker: closed, open, half-open — one breaker per dependency, paired with a fallback" %}

Two details are crucial: **one breaker per dependency** (never a single global breaker), and
**pair it with a fallback** so an open breaker degrades gracefully rather than just erroring
faster.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// examples/26-failure-modes/spring-boot/edge-service: BackendClient.java and application.properties (condensed excerpts)
@CircuitBreaker(name = "backend", fallbackMethod = "fallback")
public Map<String, Object> processWithBreaker() {
    return Map.of("source", "live", "body", process().getBody(), "breaker", breakerState());
}

private Map<String, Object> fallback(Throwable cause) {   // an open breaker or a failed call lands here
    String reason = switch (cause) {
        case CallNotPermittedException ignored -> "circuit_open";
        case HttpServerErrorException e -> "upstream_" + e.getStatusCode().value();
        default -> "upstream_unreachable";
    };
    return Map.of("source", "fallback", "reason", reason, "breaker", breakerState());
}

// 5 failed calls out of 5 open it for 10 s; 2 trial calls in half-open decide:
// resilience4j.circuitbreaker.instances.backend.sliding-window-type=COUNT_BASED
// resilience4j.circuitbreaker.instances.backend.sliding-window-size=5
// resilience4j.circuitbreaker.instances.backend.failure-rate-threshold=100
// resilience4j.circuitbreaker.instances.backend.wait-duration-in-open-state=10s
// resilience4j.circuitbreaker.instances.backend.permitted-number-of-calls-in-half-open-state=2
```

```java
// examples/26-failure-modes/quarkus/edge-service/src/main/java/com/cndp/edge/Backend.java (condensed excerpt)
/** 5 failed calls open the breaker for 10 s; 2 successful trial calls close it. */
@CircuitBreaker(requestVolumeThreshold = 5, failureRatio = 1.0, delay = 10, delayUnit = ChronoUnit.SECONDS,
        successThreshold = 2)
@CircuitBreakerName("backend")                 // read by CircuitBreakerMaintenance for /breaker-state
@Fallback(fallbackMethod = "fallback")
public Map<String, Object> processWithBreaker() {
    return Map.of("source", "live", "body", client.process().readEntity(Map.class), "breaker", breakerState());
}

Map<String, Object> fallback(Throwable cause) {
    String reason = switch (cause) {
        case CircuitBreakerOpenException ignored -> "circuit_open";
        case WebApplicationException e -> "upstream_" + e.getResponse().getStatus();
        default -> "upstream_unreachable";
    };
    return Map.of("source", "fallback", "reason", reason, "breaker", breakerState());
}
```

```csharp
// examples/26-failure-modes/dotnet/EdgeService/Program.cs (condensed excerpts)
var breakerState = new CircuitBreakerStateProvider();   // read by /breaker-state
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

try
{
    var resp = await pipelines.GetPipeline<HttpResponseMessage>("breaker").ExecuteAsync(backend.ProcessAsync);
    if ((int)resp.StatusCode >= 500)
        return Results.Json(new { source = "fallback", reason = $"upstream_{(int)resp.StatusCode}" });
    return Results.Json(new { source = "live", body = await BodyAsync(resp) });
}
catch (BrokenCircuitException)
{
    return Results.Json(new { source = "fallback", reason = "circuit_open" });
}
```

```python
# examples/26-failure-modes/python/edge-service/main.py (condensed excerpts)
# pybreaker: 5 failed calls open it, it stays open 10 s, then 2 successful trial calls close it.
breaker = pybreaker.CircuitBreaker(
    fail_max=5, reset_timeout=10, success_threshold=2, throw_new_error_on_trip=False, name="backend"
)


@app.get("/with-breaker")
async def with_breaker():
    try:
        with breaker.calling():                 # works around an awaited call
            r = await client().get("/process")
            r.raise_for_status()                # a 5xx counts as a failure
        return {"source": "live", "body": r.json(), "breaker": breaker.current_state}
    except pybreaker.CircuitBreakerError:
        reason = "circuit_open"
    except httpx.HTTPStatusError as e:
        reason = f"upstream_{e.response.status_code}"
    except httpx.TransportError:
        reason = "upstream_unreachable"
    return {"source": "fallback", "reason": reason, "breaker": breaker.current_state}
```

```cpp
// examples/26-failure-modes/cpp/edge-service/src/main.cpp (condensed excerpt)
// No maintained C++ resilience library is on ConanCenter, so the breaker is written here.
class CircuitBreaker {
public:
    bool allow() {
        std::lock_guard lock(mtx_);
        if (state_ == "open" && Clock::now() - opened_at_ >= kResetTimeout) {
            state_ = "half-open";
            successes_ = 0;
        }
        return state_ != "open";
    }
    void record_success() {
        std::lock_guard lock(mtx_);
        failures_ = 0;
        if (state_ == "half-open" && ++successes_ >= kTrialSuccesses) state_ = "closed";
    }
    void record_failure() {
        std::lock_guard lock(mtx_);
        if (state_ == "half-open" || ++failures_ >= kThreshold) {   // 5 in a row, or a failed trial
            state_ = "open";
            opened_at_ = Clock::now();
            failures_ = 0;
        }
    }
    // kThreshold = 5, kTrialSuccesses = 2, kResetTimeout = 10s
};
```

```go
// examples/26-failure-modes/go/edge-service/cmd/server/main.go (condensed excerpts)
// sony/gobreaker v2: 5 failures in a row open it, it stays open 10 s, then 2 successful trial calls close it.
cb = gobreaker.NewCircuitBreaker[[]byte](gobreaker.Settings{
	Name:        "backend",
	MaxRequests: 2,
	Timeout:     10 * time.Second,
	ReadyToTrip: func(counts gobreaker.Counts) bool { return counts.ConsecutiveFailures >= 5 },
})

func handleBreaker(w http.ResponseWriter, r *http.Request) {
	body, err := cb.Execute(func() ([]byte, error) { return call2s(r.Context()) })
	if err == nil {
		writeJSON(w, 200, map[string]any{"source": "live", "body": parse(body), "breaker": cb.State().String()})
		return
	}
	reason := "upstream_unreachable"
	if errors.Is(err, gobreaker.ErrOpenState) || errors.Is(err, gobreaker.ErrTooManyRequests) {
		reason = "circuit_open"
	} else if se, ok := errors.AsType[statusError](err); ok {
		reason = fmt.Sprintf("upstream_%d", se.code)
	}
	writeJSON(w, 200, map[string]any{"source": "fallback", "reason": reason, "breaker": cb.State().String()})
}
```

## Bulkhead

A bulkhead bounds concurrency so one saturated dependency cannot consume all of a service's
threads or connections. It got its full per-language treatment in the Security chapter, so the
point to re-state here is the interaction: **a bulkhead bounds how many, a timeout bounds how
long** — concurrency-limiting alone does not help if the bounded calls block forever, so the two
must be combined. The mesh provides bulkheading at the connection-pool level, covered next in this appendix.

## Load shedding and graceful degradation

Two related patterns engineers tend to skip. **Load shedding** feels like giving up —
choosing to reject requests — but it is the difference between degrading and collapsing. The
arithmetic is simple: at 120% of capacity, accepting everything makes *everything* slow and
timing out (0% goodput); shedding the excess 20% means the 80% you accept is served well. Shed
by priority (drop health-check-style or low-value traffic first, protect revenue-critical paths),
and let adaptive concurrency limiters shed automatically based on observed latency.

**Graceful degradation** is the product-level decision about what to return when you cannot
return everything: serve a stale cache, omit the personalised section, queue the write for later,
show a default recommendation. A product page that can't reach the reviews service should still
show the product — just without reviews. Together with the breaker these form a system: the
breaker decides to *stop calling*, the fallback decides *what to return instead*, and load
shedding decides *what not to accept* in the first place — and none of them can be done
intelligently without the observability from the Observability chapter to measure saturation.

## Istio — resilience at the mesh layer

The service mesh delivers a large slice of this toolkit without code in every service, in every
language.

{% include excalidraw.html
   file="25-istio-resilience"
   alt="An Istio Envoy sidecar wraps service-to-service calls: a VirtualService configures timeout and retries with backoff and jitter; a DestinationRule configures connectionPool (mesh bulkhead) and outlierDetection, which ejects a bad host from the callee pool."
   caption="Figure M.11 — The mesh supplies timeouts, retries, connection-pool bulkheads, and gray-failure ejection" %}

A `VirtualService` configures per-route timeouts and retries (Envoy adds backoff and jitter
automatically); a `DestinationRule` configures `connectionPool` limits (mesh-level bulkheading)
and `outlierDetection` — the mesh's answer to gray failure, ejecting a host that returns
consecutive errors regardless of what its own probe claims.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: payment }
spec:
  hosts: [payment]
  http:
  - timeout: 2s                                   # per-route deadline
    retries:
      attempts: 2                                 # mesh retries (backoff+jitter auto)
      perTryTimeout: 1s
      retryOn: 5xx,reset,connect-failure
    route: [{ destination: { host: payment } }]
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata: { name: payment }
spec:
  host: payment
  trafficPolicy:
    connectionPool:                               # mesh-level bulkhead
      tcp: { maxConnections: 100 }
      http: { http2MaxRequests: 1000, maxRequestsPerConnection: 10 }
    outlierDetection:                             # gray-failure ejection
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

The discipline that prevents amplification: **don't double up**. If Istio is retrying, do not
*also* retry in the app — decide where each concern lives. Push uniform concerns (timeouts,
outlier detection, mesh bulkheads) to Istio; keep business-aware concerns (fallbacks, idempotency
keys) in the app.

## Graceful shutdown and observing failure

Two threads from elsewhere in the book close the loop. **Graceful shutdown** (the Graceful
Shutdown appendix) is what prevents dropped requests during a rolling deploy: on `SIGTERM`, flip
readiness to draining so the platform stops sending new work, cover the deregistration lag, drain
in-flight work under a bounded timeout, then exit. **Observing failure** (the Observability
chapter) is what makes these modes visible at all — a default CPU/memory dashboard will not show
a gray failure or an amplification loop. Measure RED per *dependency* (so partial failures are
visible), compare health-check status to real-traffic SLOs (so gray failures are visible), and
watch request-rate versus user-action-rate (so amplification is visible) — then pivot from the
metric to the trace to the logs by trace id when something breaks.

## Which pattern addresses which failure mode

The synthesis. Read a **row** to see the portfolio that defends a failure mode; read a **column**
to see what a pattern buys you across modes.

| Failure mode | Timeout + deadline | Retry + backoff | Circuit breaker | Bulkhead (§12) | Load shed | Quorum / consensus | Istio outlier | Graceful shutdown |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Network partition | ✓ | ✓ |  |  |  | ✓ |  |  |
| Split-brain |  |  |  |  |  | ✓ |  |  |
| Partial failure | ✓ | ✓ | ✓ | ✓ |  |  | ✓ |  |
| Gray failure |  |  | ✓ | ✓ |  |  | ✓ |  |
| Amplification |  | ✓ | ✓ |  | ✓ |  |  |  |
| Cascading | ✓ |  | ✓ | ✓ | ✓ |  |  | ✓ |

Two observations to state aloud. **Quorum/consensus is the only real answer to split-brain** — no
amount of retrying or breaking helps when the problem is two leaders; you need majority rule.
And almost every other cell is about assembling a **portfolio**: there is no single pattern that
handles partial, gray, amplification, and cascading failures — you layer timeouts,
retries-with-budget, breakers, bulkheads, shedding, and fallbacks, and you observe the result.

## Take-aways and references

The imperatives: design for partial failure from the start (every remote call can succeed, fail,
hang, or lie); timeout everything; retry only idempotent calls, with backoff, jitter, and a
budget, at one layer, always paired with a breaker; bound the blast radius with bulkheads,
breakers, shedding, and fallbacks; use quorum for consensus rather than inventing your own; split
concerns between the mesh and the app and never double-retry; and observe from the client's
vantage point, because gray failures are invisible to naive health checks. The canonical
references are the Google SRE Book (the chapters on addressing cascading failures and handling
overload are the best free resource), Michael Nygard's *Release It!* (where the circuit breaker
and bulkhead were named for software), the gRPC retry design, gRFC A6 (retry policy, backoff with jitter, retry
throttling), the Istio traffic-management docs, and the metastable-failures research (Bronson et al.,
2021).

### Cross-check it yourself

Reproduce the two dynamics that this appendix turns on. **Cascading and the breaker:** put steady
load on a service with `hey` (or `ghz` for gRPC) while you force its downstream dependency to be
slow, and watch the downstream call count — without a breaker it climbs and the caller's threads
fill (cascading); with a per-dependency breaker configured, the count *plateaus* as the breaker
trips and the caller returns its fallback fast. **Deadline propagation:** issue a request with a
small deadline header to a chain of two services and confirm from the logs that the *second* hop
refuses to start work when the remaining budget has fallen under its minimum, rather than running a query
whose result will be discarded. A breaker that flattens downstream load under failure, and a
deadline that stops doomed work early, are the two behaviours everything here depends on.

This appendix touches difficult operational territory; if you are diagnosing a live incident, the
Google SRE cascading-failures chapter is the fastest way to a shared vocabulary with your team.

---
*Verification status: verified — [`examples/26-failure-modes/`](https://github.com/patterncatalyst/cloud-native-design-patterns/tree/main/examples/26-failure-modes/) passes 22/22 checks in each of the six languages on Docker Engine (2026-10-13)
(timeout, retry exhaustion, circuit breaker closed, open and recovered with fallback, deadline-budget propagation, bulkhead limit, a full bulkhead refusing the overflow with 429 and admitting again).*
