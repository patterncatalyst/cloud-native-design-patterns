# S13 plan — idiomatic examples

Planned by Opus 2026-10-12 from main c5d10c2 (S12 merged). Rule (user, 2026-10-12): "always prefer the idiomatic
approach to a language". Review tool: `lgtm-idiomatic-review` (lgtm-skills 3079c03: Quarkus, Spring Boot, .NET,
Python/FastAPI, Go, C++, Kubernetes checklists and `scan.sh`).

## User decisions (2026-10-12)

- Persistence: Hibernate ORM with Panache in every Quarkus example that uses a database; Spring Data JPA in Spring Boot;
  EF Core in .NET. Python (asyncpg), Go (pgx), C++ (libpq) keep their drivers.
- D1 contract: relax the shared health-body patterns in `verify.sh` to accept `ok|UP`, `ready|UP`, `down|DOWN` and
  whitespace; status codes (200/503) and paths (`/healthz`, `/readyz`) unchanged; .NET keeps the exact old bodies.
  Example 21 accepts JVM exit code 0 or 143 if the Step 1 spike confirms 143.
- D3 scope: tiers 1–2 here (persistence, health, shutdown, outbox, uv, REST params, HTTP clients, config, messaging
  serdes, ProblemDetails, workers, logging). Tier 3 (circuit breaker in 26, bulkhead in 12, Spring gRPC instead of manual
  Netty servers) is S14, planned right after, with the chapter prose rewritten to teach the pattern through the library.
- D6: sequential PRs, each merged green before the next: (1) shared contract + Python uv + CI, (2) Quarkus, (3) Spring,
  (4) .NET, (5) Go and C++. Each carries its site tabs and deck edit file.
- Recommendations adopted as defaults: D2 schema stays owned by `db/init` (Hibernate `validate`, fallback `none` with
  the reason recorded; EF Core without migrations/EnsureCreated); D4 framework cache abstraction for read-through only,
  the other five strategies keep explicit Redis clients (they report `"source"` and survive a Redis outage); D5
  pydantic-settings for Python and IConfiguration/Options for .NET; D7 no minikube re-run of 05 unless memory grows
  past the k8s limits; D8 Spring 21 drain delay via a `SmartLifecycle` bean + `AvailabilityChangeEvent` (compose has no
  preStop); D9 Quarkus outbox as a plain Panache `OutboxEvent` entity (the debezium-quarkus-outbox extension would own
  its own schema and break the shared connector).

## Inventory (baseline)

`scan.sh examples` with the new checklists: 343 lines, 35 ban-tier. Kept on purpose: the 19 CLI adapters' stdout
(Quarkus/Spring `System.out`, Python `print`, .NET `Console.Write` in `CliPlaceOrder`, Go `fmt.Print`) and the
deliberately bad `12-security/policy/bad-deploy.yaml` (`:latest`).

| Mechanism | Quarkus (31) | Spring Boot (31) | .NET (32) | Python (32) | Go / C++ |
|---|---|---|---|---|---|
| Persistence | Agroal + raw JDBC in 14 (01, 02, 03, 04, 05×3, 06, 11×2, 17, 19, 21, 25) | JdbcClient/JdbcTemplate, same 14 | NpgsqlDataSource/Command in 15 (+30) | asyncpg, keep | pgx / libpq, keep |
| Health | hand-written JAX-RS in 23 | hand-written `@GetMapping` in 23 | `MapGet` in 24 | keep | keep |
| Shutdown (21) | `sun.misc.Signal` + `Quarkus.asyncExit` | `sun.misc.Signal` + `System.exit`; 18 `addShutdownHook` | `ManualLifetime` + `PosixSignalRegistration`; console consumers (05×2, 11, 06) and 25 flusher hand-rolled | keep | keep |
| Messaging | JSON by hand via `new ObjectMapper` (8) | JSON by hand; 06 raw `KafkaProducer` | consumers → `BackgroundService` | keep | keep |
| Config | `System.getenv` in 19 CLI, 21 | `System.getenv` in 18, 19 CLI, 21 | `Environment.GetEnvironmentVariable` in 28 | `os.environ` in 30 files → pydantic-settings | keep |
| HTTP client | `java.net.http` in 03, 24×2, 26 | RestClient, ok | `new HttpClient` in 03, 24, 26 | httpx | keep |
| Errors (18) | check `@ServerExceptionMapper` | mutable ErrorResponse → `ProblemDetail` | hand-built IResult → `AddProblemDetails` | ok | keep |
| Packaging/logging | REST params: raw JAX-RS in 12 files | — | `Console.Write` logging in 6 services → ILogger | requirements.txt → uv + pyproject + uv.lock (32) | C++ `std::cerr`/printf logging in 21 files → spdlog; Go one `interface{}` → `any` |

