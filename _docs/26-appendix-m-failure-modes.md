---
title: "Failure Modes"
marker: "M"
label: "Appendix M"
order: 26
part: "Deep-dive appendices"
description: "The synthesis appendix — a taxonomy of how distributed systems actually fail (partition, split-brain, partial, gray, amplification, cascading) and the defensive toolkit mapped to each: timeouts and deadlines, retry with backoff and jitter, circuit breakers, bulkheads, load shedding, quorum, and the mesh."
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
errors). Everything below follows from accepting this and designing to bound it.

## A taxonomy of failure modes

The failures sort into three families, and the rest of the appendix is the toolkit that sits
underneath them.

{% include excalidraw.html
   file="25-failure-taxonomy"
   alt="Three families feed into a distributed system: NETWORK (partition, split-brain — alive but cannot talk), COMPONENT (partial, gray failure — some fail, some lie), and LOAD (amplification, cascading — a failure feeds on itself). Below sits the defensive toolkit: timeouts, retries, circuit breakers, bulkheads, load shedding, fallback, quorum, Istio, graceful shutdown, observability."
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

The rest of the appendix is the toolkit, and the thing to hold onto is that **no pattern is
sufficient alone** — several interact, and production resilience is their deliberate
composition. Retry without a circuit breaker amplifies; a circuit breaker without a fallback
just fails faster; a bulkhead without a timeout still lets threads block within its pool. The
patterns below each get a diagram and per-language code; the platform-level pieces (Istio,
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
@Service
public class PaymentService {
    private final RestClient client;            // built with timeouts (below)

    @TimeLimiter(name = "payment")              // Resilience4j: caps total time
    public CompletableFuture<Receipt> charge(Order o, long deadlineMs) {
        long remaining = deadlineMs - elapsedMs();
        if (remaining < 50)                                       // too little budget
            return CompletableFuture.failedFuture(new DeadlineExceeded());
        return CompletableFuture.supplyAsync(() ->
            client.post().uri("/charge")
                .header("X-Deadline-Ms", Long.toString(remaining))  // propagate
                .body(o).retrieve().body(Receipt.class));
    }
}
// RestClient factory: ClientHttpRequestFactorySettings
//   .withConnectTimeout(500ms).withReadTimeout(2s)
// application.yml: resilience4j.timelimiter.instances.payment.timeout-duration: 2s
```

```java
@ApplicationScoped
public class PaymentService {
    @Inject @RestClient PaymentClient client;

    @Timeout(2000)                               // MicroProfile: hard 2s ceiling
    @Blocking
    public Receipt charge(Order o, long deadlineMs) {
        long remaining = deadlineMs - elapsedMs();
        if (remaining < 50)                       // too little budget to start
            throw new DeadlineExceeded();
        return client.charge(o, remaining);       // propagate remaining budget
    }
}
// application.properties — client-level timeouts (the real defence)
//   quarkus.rest-client.payment.connect-timeout=500
//   quarkus.rest-client.payment.read-timeout=2000
```

```csharp
public class PaymentService(HttpClient http)   // http.Timeout set at registration
{
    public async Task<Receipt> Charge(Order o, TimeSpan deadline,
                                      CancellationToken ct)
    {
        if (deadline < TimeSpan.FromMilliseconds(50))
            throw new DeadlineExceededException();      // too little budget
        // link the caller's token with a deadline-bounded one
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(deadline);
        var req = new HttpRequestMessage(HttpMethod.Post, "/charge")
            { Content = JsonContent.Create(o) };
        req.Headers.Add("X-Deadline-Ms",                 // propagate budget
            deadline.TotalMilliseconds.ToString("0"));
        var resp = await http.SendAsync(req, cts.Token); // throws on timeout
        return (await resp.Content.ReadFromJsonAsync<Receipt>(cts.Token))!;
    }
}
```

```python
import httpx, asyncio

# Every client has an EXPLICIT timeout — the httpx default is None (infinite)
client = httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=0.5))

async def charge(order: dict, deadline_ms: int) -> dict:
    remaining = deadline_ms - elapsed_ms()        # budget left for this hop
    if remaining <= 50:                            # too little to finish
        raise DeadlineExceeded("no budget left")  # fail fast, don't start
    try:
        r = await asyncio.wait_for(
            client.post("/charge", json=order,
                        headers={"X-Deadline-Ms": str(remaining)}),  # propagate
            timeout=remaining / 1000)
        r.raise_for_status()
        return r.json()
    except (asyncio.TimeoutError, httpx.TimeoutException):
        raise HTTPException(504, "downstream timed out")
```

```cpp
// Every C++ client has an EXPLICIT timeout; deadlines propagate downstream.
#include <chrono>
using namespace std::chrono;
constexpr auto MIN_BUDGET = 50ms;

