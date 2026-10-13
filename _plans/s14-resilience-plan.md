# S14 plan — resilience and gRPC through libraries

Planned by Opus 2026-10-13 from main 6656c0a (S13 and the Bibliography merged). Scope from the S13 plan (D3,
tier 3): "circuit breaker in 26, bulkhead in 12, Spring gRPC instead of manual Netty servers", with the chapter prose
rewritten to teach each pattern through the library. Same rule as S13: prefer the idiomatic approach of each
language; do not hand-roll what a maintained library provides.

## User decisions (2026-10-13: all four recommended defaults accepted; D4 without compose gRPC healthchecks)

- **D1 contract changes in `verify.sh`.** Today neither 12 nor 26 tests saturation, and the languages disagree on what
  a full bulkhead does (JVM and C++ return 429, .NET, Python and Go block forever in 12; Go returns 503 in 26).
  Recommended: one rule, "a full bulkhead rejects at once with 429", and new checks that saturate it (12: 6 concurrent
  requests for one tenant, at least one 429, other tenants unaffected; 26: 6 concurrent `/with-bulkhead` calls against
  a slow backend, at least one 429). Check counts grow (12: 16 → 18, 26: 20 → 22); footers follow the final matrix.
- **D2 `/breaker-state` body.** The hand-written counters (`failure_count`, `total_calls`, `total_rejected`) exist
  only because the breaker is hand-written; the libraries expose different metrics. Recommended: the shared body is
  `{"name","state"}` with `state` in `closed|open|half-open` (mapped from each library's enum), plus whatever metrics
  the library exposes natively. `verify.sh` already asserts only `state`; Go gains `name`.
- **D3 C++.** No maintained C++ resilience library is on ConanCenter. Recommended: C++ keeps a hand-written breaker
  and bulkhead (the prose already says "shown for reference"), cleaned up: remove the dead `retry_with_backoff`,
  stop blocking a Drogon event-loop thread with `sleep_for` (use `drogon::sleepCoro` in a coroutine handler), and
  use `std::counting_semaphore` consistently.
- **D4 extra gRPC scope.** Recommended yes: .NET clients move from `GrpcChannel.ForAddress` to the gRPC client
  factory (`AddGrpcClient`, Grpc.Net.ClientFactory), and the Spring inventory services expose the standard gRPC
  health service through Spring gRPC. Recommended no: compose healthchecks on gRPC-only services (needs a probe
  binary in each image; the callers' `/readyz` already gates).

## Pins (Step 0, 2026-10-13)

| Stack | Library | Version | Source |
|---|---|---|---|
| Spring Boot 4.1.1 | `io.github.resilience4j:resilience4j-spring-boot4` | 2.4.0 (built against Boot 4.0.0) | Maven Central |
| Spring Boot 4.1.1 | `spring-boot-starter-aspectj` (the Boot 4 name of the AOP starter) | BOM 4.1.1 | Boot BOM |
| Spring Boot 4.1.1 | `spring-boot-starter-grpc-server` / `-client` (Spring gRPC) | 1.1.1 via BOM 4.1.1 | Boot BOM |
| Spring Boot 4.1.1 | `io.github.ascopes:protobuf-maven-plugin` | 5.1.8 via BOM 4.1.1 | Boot BOM |
| Quarkus 3.40.1 | `quarkus-smallrye-fault-tolerance` | BOM 3.40.1 | Quarkus BOM |
| .NET 10 | `Microsoft.Extensions.Http.Resilience` | 10.10.0 (Polly.Core 8.8.0) | NuGet |
| .NET 10 | `Grpc.Net.ClientFactory` | 2.84.0 (matches Grpc.Net.Client) | NuGet |
| Python 3.14 | `tenacity` | 9.2.1 | PyPI |
| Python 3.14 | `pybreaker` (circuit breaker) | 1.4.1 | PyPI |
| Go 1.27 | `golang.org/x/sync` (semaphore) | v0.24.0 | Go proxy |
| Go 1.27 | `github.com/sony/gobreaker/v2`, `github.com/cenkalti/backoff/v7` | v2.4.0, v7.0.1 (unchanged) | Go proxy |

Rejected at Step 0: Spring Framework 7.0.9 `@ConcurrencyLimit` (documented as blocking, no reject policy, so it cannot
give 429 at once) and `@Retryable` (no breaker); aiobreaker (no release since 2021); purgatory (asyncio-native and in
today's Appendix M Python tab, but no release since November 2024 and a very small project). pybreaker is maintained
(commits in September 2026) and works in asyncio through its `calling()` context manager: `with breaker.calling():
resp = await client.get(...); resp.raise_for_status()`. `call()` returns a generator, so the breaker's lock is
released before the block runs and is not held across the `await`; the generator records success or failure when the
block exits, and an open breaker raises `CircuitBreakerError` on entry. Its `fail_max`, `reset_timeout` and
`success_threshold` match the shared settings (5, 10 s, 2), and its state names are already `closed`, `open`,
`half-open` (D2). Its `call_async` needs Tornado and is not used.

## Inventory (baseline, from two read-only surveys on 6656c0a)

**26-failure-modes** (edge 8080, backend 8081; endpoints `/with-timeout`, `/with-retry`, `/with-breaker`,
`/with-deadline`, `/with-bulkhead`, `/breaker-state`, `/bulkhead-state`):

| Language | Breaker | Retry | Timeout | Bulkhead | Notes |
|---|---|---|---|---|---|
| Spring Boot | hand `CircuitBreaker.java` (104 lines) | hand loop | `SimpleClientHttpRequestFactory` 2 s | `Semaphore(5)` | README says "no Resilience4j" |
| Quarkus | hand `CircuitBreaker.java` (96), state `half_open` | hand loop | rest-client read-timeout | `Semaphore(5)` | README says "no SmallRye Fault Tolerance" |
| .NET | hand, in `Program.cs` (305 lines) | hand loop | CTS 2 s | `SemaphoreSlim(5)` | no PackageReferences at all |
| Python | hand class, no lock | hand loop | httpx Timeout | `asyncio.Semaphore(5)` | |
| C++ | hand class | hand loop inline (dead helper) | libcurl | `counting_semaphore<5>` | `sleep_for` in a Drogon handler |
| Go | sony/gobreaker v2.4.0 (half-open closes after 1) | cenkalti/backoff v7.0.1 | context | buffered chan, 503 | `/breaker-state` = `{state}` only |

Backend contract drift: Quarkus `/call` + `X-Deadline-Remaining`; Go `/` + `X-Deadline-Remaining` (422 on a small
budget); the others `/process` + `X-Deadline-Ms` (200 with `deadline_too_small`). `verify.sh` asserts the edge
results only, so the backends may differ; S14 aligns Quarkus and Go on `/process` + `X-Deadline-Ms` while the code
is open anyway.

**12-security** per-tenant bulkhead (5 per tenant) on `POST /orders`, `GET /bulkhead-state`: Spring and Quarkus
`ConcurrentHashMap<String,Semaphore>` with `tryAcquire(5 s)` then 429; .NET `SemaphoreSlim.WaitAsync()`, Python
`async with Semaphore` and Go channel send all block with no 429; C++ atomic CAS, 429 with different text; Python
reads the private `sem._value`.

**gRPC** (02, 03, 11, 18): every Spring inventory service builds `ServerBuilder.forPort(...)` by hand (02, 03, 11
inside the `@SpringBootApplication` class as a `CommandLineRunner` parked in `awaitTermination()`; 18 as a
`SmartLifecycle` on a hard-coded port), and every Spring client builds `ManagedChannelBuilder...usePlaintext()`.
Spring Boot 4.1.1 already manages Spring gRPC 1.1.1 (`spring-boot-starter-grpc-server`/`-client`) and the
`io.github.ascopes:protobuf-maven-plugin` 5.1.8; the examples use xolstice 0.6.1. Quarkus already uses
`quarkus-grpc`; .NET uses `Grpc.AspNetCore` (library) but builds client channels by hand. Trace propagation over gRPC
in Spring comes from the OTel Java agent (03, 11); 11's check that the inventory span sits inside the order's trace
must keep passing.

**Prose and decks.** Appendix M's codetabs already show the libraries for Spring (Resilience4j), Quarkus (MP Fault
Tolerance), .NET (Polly v8), Python (tenacity, purgatory; S14 moves it to pybreaker) and Go; only C++ is hand-written. So for 26 the examples
move to what the chapter teaches, and the excerpts then become literal. Chapter 12's bulkhead codetab is hand-written
in all six languages and gets rewritten. Site defects found on the way: the Spring tab in `_docs/05-event-driven.md`
(about L577) uses a net.devh `@GrpcClient("sidecar")` that no example backs; the Spring tab in
`_docs/03-composition.md` (about L67) and the Spring deck slides [024] and [064] use an `InventoryGrpcClient` type no
example has. Deck slides per language: bulkhead [085] (.NET [087]); Appendix M timeouts, retry, breaker, bulkhead
[237]–[243] (Spring [241]–[247], .NET [251]–[257]); Spring gRPC [018], errors [136].

## Approach (per language)

- **Spring Boot:** `io.github.resilience4j:resilience4j-spring-boot4` 2.4.0 (on Maven Central; Boot 4 starter) plus
  `spring-boot-starter-aspectj` (the Boot 4 name of the AOP starter). 26: `@CircuitBreaker(name="backend", fallbackMethod=...)`,
  `@Retry`, `@TimeLimiter` or RestClient timeouts, `@Bulkhead(type=SEMAPHORE)`, all configured in
  `application.yaml` (COUNT_BASED window 5, `minimumNumberOfCalls` 5, `failureRateThreshold` 100,
  `waitDurationInOpenState` 10s, `permittedNumberOfCallsInHalfOpenState` 2); `/breaker-state` reads
  `CircuitBreakerRegistry`. 12: a `BulkheadRegistry` keyed by tenant (`maxWaitDuration` 0 → 429 at once). Spring
  Framework 7's own `@Retryable` and `@ConcurrencyLimit` were considered: they have no circuit breaker, and Step 0 found `@ConcurrencyLimit` documented as blocking only, so it cannot
  give 429 at once in 12.
- **Quarkus:** `quarkus-smallrye-fault-tolerance` (BOM 3.40.1). 26: `@CircuitBreaker` (requestVolumeThreshold 5,
  failureRatio 1.0, delay 10 s, successThreshold 2), `@Retry` + `@ExponentialBackoff`, `@Timeout`, `@Bulkhead`,
  `@Fallback`; state through `CircuitBreakerMaintenance`. 12: per-tenant bulkheads cannot be keyed by annotation, so
  a map of programmatic `TypedGuard`s with a bulkhead (the SmallRye programmatic API).
- **.NET:** `Microsoft.Extensions.Http.Resilience` (Polly v8) on the typed `BackendClient` via
  `AddResilienceHandler` (retry, circuit breaker with `CircuitBreakerStateProvider`, timeout), bulkhead via
  `AddConcurrencyLimiter`. 12: the ASP.NET Core rate-limiting middleware (`AddRateLimiter` with a
  `PartitionedRateLimiter` concurrency limiter keyed by tenant, `RejectionStatusCode = 429`). Pins exact.
- **Python:** tenacity for retry; pybreaker for the breaker through `calling()` (see Pins); the Appendix M Python tab moves from purgatory to
  pybreaker; bulkheads stay `asyncio.Semaphore` (standard library) but reject at once and stop reading
  `_value`. Pins exact in `pyproject.toml` + `uv.lock`.
- **Go:** keep gobreaker and backoff; gobreaker `MaxRequests` 2 to match the others; bulkheads via
  `golang.org/x/sync/semaphore` `TryAcquire` (12 per tenant, 26 global) returning 429; `/breaker-state` gains `name`.
- **C++:** per D3.
- **Spring gRPC:** `spring-boot-starter-grpc-server` in the four inventory services (`@Service` beans extending the
  generated `ImplBase`, `spring.grpc.server.port=50051`, graceful shutdown by the starter, standard health service),
  `spring-boot-starter-grpc-client` in the callers (`GrpcChannelFactory` / `@ImportGrpcClients`,
  `spring.grpc.client.channels.inventory.address`), the protobuf plugin switched to the Boot-managed
  `io.github.ascopes` plugin. 18 keeps its deadline (`withDeadlineAfter`) and its `StatusRuntimeException` mapping.
  The OTel agent keeps instrumenting grpc-java; 11's cross-service trace check is the acceptance gate.

## PRs (sequential, each merged green before the next)

| PR | Content | Matrix before merge |
|---|---|---|
| 1 | Example 26 in all six languages + its `verify.sh` (D1, D2) + Appendix M codetabs + the Appendix M deck slides in all six decks | 26 × 6 |
| 2 | Example 12 bulkhead in all six languages + its `verify.sh` (D1) + the chapter 12 bulkhead codetab + slide [085]/[087] in all six decks | 12 × 6 |
| 3 | Spring gRPC in 02, 03, 11, 18 (+ D4 .NET client factory) + the gRPC codetabs (02, 03, 05, 14, 18) + Spring deck [018], [024], [064], [136] (+ .NET slides if D4) | 02, 03, 11, 18 × 6 |
| 4 | CLAUDE.md locked stacks (resilience libraries, Spring gRPC), modernization plan, final full matrix, footers | all 111 |

Order inside a PR: Spring, Quarkus, .NET, Python, Go, C++, one example at a time with
`scripts/verify-matrix.sh NN-x/<lang>` after each. Decks follow the S12/S13 method (edit files applied once,
`deck_text.py --write`, render, `deck_fit` 0).

## Steps

| # | Step | PR | Status |
|---|---|---|---|
| 0 | Preflight: user decisions D1–D4 (done 2026-10-13); pins (done, see Pins); baseline matrix of 12, 26, 02, 03, 11, 18 on main | – | done: baseline 36/36 PASS on main 6656c0a code (2026-10-13) |
| 1 | Example 26 + verify.sh + Appendix M prose + decks | 1 | done: 26 × 6 PASS (22/22 each); Appendix M tabs, READMEs, 18 deck slides |
| 2 | Example 12 bulkhead + verify.sh + chapter 12 prose + decks | 2 | pending |
| 3 | Spring gRPC (+ .NET client factory) + gRPC prose and slide fixes | 3 | pending |
| 4 | CLAUDE.md, modernization plan, final 111 matrix, footers | 4 | pending |

## Acceptance criteria

1. No hand-written breaker, retry loop or semaphore bulkhead in Spring, Quarkus, .NET, Python or Go example code
   (C++ per D3); the READMEs no longer say "no Resilience4j / SmallRye / Polly".
2. No `ServerBuilder.forPort` or `ManagedChannelBuilder` in Spring sources; no `GrpcChannel.ForAddress` in .NET (D4).
3. Every full bulkhead returns 429 at once (12 and 26), tested by `verify.sh` (D1); `/breaker-state` follows D2.
4. 11's inventory span stays inside the order's trace in every language; 18's 409/503 mapping is unchanged.
5. Every changed codetab and slide is an excerpt of its example file; no codetab names a type or annotation that no
   example uses (05 and 03 fixed).
6. Every library pinned exactly; CLAUDE.md lists the resilience libraries and Spring gRPC in the locked stacks.
7. Final `verify-matrix.sh` 111/111; `site`, `content-ok`, `examples-ok` green on every PR; validate_site 0, voice
   scan 0 ban tier, `deck_text --check` ok, `deck_fit` 0 on every changed slide.

## Risks

Resilience4j's count-based window and Polly's failure-ratio sampling open the breaker at slightly different points
than the hand-written consecutive-failure counter (verify sends 6 failures, so 5 must trip it in every library);
half-open close rules differ (Polly lets one probe through); the 11-second reset wait in `verify.sh` leaves 1 s of
slack; Polly's breaker state lives per typed client, so `/breaker-state` must read the same provider instance;
SmallRye FT annotations need CDI-intercepted calls (not `this.` calls); Spring gRPC's port and health defaults
versus the compose wiring; the OTel agent and Spring gRPC's own observation both instrumenting gRPC (double spans);
Conan cache churn if C++ dependencies change (they should not).