Shared contracts to keep: `/healthz` and `/readyz` paths and codes; 01 ready/down + 503; 21 single-SIGTERM drain
(`shutting_down`, 503 "shutting down", `/healthz` 200 while draining, exits within 30 s, log lines "SIGTERM received"
and "shutting down HTTP server"); 25 `"source":"db"|"cache"` and cache-aside surviving a Redis stop; 05 idempotent
consumers; 18 error fields `code`, `traceId`, `retryable`, `retryAfter`; `db/init` schemas unchanged; HTTP responses
stay DTOs, never serialized entities (field names, numeric scale, timestamps unchanged); Kafka payloads byte-compatible.

## Approach (per framework)

- Quarkus: `quarkus-hibernate-orm-panache` (active-record entities over the existing tables; JSONB via
  `@JdbcTypeCode(SqlTypes.JSON)`; 17 `FOR UPDATE` via `findById(id, PESSIMISTIC_WRITE)`; 25 upsert via Hibernate
  `StatelessSession.upsert`); `quarkus-smallrye-health` with `liveness-path=/healthz`, `readiness-path=/readyz`
  (fallback: non-application root `/`); 21 via `quarkus.shutdown.delay-enabled`, `quarkus.shutdown.delay`,
  `quarkus.shutdown.timeout=20s`, a `ShutdownDelayInitiatedEvent` observer and a `@Readiness` check;
  `@RestPath/@RestQuery/@RestHeader`; REST Client instead of `java.net.http`; typed messaging payloads with the
  framework-configured mapper; `@ServerExceptionMapper`.
- Spring Boot: `spring-boot-starter-data-jpa` + `JpaRepository` (`@Lock(PESSIMISTIC_WRITE)`, `@Modifying` native
  `ON CONFLICT` for 25), `spring.jpa.open-in-view=false`; actuator health groups with `additional-path=server:/healthz`
  and `server:/readyz`; 21 via `server.shutdown=graceful`, `spring.lifecycle.timeout-per-shutdown-phase=20s`, a
  `SmartLifecycle` drain bean and a readiness `HealthIndicator`; Spring Kafka JSON serdes and a `ProducerFactory` from
  `spring.kafka.*`; `ProblemDetail`.
- .NET: EF Core `DbContext` per service mapped to the snake_case columns (no migrations), `FromSql(... FOR UPDATE)`,
  `ExecuteSqlAsync` upsert; `AddHealthChecks().AddDbContextCheck<T>(tags: ["ready"])` + `MapHealthChecks` with a
  `ResponseWriter` emitting today's bodies; 21 via `IHostedLifecycleService.StoppingAsync` and
  `HostOptions.ShutdownTimeout`; Worker SDK `BackgroundService` for consumers, the stream processor and the 25 flusher;
  IConfiguration/Options; typed `AddHttpClient`; `AddProblemDetails` + `TypedResults.Problem`; ILogger everywhere.
- Python: uv + `pyproject.toml` + committed `uv.lock`, Containerfiles on the lgtm-python template, pydantic-settings;
  CI marker becomes `pyproject.toml` (`scripts/ci_changed_projects.py`, `examples.yml` python job with setup-uv).
- Go: `any` for `interface{}`. C++: spdlog instead of `std::cerr`/`printf` in service code (CLI and test-runner output
  stays).
- Caching 25: read-through through Quarkus `Cache.get(key, loader)` (quarkus-redis-cache), Spring
  `Cache.get(key, Callable)` (`RedisCacheManager`), .NET `HybridCache.GetOrCreateAsync`; a flag set in the loader
  reports `"source"`.

Rejected: keeping hand-written JVM health (contradicts the rule); faking `"ok"` with a custom Spring status/aggregator;
debezium-quarkus-outbox extension (own schema); EF Core migrations or Hibernate `update` (second schema owner);
annotations for cache-aside (lose `"source"` and outage tolerance); Xabaril AspNetCore.HealthChecks (built-ins plus
`Microsoft.Extensions.Diagnostics.HealthChecks.EntityFrameworkCore` cover it); one mega-PR.

## Pins (re-check at Step 0)

Quarkus extensions from BOM 3.40.1 (no versions). Spring starters from parent 4.1.1. NuGet exact:
`Npgsql.EntityFrameworkCore.PostgreSQL` 10.0.3, `Microsoft.EntityFrameworkCore` and `.Relational` 10.0.12,
`Microsoft.Extensions.Diagnostics.HealthChecks.EntityFrameworkCore` 10.0.12, `Microsoft.Extensions.Hosting` 10.0.12,
`Microsoft.Extensions.Caching.StackExchangeRedis` 10.0.12, `Microsoft.Extensions.Caching.Hybrid` 10.10.0 (check
compatibility). Python: uv 0.13.0, `astral-sh/setup-uv` v10.3.0; package versions exactly as today's requirements.

