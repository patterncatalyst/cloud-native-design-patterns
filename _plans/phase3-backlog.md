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
4. **Appendix A** ✅ **(r63).** — protocol-differences table; when-to-choose guidance; streaming &
   bidirectional-communication impacts; gRPC performance advantages; a diagram of how RPC
   works client ↔ server. **+ six-language code samples** (house codetabs).
5. **Appendix C** ✅ **(r64).** — protobuf over WebSockets; failover without interruption; performance.
   **+ six-language code samples** (house codetabs).
6. **Appendix B** ✅ **(r65).** — versioning a Kafka API (key/version); which REST versioning scheme to
   start with and its impact on HATEOAS and security. **+ six-language code samples**
   (house codetabs).

   > Items 4–6 currently carry prose/diagrams but no `codetabs.html` blocks; add
   > `Spring Boot|Quarkus|.NET|Python|C++|Go` samples for each new concept they introduce.
7. **Appendix G (coupling)** — module coupling, connascence, semantic / temporal /
   lifecycle / runtime coupling, afferent & efferent coupling, Cynefin, coupling in DDD.
   (ref: coupling.dev/posts/core-concepts/)
8. **Chapter 05 (Event-Driven)** — Core Benefits (loose coupling, real-time
   responsiveness, high scalability) and Common Challenges (eventual consistency, debugging
   complexity, event ordering & duplicates).
9. **Chapter 05** — comparison of Kafka vs Pulsar vs AMQP.

10. **Site bug — broken top-nav (404). ✅ FIXED (r62).** The primary nav in
    `_includes/header.html` (and the breadcrumb fallback in `_layouts/tutorial.html`)
    pointed at template-scaffold paths that don't exist here. Resolved by repointing
    to real docs:
    - *Tutorial* → `/docs/01-cloud-native-principles/` (first content chapter)
    - *Prerequisites* → `/docs/00-setting-up/` (the setup chapter)
    - *GitHub ↗* → `https://github.com/RobertSedor/cloud-native-design-patterns`
      (config-driven; unchanged). If this still 404s for visitors it's repo
      **visibility** (private repo) — make the repo public or adjust
      `github_username`/`github_repo` in `_config.yml`.

Build whatever diagrams each item needs, in house style.

---

## Go (1.26) stack — proposed, pending Robert's sign-off on the first chapter

Idiomatic, OSS, no managed-cloud lock-in, runs on plain Kubernetes — the same constraints as
the other five language stacks. Chosen to parallel the existing per-language picks.

| Concern | Go choice | Parallels |
|---|---|---|
| HTTP / REST | `net/http` stdlib (1.22+ `ServeMux`) — no router dep | FastAPI / minimal API |
| gRPC | `google.golang.org/grpc` + `google.golang.org/protobuf` | Grpc.* / grpc++ |
| GraphQL | `99designs/gqlgen` (schema-first) | HotChocolate / Strawberry |
| Kafka | `twmb/franz-go` (pure Go, no cgo) — **LOCKED** | modern-cpp-kafka / MassTransit |
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

## Decisions — LOCKED (Robert, r55 review)
- REST baseline: **stdlib `net/http`** (1.22+ `ServeMux`), no router dependency (chi).
- Kafka: **`franz-go`** (pure Go, no cgo).
- Style: idiomatic Go, "Idiomatic Go" book conventions — clean, small, error-as-value.

## Progress
- r55 — `02-communications` Go proof-of-pattern shipped; stack signed off.
- **r56–r61 — item 2 COMPLETE.** All 35 codetabs across 19 docs carry six languages
  (`Spring Boot|Quarkus|.NET|Python|C++|Go`); homepage/_config/README updated.
- **r62 — item 10 (broken top-nav 404) FIXED.** Repointed Tutorial/Prerequisites in
  `_includes/header.html` + the `_layouts/tutorial.html` breadcrumb to real docs.
- **r63 — item 4 (Appendix A) DONE.** Added the RPC stub-to-stub mechanism (Fig A.4),
  streaming & bidirectional modes (Fig A.5), a gRPC-performance section, and two
  six-language gRPC codetabs (unary client call + server-streaming handler).
- **r64 — item 5 (Appendix C) DONE.** Added protobuf-over-WebSockets (envelope proto,
  Fig C.4, six-language binary-frame codetab), failover-without-interruption (Fig C.5),
  and a performance-levers section; checklist + duration updated.
- **r65 — item 6 (Appendix B) DONE.** Added Kafka API versioning (key vs version, registry
  compatibility, Fig B.5, six-language producer codetab) and a REST where-to-start section
  with its HATEOAS + security impact.
- **GitHub-link 404 root cause:** `github_username` in `_config.yml` is a placeholder
  (flagged in `_plans/iteration-plan.md` open decisions). Link is built correctly in 5
  places (header, footer ×3, homepage); awaiting the real GitHub owner/repo to set it.
- **item 3 — Go deck COMPLETE (deck-side r01.0).** In-place retarget of the canonical
  Python deck; `Designing-Cloud-Native-APIs-Go.pptx` (272 slides) added to
  `lgtm-presentation/` with `BUILD.md`. The five language decks stay frozen at r32.
