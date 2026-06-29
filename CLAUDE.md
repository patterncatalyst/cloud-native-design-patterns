# CLAUDE.md — cloud-native-design-patterns

Project context for Claude Code. Read this first; it is the memory that does not
otherwise carry over from the claude.ai sessions where this repo was built.

## What this repo is

A Jekyll / GitHub Pages tutorial site teaching cloud-native API design, with **six-language
code tabs** (Spring Boot, Quarkus, .NET, Python, C++, Go), paired **SVG + Excalidraw**
diagrams, and a companion **six-deck PPTX series** in `lgtm-presentation/`.

- Live site: https://patterncatalyst.github.io/cloud-native-design-patterns/
- Owner: `patterncatalyst`. Deploy: GitHub Actions → Pages (`.github/workflows/pages.yml`).
- Run locally: `bundle exec jekyll serve --baseurl ""` → http://localhost:4000

## Current focus — add the runnable examples

Doc footers reference `examples/NN-<slug>/` runners that **do not exist yet**. The job is
to build them, run them locally, and flip each chapter's `*Verification status: …*` footer
from "unverified" to **verified**. This is exactly why we moved to Claude Code: it can
actually run the stack and assert behaviour.

**The 20 promised runners** (by doc number): 01, 02, 03, 04, 05, 06, 09, 11, 12, 16, 17,
18, 19, 21, 22, 24, 25, 26, 27, 28.

Build **one end-to-end first** as a proof-of-pattern, get sign-off, then roll out the rest.

### Proposed example structure

```
examples/
  _infra/            # shared podman compose base: Kafka (Strimzi-like), Postgres, OTel, LGTM
  NN-<slug>/
    compose.yaml     # extends _infra or self-contained
    <service code>   # one canonical reference language (default Python) unless the
                     #   chapter's emphasis dictates otherwise — decide per example
    README.md        # how to run + what to observe
    verify.sh        # asserts expected behaviour with the house test tools
```

Default infra: **Podman compose** locally (`lgtm-podman-stack` patterns). Platform-flavoured
ones (22 L7-routing, 24 monolith→microservices, scaling) target **minikube**
(`lgtm-minikube-stack` patterns). Each example must run standalone.

## Running-example domain

Five services exchanging the `order.placed` fact: **order, payment, inventory,
notification, shipping**. Local = Podman; prod = plain Kubernetes (no managed cloud) with
CloudNativePG, Strimzi/Kafka, Apicurio, Istio, KEDA, Debezium, and OTel → the LGTM stack.

## Locked language stacks (do not substitute)

- **Go** 1.26: `net/http` stdlib (1.22 ServeMux, no chi/gin/echo); `franz-go` (Kafka); pgx v5;
  go-redis v9; gqlgen; golang-jwt v5; OTel Go SDK + `log/slog`; sony/gobreaker +
  cenkalti/backoff; gopher-lua; **goka** (stream processing); coder/websocket; OpenFeature +
  flagd; `signal.NotifyContext` + `atomic.Bool` shutdown.
- **C++**: Drogon (REST + WebSocket); grpc++ sync; cppgraphqlgen; modern-cpp-kafka;
  **libpq direct (not libpqxx)**; sw/redis++; jwt-cpp; boost::sml (saga); sol2 + Lua; OTel
  C++ + spdlog; Conan 2 + CMake 3.27 + Ninja + GCC 14.
  - ⚠️ Reconcile: the r76 outbox codetab in `_docs/05-event-driven.md` used `pqxx` for
    brevity; the example must use **libpq** per this lock (and consider fixing the codetab).
- **JVM / .NET / Python** (as used in the site codetabs): Spring Boot (Spring Kafka,
  `spring-boot-starter-websocket`, Kafka Streams); Quarkus (`websockets-next`, SmallRye
  Reactive Messaging, Kafka Streams); .NET (**MassTransit** for Kafka, **Streamiz** for
  stream processing, Grpc.Net); Python (FastAPI, **aiokafka**, **faust-streaming** for
  stateful processing, grpcio).

## House test tools (prefer these; don't introduce alternatives)

curl + Postman for calls · **hey** for HTTP load · **ghz** for gRPC load · **newman** for
API-test runs (Appendix O is the newman runner = `examples/28-newman/`). Avoid HTTPie/xh,
k6, Locust.

## Site-authoring conventions (when editing docs)

- **Code tabs:** `{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}`
  followed by **6 fenced blocks** in order (`java, java, csharp, python, cpp, go`). C++/Go
  `{{` must be `{% raw %}`-guarded **or** restructured (Go: use `append()` for header slices).
- **Diagrams:** `scripts/generate_diagram.py` — `emit(name, w, h, bands, nodes, edges, notes)`;
  node styles `box/sub/accent/kernel/user/ghost/ink`; edges `amber/dashed/bidir`. Every figure
  ships **both** `name.svg` and `name.excalidraw` in `assets/diagrams/`. QA-render with
  `soffice --headless --convert-to png` (rsvg/cairosvg are unavailable in the old sandbox; in
  Claude Code, `rsvg-convert`/`cairosvg` may be installable for cleaner renders).
- Figure captions **unique and sequential per doc**. Sort version-aware:
  `float("5.10") == 5.1` is a known trap.
- **No positional language** anywhere (slides or site): no "above / below / next slide /
  previous section / see slide N". Cross-reference the **concept**, not a number.
- Chapters end with `### Cross-check it yourself` + an italic `*Verification status: …*`
  footer. **Flip the footer to verified once `examples/NN-*/` runs green.**
- **Validate before commit:** front-matter parses; raw-guard balance; **0 unguarded `{{`**;
  each codetab block-count == its `langs` count; referenced figures exist (`.svg` + `.excalidraw`);
  **0 positional terms**.

## Workflow in Claude Code (changed from claude.ai)

- Edit files in place, run podman/builds/tests directly, commit normally. **The delta-tarball
  + by-hand-git dance from claude.ai is no longer needed.**
- **Conventional Commits**, scopes used in this project: `docs / site / demo / ci / chore /
  fix / feat / refactor / style` with `§N`, `demo-NN`, or `rNN.x` qualifiers.
- The site rev counter reached **r77** in claude.ai; in Claude Code, prefer normal
  per-change commits over the rNN packaging convention.

## Reference authors

Geewax, Zimmermann, Amundsen, Newman, Kleppmann, Bellemare. (The Ch05 event-driven chapter
was expanded to a full event-driven-microservices treatment drawn from Bellemare's
*Building Event-Driven Microservices* — 20 figures, 9 codetabs.)

## Plans

- `_plans/phase3-backlog.md` — full history of the r62–r77 work and the Ch05 expansion tranches.
- `_plans/examples-plan.md` — **create this** as the first step: the 20-runner manifest, the
  per-example structure above, and the per-example language/infra choices as they're decided.
