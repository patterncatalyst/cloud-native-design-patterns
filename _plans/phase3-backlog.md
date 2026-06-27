# Phase 3 — backlog

Tracking file for the post-second-pass work. The five language decks stay **frozen at
r32**; the REST deck is **complete** (done in a separate project). Site revision counter
continues from r54.

## Sequencing (Robert's call)

Do the **Go/golang work first** (items 2 then 3) to reach full-language parity, then the
content enhancements (items 4–9). Item 1 (audit) runs alongside / informs the rest.

## Items

1. **Fresh end-to-end diagram/content audit** of the now-enriched site. Decks stay frozen.
2. **Add Go (1.26) as a 6th language** to every codetab across the site (35 codetabs in
   19 docs) — language parity.
3. **Build a 6th language deck in Go** (mirrors the five existing decks).
4. **Appendix A** — protocol-differences table; when-to-choose guidance; streaming &
   bidirectional-communication impacts; gRPC performance advantages; a diagram of how RPC
   works client ↔ server.
5. **Appendix C** — protobuf over WebSockets; failover without interruption; performance.
6. **Appendix B** — versioning a Kafka API (key/version); which REST versioning scheme to
   start with and its impact on HATEOAS and security.
7. **Appendix G (coupling)** — module coupling, connascence, semantic / temporal /
   lifecycle / runtime coupling, afferent & efferent coupling, Cynefin, coupling in DDD.
   (ref: coupling.dev/posts/core-concepts/)
8. **Chapter 05 (Event-Driven)** — Core Benefits (loose coupling, real-time
   responsiveness, high scalability) and Common Challenges (eventual consistency, debugging
   complexity, event ordering & duplicates).
9. **Chapter 05** — comparison of Kafka vs Pulsar vs AMQP.

Build whatever diagrams each item needs, in house style.

---

## Go (1.26) stack — proposed, pending Robert's sign-off on the first chapter

Idiomatic, OSS, no managed-cloud lock-in, runs on plain Kubernetes — the same constraints as
the other five language stacks. Chosen to parallel the existing per-language picks.

| Concern | Go choice | Parallels |
|---|---|---|
| HTTP / REST | `net/http` (1.22+ `ServeMux`) + `go-chi/chi` middleware | FastAPI / minimal API |
| gRPC | `google.golang.org/grpc` + `google.golang.org/protobuf` | Grpc.* / grpc++ |
| GraphQL | `99designs/gqlgen` (schema-first) | HotChocolate / Strawberry |
| Kafka | **decision needed** — `confluent-kafka-go` (librdkafka, parallels C++ `modern-cpp-kafka`) **or** `twmb/franz-go` (pure Go) | modern-cpp-kafka / MassTransit |
| Postgres | `jackc/pgx` v5 (direct, no ORM) | C++ `libpq` direct |
| Redis | `redis/go-redis` v9 | sw/redis++ |
| JWT | `golang-jwt/jwt` v5 | jwt-cpp |
| Saga / FSM | `looplab/fsm` or hand-rolled `switch` (no dominant lib — note the gap) | boost::sml |
| Business-rule routing | `yuin/gopher-lua` (embed Lua) — parallels C++ sol2+Lua; note the gap | sol2 + Lua |
| Observability | `go.opentelemetry.io/otel` SDK + `log/slog` (stdlib) | OTel SDK + spdlog |
| Workflow | `go.temporal.io/sdk` | Temporal |
| Resilience | `sony/gobreaker` + `cenkalti/backoff` + `context` deadlines | Resilience4j / Polly |
| Concurrency | goroutines, channels, `context.Context`, `golang.org/x/sync/errgroup` | — |

**Idioms to keep consistent across all Go blocks**
- `context.Context` as the first parameter on anything that does I/O.
- Errors as values: `if err != nil { return …, fmt.Errorf("…: %w", err) }`.
- `defer` for cleanup (the Go analogue of RAII / `using` / try-with-resources).
- Struct embedding over inheritance; small interfaces defined at the consumer.
- `log/slog` for structured logging; no `fmt.Println` in service code.
- Composite literals that produce `{{` (e.g. `[]T{{…}}`) must be wrapped in
  `{% raw %}…{% endraw %}` like the C++ initializer-list blocks, to avoid Liquid collision.

**Canonical codetab order (now six):**
`Spring Boot | Quarkus | .NET | Python | C++ | Go` → fences `java, java, csharp, python, cpp, go`.

## Open decisions for Robert
- **Kafka client**: `confluent-kafka-go` (cgo/librdkafka, matches the C++ stack) vs
  `franz-go` (pure Go, more idiomatic). Default assumption unless told otherwise:
  `franz-go` (pure Go, no cgo — better fit for "plain Kubernetes, simple images").
- Any house Go libraries to pin/avoid (the C++ list had hard exclusions like libpqxx).

## Progress
- (pending) r55 — Go added to `02-communications` as the proof-of-pattern; PAUSE for stack sign-off.
