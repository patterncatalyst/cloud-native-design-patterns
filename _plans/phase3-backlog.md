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
7. **Appendix G (coupling)** ✅ **(r66).** — module coupling, connascence, semantic / temporal /
   lifecycle / runtime coupling, afferent & efferent coupling, Cynefin, coupling in DDD.
   (ref: coupling.dev/posts/core-concepts/)
8. **Chapter 05 (Event-Driven)** ✅ **(r67).** — Core Benefits (loose coupling, real-time
   responsiveness, high scalability) and Common Challenges (eventual consistency, debugging
   complexity, event ordering & duplicates).
9. **Chapter 05** ✅ **(r67).** — comparison of Kafka vs Pulsar vs AMQP.

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
- **r66 — item 7 (Appendix G) DONE.** Added the classical coupling vocabulary mapped to the
  model (module/connascence/semantic/temporal/lifecycle/runtime, afferent-efferent + the
  instability metric; Fig G.4 connascence), a Cynefin coupling-strategy section (Fig G.5),
  and a DDD context-mapping bridge; coupling.dev + connascence.io references added.
- **r67 — items 8 + 9 (Chapter 05) DONE.** Added "Core benefits — and the costs they carry"
  (loose coupling/real-time/scalability paired with eventual consistency/debugging/ordering
  & duplicates) and "Choosing the substrate: Kafka vs Pulsar vs AMQP" (comparison matrix +
  log-vs-queue prose). Table-led, no new figures. **Phase-3 content items 4–9 all complete.**
- **r68 — GitHub-link 404 FIXED.** Root cause was the placeholder `github_username`
  (`RobertSedor`). Set to `patterncatalyst` in `_config.yml`; all 5 link sites (header,
  footer ×3, homepage) now resolve to `github.com/patterncatalyst/cloud-native-design-patterns`.
- **r69 — Ch05 deep expansion, tranche 1 (substrate architectures).** Added "Inside the
  substrates" with Kafka (Fig 5.5), Pulsar (Fig 5.6), and AMQP (Fig 5.7) architecture
  deep-dives — architecture + advantages + decoupling; log-truth figure renumbered to 5.8;
  duration 30→36. First of several tranches building Ch05 toward Bellemare depth.
- **r70 — README cleanup + final QA pass.** Rewrote the top-level `README.md` (six languages,
  six decks, running-example system, live-site URL, current layout). Ran a full mechanical QA
  sweep across all 30 docs + 126 figures + config — **0 defects** (see `_plans/qa-pass-r70.md`):
  codetab block/order, raw-guards, figure pairing/sequencing, orphans, positional language,
  stale markers all clean. Item 1 (fresh audit) ✅.
- **r71 — Ch05 expansion tranche 2 (Building EDMs + sidecar).** Added the consume→process→produce
  anatomy (Fig 5.9, stateless vs stateful) and the sidecar pattern (Fig 5.10) with two six-language
  codetabs; figures now 5.1–5.10; duration 36→42.
- **r72 — Ch05 reorg + tranche 3.** Moved "the log is the source of truth" up to a `###` directly
  under the Kafka block (was stranded after AMQP); figures renumbered to stay sequential
  (log-truth→5.6, Pulsar→5.7, AMQP→5.8). Added tranche 3: eventification/CDC (Fig 5.11) and
  ECST-vs-notification + local denormalized views (Fig 5.12, six-language fold-into-upsert codetab).
  Figures now 5.1–5.12; duration 42→48.
- **r73 — Ch05 tranche 4 (stateful EDMs).** Added the state store + compacted changelog with
  replay-on-rebalance (Fig 5.13) and order-independent state — LWW by version, commutativity,
  idempotency, co-partitioned joins (Fig 5.14). Two six-language codetabs (a deliberately
  heterogeneous aggregation: Kafka Streams / Streamiz / Faust / goka / manual-store-plus-changelog;
  and a uniform LWW guarded-upsert). Figures now 5.1–5.14; duration 48→54.
- **r74 — Ch05 tranche 5 (deterministic stream processing).** Added event-time-vs-processing-time
  + watermarks/late-events with the determinism-on-replay rule (Fig 5.15), and checkpoints +
  exact recovery + intentional reprocessing (Fig 5.16) with a six-language transactional
  exactly-once codetab. Windowing mechanics cross-referenced to Ch06, not duplicated. Figures now
  5.1–5.16; duration 54→60.
- **item 3 — Go deck COMPLETE (deck-side r01.0).** In-place retarget of the canonical
  Python deck; `Designing-Cloud-Native-APIs-Go.pptx` (272 slides) added to
  `lgtm-presentation/` with `BUILD.md`. The five language decks stay frozen at r32.


## Chapter 05 deep expansion (Bellemare) — in progress

Source of truth: Adam Bellemare, *Building Event-Driven Microservices*. Goal: grow Ch05
from the substrate comparison into a full event-driven-microservices treatment, with a
house diagram (and code where it illustrates) per concept.

- **Tranche 1 ✅ (r69)** — substrate architecture deep-dives: Kafka / Pulsar / AMQP
  (Figs 5.5–5.7), advantages + decoupling.
- **Tranche 2 ✅ (r71)** — Building EDMs: consume → process → produce anatomy (Fig 5.9),
  stateless vs stateful, and the **sidecar** pattern (Fig 5.10); two six-language codetabs
  (transform-and-reemit; publish-via-local-sidecar). Duration 36→42.
- **Tranche 3 ✅ (r72)** — Eventification (data liberation / CDC, table–stream duality;
  Fig 5.11) and event-carried state transfer vs notification + denormalized local views
  (Fig 5.12, fold-into-upsert codetab).
- **Tranche 4 ✅ (r73)** — Stateful EDMs: local state store + compacted changelog with
  replay-to-recover (Fig 5.13, heterogeneous aggregation codetab) and order-independent state
  via last-writer-wins / commutativity / idempotency + co-partitioned joins (Fig 5.14, LWW codetab).
- **Tranche 5 ✅ (r74)** — Deterministic stream processing: event time vs processing time +
  watermarks/late events (Fig 5.15), and checkpoints/recovery/reprocessing (Fig 5.16) with a
  transactional exactly-once codetab. Windowing depth deferred to Ch06 by cross-reference.
- **Tranche 6** — Workflows: choreography vs orchestration vs **saga** (bridges Appendix D).
  Diagram(s).
- **Tranche 7** — Integrating EDA into existing systems (strangler + CDC + outbox);
  **multi-tenancy** considerations; dealing with **eventual consistency** in practice.
  Diagram(s) + table.