Task<json> charge(const Order& order, milliseconds remaining) {
  if (remaining <= MIN_BUDGET)                // too little to finish
    throw DeadlineExceeded{"no budget left"};
  // -------- gRPC: deadline propagation is built-in --------
  grpc::ClientContext ctx;
  ctx.set_deadline(system_clock::now() + remaining);
  ChargeReply reply;
  auto status = payment_stub_->Charge(&ctx, order_to_proto(order), &reply);
  if (status.error_code() == grpc::DEADLINE_EXCEEDED)
    throw HttpException{504, "downstream timed out"};
  co_return to_json(reply);
}
```

```go
// every client has an EXPLICIT timeout; deadlines propagate downstream on ctx
const minBudget = 50 * time.Millisecond

func charge(ctx context.Context, order Order) (Reply, error) {
	remaining := time.Until(deadlineOf(ctx)) // budget left for this hop
	if remaining <= minBudget {              // too little to finish
		return Reply{}, fmt.Errorf("no budget left: %w", context.DeadlineExceeded)
	}
	// the deadline rides on ctx; gRPC propagates it as the call deadline
	ctx, cancel := context.WithTimeout(ctx, remaining)
	defer cancel()

	reply, err := paymentClient.Charge(ctx, toProto(order))
	if status.Code(err) == codes.DeadlineExceeded {
		return Reply{}, &HTTPError{Status: 504, Msg: "downstream timed out"}
	}
	return toReply(reply), err
}
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
@Service
public class QuoteService {
    private final QuoteClient client;

    @Retry(name = "quote")                  // config in application.yml
    @CircuitBreaker(name = "quote")         // ALWAYS pair retry with a breaker
    public Quote quote(String symbol) {     // idempotent GET only
        return client.getQuote(symbol);
    }
}
// application.yml
//   resilience4j.retry.instances.quote:
//     max-attempts: 3
//     wait-duration: 100ms
//     enable-exponential-backoff: true
//     exponential-backoff-multiplier: 2
//     enable-randomized-wait: true          # jitter — do not omit
//     retry-exceptions: [java.io.IOException]   # transient only
```

```java
@ApplicationScoped
public class QuoteService {
    @Inject @RestClient QuoteClient client;

    @Retry(maxRetries = 3,                       // hard cap on attempts
           delay = 100, delayUnit = MILLIS,      // base backoff
           jitter = 50, jitterUnit = MILLIS,     // de-synchronise clients
           retryOn = TransientException.class)   // transient failures only
    @CircuitBreaker(requestVolumeThreshold = 10, // ALWAYS pair with a breaker
                    failureRatio = 0.5, delay = 5000)
    public Quote quote(String symbol) {           // idempotent GET
        return client.getQuote(symbol);
    }
}
// MicroProfile applies the breaker first, then retry within the closed state.
```

```csharp
// Polly v8: exponential backoff WITH jitter is built in
private static readonly ResiliencePipeline _pipeline =
    new ResiliencePipelineBuilder()
        .AddRetry(new RetryStrategyOptions {
            ShouldHandle = new PredicateBuilder()
                .Handle<HttpRequestException>(),       // transient only
            MaxRetryAttempts = 3,                       // hard cap
            BackoffType = DelayBackoffType.Exponential,
            UseJitter = true,                           // de-synchronise
            Delay = TimeSpan.FromMilliseconds(100)
        })
        .AddCircuitBreaker(new CircuitBreakerStrategyOptions {  // pair it
            FailureRatio = 0.5, MinimumThroughput = 10,
            BreakDuration = TimeSpan.FromSeconds(5)
        })
        .Build();

public Task<Quote?> Quote(string symbol, CancellationToken ct) =>   // GET
    _pipeline.ExecuteAsync(async t =>
        await http.GetFromJsonAsync<Quote>($"/quote/{symbol}", t), ct).AsTask();
```

```python
from tenacity import (retry, stop_after_attempt, wait_exponential_jitter,
                      retry_if_exception_type)

# Retry ONLY idempotent calls. Exponential backoff + jitter. Cap attempts.
@retry(
    retry=retry_if_exception_type(httpx.TransportError),   # transient only
    wait=wait_exponential_jitter(initial=0.1, max=2.0),    # backoff + jitter
    stop=stop_after_attempt(3),                            # hard cap
    reraise=True)
async def get_quote(symbol: str) -> dict:
    r = await client.get(f"/quote/{symbol}")      # GET is idempotent — safe
    r.raise_for_status()
    return r.json()
# Do NOT decorate a non-idempotent POST unless it carries an idempotency key.
# Pair with a circuit breaker so a down dep stops retries entirely.
```

```cpp
// Retry with exponential backoff + jitter — for idempotent calls only.
// Prefer the Istio retry policy when possible; in-process retry is the fallback.
#include <random>
#include <thread>

