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

## Current focus — modernization

The 20 runnable examples exist in all six languages. The work now is the staged
modernization (runtime, versions, tests, CI) tracked step by step in
`_plans/modernization-plan.md`. Read it before starting a step, and update its status
table when a step lands. Examples are flipped to **verified** (footer in the chapter) only
after their `verify.sh` runs green.

## CI and branch protection

`main` is protected by a repository ruleset: **PR-only, squash merge, zero required
approvals**, no direct pushes. The required checks are summary jobs that always report:

| Check | Workflow | Covers |
|-------|----------|--------|
| `site` | `pages.yml` | Jekyll build (deploys only on a push to main) |
| `content-ok` | `content.yml` | `scripts/validate_site.py` (the "Validate before commit" rules) |
| `examples-ok` | `examples.yml` | build matrix per changed example project |

Workflows trigger on `push: branches: [main]` plus `pull_request:` (no `paths:` filters).
`examples.yml` selects projects with `scripts/ci_changed_projects.py`, which you can run
locally (`--base origin/main`). Run `python3 scripts/validate_site.py` before committing doc
changes. Work on a branch, open a PR, wait for the three checks, squash-merge.

## Example layout

```
examples/
  _infra/            # shared docker compose base: Kafka, Postgres, OTel, LGTM
  NN-<slug>/
    verify.sh        # shared — asserts expected behaviour (language-agnostic HTTP tests)
    README.md        # how to run + what to observe
    db/init/         # shared SQL schema (where applicable)
    python/
      compose.yaml   # includes ../../_infra/..., volumes ../db/init
      Containerfile  # or per-service Containerfiles inside service dirs
                     # (Containerfile.<svc> for .NET); compose uses
                     # build.dockerfile: Containerfile
      <service code>
    spring-boot/     # same API contract, different language
      compose.yaml
      Containerfile
      <service code>
```

Default infra: **Docker Engine with `docker compose`** on Fedora/RHEL (`lgtm-docker-stack`
patterns). Run an example with `docker compose up -d --build --wait` and tear it down with
`docker compose down -v`. All examples, including 09, 12, 22 and 24, run on compose.
minikube (`lgtm-minikube-stack` patterns) and OpenShift Local are optional paths added later in
the modernization plan. Prometheus/Mimir is published on host port 19090 (Cockpit holds 9090
on Fedora/RHEL). Each example must run standalone.

## Running-example domain

Five services exchanging the `order.placed` fact: **order, payment, inventory,
notification, shipping**. Local = Docker; prod = plain Kubernetes (no managed cloud) with
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
  Reactive Messaging, Kafka Streams); .NET 10.0.12 (**Confluent.Kafka** 2.16.0 for Kafka —
  MassTransit dropped: its abstraction hides the Kafka semantics the examples teach, and v9
  moved to a commercial license; **Streamiz** 1.8.2 for stream processing; Grpc.Net for gRPC;
  images `ubi9/dotnet-100:9.8-1791421718` and `ubi9/dotnet-100-aspnet:9.8-1791363520`, held on
  ubi9 because Red Hat publishes no ubi10 .NET image; every NuGet package pinned exactly); Python (FastAPI, **aiokafka**, **faust-streaming** for
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

- Edit files in place, run docker, builds and tests directly, commit normally. **The delta-tarball
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
- `_plans/examples-plan.md` — the runnable-examples manifest and per-example language/infra choices.
- `_plans/modernization-plan.md` — the current modernization: section order, decisions, pins, status.