## Steps

| # | Step | PR | Status |
|---|---|---|---|
| 0 | Preflight: pins, checklists read, scanner baseline (this file), Docker idle, S12 venv | 1 | done (baseline above) |
| 1 | Spikes on 01 and 21 (Quarkus, Spring, .NET): absolute health paths and exact JSON; JVM exit code after framework drain; 21 log lines and "shutting down" body during the delay; Hibernate `validate` on TEXT/JSONB/TIMESTAMPTZ; Spring lifecycle delay keeps actuator serving. Output: exact verify.sh pattern changes | 1 | done |
| 2 | Shared verify.sh pattern relaxations (D1) + Python uv/pydantic-settings (32 projects) + CI marker + Python deck slides 10, 14 and site; matrix for every example whose verify.sh changed | 1 | committed; Python 32/32 PASS, non-Python matrix resumed 2026-10-12 |
| 3 | Quarkus batch (about 26 projects) + site tabs + `Quarkus.fix5.json` | 2 | committed on `refactor/s13-quarkus`, matrix pending |
| 4 | Spring batch (about 26) + site tabs + `Spring.fix6.json` | 3 | committed on `refactor/s13-spring`, matrix pending |
| 5 | .NET batch (about 28) + site tabs + `DotNet.fix6.json` | 4 | committed on `refactor/s13-dotnet`, matrix pending |
| 6 | Go (`any`) and C++ (spdlog) + any deck/site follow-ups | 5 | pending |
| 7 | Final full matrix (111 targets, one at a time), footers with verified counts | 5 | pending |
| 8 | CLAUDE.md locked stacks (ORMs, health, shutdown, uv, schema ownership), modernization plan | 5 | pending |
| 9 | Opus validation per PR (re-scan, checklist sample, `db/init` unchanged, three CI checks green) | each | pending |

Order inside a batch: 01, 21, 04, 05, 17, 19, 25, then the health-only examples. Run `scripts/verify-matrix.sh NN-x/<lang>`
after each example (Docker runs strictly one at a time). Decks follow the S12 method (edit files applied once,
`deck_text.py --write`, render + `deck_fit` 0, colour/caps audits 0). 19 CLI adapters: Quarkus `@QuarkusMain` with the
HTTP server off, Spring `ApplicationRunner` with `web-application-type=none`, .NET host without Kestrel, all reusing
the ORM adapter.

## Acceptance criteria

1. `scan.sh examples`: 0 `requirements.txt`, 0 raw JAX-RS params, 0 hand-written health endpoints (Spring, .NET),
   0 `sun.misc.Signal`/`PosixSignalRegistration`, 0 `Console.Write` / `std::cerr` service logging, 0 hand-built Npgsql
   data sources, 0 `JdbcTemplate`; ban-tier survivors only the recorded CLI/fixture lines.
2. No `JdbcClient`, `AgroalDataSource`, `javax.sql.DataSource`, `NpgsqlCommand`, `java.net.http`, `new HttpClient`,
   `Environment.GetEnvironmentVariable`, `Quarkus.asyncExit`, `ManualLifetime`, `System.exit` (except 19 CLI) in Quarkus,
   Spring and .NET sources.
3. Every Quarkus HTTP service has `quarkus-smallrye-health`; every Spring HTTP service the actuator; every .NET service
   `MapHealthChecks`.
4. Hibernate `validate` (or `none` with the reason recorded); no EF migrations or `EnsureCreated`; `git diff main --
   'examples/*/db/init'` empty.
5. Every `PackageReference` exact; every Python project has `pyproject.toml` + `uv.lock`.
6. `verify.sh` diffs touch only the D1 patterns; check counts unchanged per example.
7. Final `verify-matrix.sh` 111/111 PASS; per-target runs green in each batch; `examples-ok`, `content-ok`, `site` green
   on every PR.
8. Changed decks: `deck_text.py --check` ok, `deck_fit` 0, audits 0, every changed slide rendered and read; changed
   codetabs and slides match their example files.
9. `validate_site.py` 0 errors, voice scan 0 ban tier; CLAUDE.md and `modernization-plan.md` updated; footers changed
   only after green runs.

## Risks

JVM exit 143 (D1b); Quarkus absolute health paths; ordering of the Quarkus shutdown events against the 21 log/body
asserts; Spring lifecycle phase versus `WebServerGracefulShutdownLifecycle`; Hibernate `validate` on TEXT/JSONB; JSON
and Kafka payload drift (DTOs only, compare with kcat); idempotent consumers under JPA/EF rollback; Hibernate/EF memory
and start time against compose `--wait` and the 05 k8s limits; deck `expect` counts (measure on committed decks);
Python lock drift (diff `uv export` against the old pins); long matrix runs.