template <typename F>
auto retry_with_backoff(F&& fn, int max_attempts = 3) {
  thread_local std::mt19937 rng{std::random_device{}()};
  std::uniform_real_distribution<double> jitter{0.0, 100.0};
  std::chrono::milliseconds wait{100};            // initial
  for (int attempt = 1; attempt <= max_attempts; ++attempt) {
    try {
      return fn();
    } catch (const TransportError& e) {
      if (attempt == max_attempts) throw;        // out of budget
      auto sleep_ms = wait + std::chrono::milliseconds{(int)jitter(rng)};
      std::this_thread::sleep_for(sleep_ms);     // backoff
      wait = std::min(wait * 2, 2000ms);          // exponential, capped
    }
  }
  std::unreachable();
}
// Usage: GETs are idempotent → safe to retry. Pair with a circuit breaker.
```

```go
// retry with exponential backoff + jitter, idempotent calls only (cenkalti/backoff).
// Prefer the Istio retry policy when possible; in-process retry is the fallback.
func getQuote(ctx context.Context, symbol string) (Quote, error) {
	var q Quote
	op := func() error {
		r, err := client.Get(ctx, "/quote/"+symbol) // GET is idempotent — safe
		if err != nil {
			return err // transient errors get retried
		}
		q = r
		return nil
	}
	bo := backoff.NewExponentialBackOff()       // backoff + jitter built in
	bo.InitialInterval = 100 * time.Millisecond //
	bo.MaxInterval = 2 * time.Second            // capped
	// hard cap on attempts, and stop if the context is cancelled
	err := backoff.Retry(op, backoff.WithMaxRetries(backoff.WithContext(bo, ctx), 3))
	return q, err
	// Do NOT retry a non-idempotent POST unless it carries an idempotency key.
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
@Service
public class PaymentService {
    private final PaymentClient client;
    private final Outbox outbox;

    @CircuitBreaker(name = "payment", fallbackMethod = "queueForLater")
    public Receipt charge(Order o) {
        return client.charge(o);       // while OPEN: skipped, fallback runs
    }

    Receipt queueForLater(Order o, Throwable t) {   // graceful degradation
        outbox.enqueue(o);
        return Receipt.pending(o.id());
    }
}
// application.yml
//   resilience4j.circuitbreaker.instances.payment:
//     sliding-window-size: 10
//     failure-rate-threshold: 50          # open at 50%
//     wait-duration-in-open-state: 5s
//     permitted-number-of-calls-in-half-open-state: 2
```

```java
@ApplicationScoped
public class PaymentService {
    @Inject @RestClient PaymentClient client;
    @Inject Outbox outbox;

    @CircuitBreaker(
        requestVolumeThreshold = 10,   // rolling window of 10 calls
        failureRatio = 0.5,            // open at 50% failures
        delay = 5000,                  // stay open 5s, then half-open
        successThreshold = 2)          // 2 trial successes → close
    @Fallback(fallbackMethod = "queueForLater")   // degrade gracefully
    public Receipt charge(Order o) {
        return client.charge(o);       // while OPEN: skipped, fallback runs
    }

    Receipt queueForLater(Order o) {   // graceful degradation
        outbox.enqueue(o);
        return Receipt.pending(o.id());
    }
}
```

```csharp
public class PaymentService(HttpClient http, IOutbox outbox)
{
    private readonly ResiliencePipeline<Receipt> _pipeline =
        new ResiliencePipelineBuilder<Receipt>()
            .AddCircuitBreaker(new CircuitBreakerStrategyOptions<Receipt> {
                FailureRatio = 0.5,                 // open at 50%
                MinimumThroughput = 10,             // over a window of 10
                BreakDuration = TimeSpan.FromSeconds(5),
                ShouldHandle = new PredicateBuilder<Receipt>()
                    .Handle<HttpRequestException>()
            })
            .AddFallback(new FallbackStrategyOptions<Receipt> {   // degrade
                ShouldHandle = new PredicateBuilder<Receipt>()
                    .Handle<BrokenCircuitException>(),
                FallbackAction = args => {
                    outbox.Enqueue(args.Context.GetOrder());
                    return Outcome.FromResultAsValueTask(Receipt.Pending());
                }
            })
            .Build();
}
```

```python
from purgatory import AsyncCircuitBreakerFactory

# Open after 5 failures; stay open 30s; then half-open to test recovery
breakers = AsyncCircuitBreakerFactory(default_threshold=5, default_ttl=30)

async def charge(order: dict) -> dict:
    try:
        async with await breakers.get_breaker("payment"):
            # While OPEN this raises immediately — no doomed downstream call
            r = await client.post("/charge", json=order, timeout=2.0)
            r.raise_for_status()
            return r.json()
    except OpenedState:                       # breaker is open → degrade
        await outbox.enqueue(order)           # graceful fallback
        return {"status": "pending", "id": order["id"]}
# One breaker per dependency ("payment"), never one global breaker.
```

```cpp
// Hand-rolled circuit breaker — atomic state machine, per-dependency.
// Production C++ shops typically let Istio do this; shown for reference.
class CircuitBreaker {
  enum State { Closed, Open, HalfOpen };
  std::atomic<State> state_{Closed};
  std::atomic<int>   failures_{0};
  std::atomic<steady_clock::time_point> opened_at_;
  static constexpr int     THRESHOLD = 5;
  static constexpr seconds RESET_AFTER = 30s;
 public:
  template <typename F, typename Fallback>
  auto call(F&& fn, Fallback&& fb) {
    if (state_.load() == Open) {
      if (steady_clock::now() - opened_at_.load() < RESET_AFTER)
        return fb();                             // fail fast
      state_.store(HalfOpen);                    // test
    }
    try {
      auto r = fn();
      failures_.store(0); state_.store(Closed);  // recovered
      return r;
    } catch (...) {
      if (++failures_ >= THRESHOLD) {
        opened_at_.store(steady_clock::now());
        state_.store(Open);
      }
      return fb();                               // fallback
    }
  }
};
```

```go
// circuit breaker, one per dependency — sony/gobreaker.
// Production shops often let Istio do this; shown for reference.
var paymentBreaker = gobreaker.NewCircuitBreaker(gobreaker.Settings{
	Name:    "payment",
	Timeout: 30 * time.Second, // stay open 30s, then half-open to test recovery
	ReadyToTrip: func(c gobreaker.Counts) bool {
		return c.ConsecutiveFailures >= 5 // open after 5 failures
	},
})

func charge(ctx context.Context, order Order) (Result, error) {
	v, err := paymentBreaker.Execute(func() (any, error) {
		return client.Post(ctx, "/charge", order) // skipped while OPEN — no doomed call
	})
	if err != nil { // breaker open or call failed → degrade
		_ = outbox.Enqueue(ctx, order)                  // graceful fallback
		return Result{Status: "pending", ID: order.ID}, nil
	}
	return v.(Result), nil
}
```

## Bulkhead

A bulkhead bounds concurrency so one saturated dependency cannot consume all of a service's
threads or connections. It got its full per-language treatment in the Security chapter, so the
point to re-state here is the interaction: **a bulkhead bounds how many, a timeout bounds how
long** — concurrency-limiting alone does not help if the bounded calls block forever, so the two
must be combined. The mesh provides bulkheading at the connection-pool level, covered just below.

## Load shedding and graceful degradation

Two related patterns engineers tend to skip. **Load shedding** feels like giving up —
deliberately rejecting requests — but it is the difference between degrading and collapsing. The
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
and bulkhead were named for software), the AWS Builders' Library (timeouts, retries, backoff with
jitter), the Istio traffic-management docs, and the metastable-failures research (Bronson et al.,
2021).

### Cross-check it yourself

Reproduce the two dynamics that this appendix turns on. **Cascading and the breaker:** put steady
load on a service with `hey` (or `ghz` for gRPC) while you force its downstream dependency to be
slow, and watch the downstream call count — without a breaker it climbs and the caller's threads
fill (cascading); with a per-dependency breaker configured, the count *plateaus* as the breaker
trips and the caller returns its fallback fast. **Deadline propagation:** issue a request with a
small deadline header to a chain of two services and confirm from the logs that the *second* hop
refuses to start work when the remaining budget is below its minimum, rather than running a query
whose result will be discarded. A breaker that flattens downstream load under failure, and a
deadline that stops doomed work early, are the two load-bearing behaviours of everything here.

This appendix touches difficult operational territory; if you are diagnosing a live incident, the
Google SRE cascading-failures chapter is the fastest way to a shared vocabulary with your team.

---
*Verification status: unverified — code transcribed and normalised from the source decks (the
Quarkus timeout was converted from reactive `Uni` to the blocking `@Blocking` form to match the
other languages), not yet run. Worth confirming on a real build: the Resilience4j
`@TimeLimiter`/`@Retry`/`@CircuitBreaker` annotation config keys, the MicroProfile Fault Tolerance
`@Timeout`/`@Retry`/`@CircuitBreaker` parameters, the Polly v8 `ResiliencePipelineBuilder` strategy
options, the `tenacity` `wait_exponential_jitter` and `purgatory` `OpenedState` APIs, and the Istio
CRD `apiVersion`/field schema against the installed mesh version. The `examples/26-failure-modes/`
runner moves it to verified.*
