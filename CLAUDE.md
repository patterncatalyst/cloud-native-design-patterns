# CLAUDE.md — cloud-native-design-patterns

Project context for Claude Code. Read this first; it is the memory that does not
otherwise carry over from the claude.ai sessions where this repo was built.

## What this repo is

A Jekyll / GitHub Pages tutorial site teaching cloud-native API design, with **six-language
code tabs** (Spring Boot, Quarkus, .NET, Python, C++, Go), paired **SVG + Excalidraw**
diagrams, and a companion **eight-deck PPTX set** in `lgtm-presentation/` (six language decks and two policy decks).

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
| `content-ok` | `content.yml` | `scripts/validate_site.py` (the "Validate before commit" rules, including the positional, old-engine and stale-stack checks over `lgtm-presentation/`) + voice scan, ban tier (`scripts/voice-scan.sh`) + `scripts/deck_text.py --check` (the deck text copies) |
| `examples-ok` | `examples.yml` | build matrix per changed example project |

Workflows trigger on `push: branches: [main]` plus `pull_request:` (no `paths:` filters).
`examples.yml` selects projects with `scripts/ci_changed_projects.py`, which you can run
locally (`--base origin/main`). Run `python3 scripts/validate_site.py` and `scripts/voice-scan.sh` before
committing doc changes. Work on a branch, open a PR, wait for the three checks, squash-merge.

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
Example 05 also runs on minikube (`examples/05-event-driven/k8s/`, Appendix R): profile `cndp-k8s`
(docker driver, containerd, Kubernetes v1.36.5), NodePorts 30080 and 30300 published on 127.0.0.1 at
creation, Strimzi 1.2.0 for Kafka, kustomize manifests, `RUNTIME=kubernetes ./verify.sh`. Always pass
`--keep-context` to `minikube start` (setup-profile.sh also restores the prior current-context, because minikube's restart path overrides the flag) and `--context cndp-k8s` to kubectl; never use port-forward,
`minikube tunnel` or `minikube service`. Prometheus/Mimir is published on host port 19090 (Cockpit holds 9090
on Fedora/RHEL). Each example must run standalone. Example 05 also runs on OpenShift Local
(`examples/05-event-driven/openshift/`, Appendix S; Spring Boot, Quarkus, .NET, Python, Go): crc 2.64.0 sized
12 vCPU / 32768 MiB, AMQ Streams from OLM (pinned `startingCSV`, `installPlanApproval: Manual`, only that
InstallPlan approved), Kafka 4.2.0, `restricted-v2` pods with no fixed UID, Red Hat `rhel10/postgresql-18`,
edge-TLS Routes verified with the ingress CA, `RUNTIME=kubernetes KUBECTL=oc ./verify.sh`. OpenShift rules:
call `oc --context crc-admin` on every command and never `oc config use-context` (`setup-crc.sh` restores the
recorded current-context, including "none"); never print or store the kubeadmin password, a token or the pull
secret; images go to the internal registry with `skopeo copy` and a `builder` token held in a shell variable and
passed through a process-substitution authfile (no `skopeo login`, no `--dest-creds`, no token in a file or an
argument list); never `curl -k` or port-forward; CRC is stopped after use, never deleted, and `teardown.sh`
removes only the CRDs our CSV owns or that carry OLM's `operators.coreos.com/amq-streams.cndp-amq-streams` label (and only with no foreign Kafka items), plus OLM's `Operator` object for that package; it reports foreign items and never removes them.

## Running-example domain

Five services exchanging the `order.placed` fact: **order, payment, inventory,
notification, shipping**. Local = Docker; prod = plain Kubernetes (no managed cloud) with
CloudNativePG, Strimzi/Kafka, Apicurio, Istio, KEDA, Debezium, and OTel → the LGTM stack.

## Infrastructure images (pinned, fully qualified)

All shared infra lives in `examples/_infra/` and uses fully qualified names, never `:latest`:
`docker.io/apache/kafka:4.3.1` (KRaft), `docker.io/library/postgres:18.6-alpine` (the volume mounts at
`/var/lib/postgresql`, not `/data`: PGDATA moved to `/var/lib/postgresql/18/docker`),
`docker.io/library/redis:8.10.2-alpine`, `quay.io/debezium/connect:3.7.0.Final`,
`docker.io/apicurio/apicurio-registry:3.3.3`, `ghcr.io/open-feature/flagd:v0.17.0`,
`docker.io/grafana/otel-lgtm:0.36.0`, `docker.io/envoyproxy/envoy:v1.39.3`. kafka-ui is gone: inspect topics
with `kcat` or `kafka-console-consumer.sh` inside the `kafka` container. Test tools: newman 6.2.3 +
newman-reporter-htmlextra 1.23.1, hey v0.1.5, ghz v0.121.0, conftest 0.71.1.
Redis 8 is tri-licensed (RSALv2 / SSPLv1 / AGPLv3); we take the free AGPLv3 open-source option, no license key needed.

## CI cache budget

The repo gets 10 GB of Actions cache. Policy in `examples.yml`: every run restores caches, only a push to
`main` writes them, and each ecosystem keeps a fixed number of entries. Maven and Go are one shared entry each
(`maven-Linux-<hash of all pom.xml>`, `go-Linux-<hash of all go.sum>`), written by the main-only `warm-maven` /
`warm-go` jobs, which resolve every project and delete the superseded entry. Conan is one entry per
distinct `conan.lock` (22), pruned of sources, build trees and downloads before it is saved; on a main miss the
builder stage is forced to run so the cache mount is never empty. BuildKit layers are `type=gha,mode=min`.
Steady state on main: typical about 3.7 GB (22 x 82 MB Conan + Maven 1.0 + Go 0.6 + layers 0.25 + Pages 0.05),
bound 4.9 GB, peak about 8 GB when a Conan key bump or bulk lock change leaves superseded per-lock entries and
layer blobs age out after 7 days unused. Measured: unpruned Conan entries, BuildKit layers (27 blobs = 200 MB).
Partly measured: prune ratio (one project). Estimated: Maven <=1.0 GB, Go <=0.6 GB, Pages. After the first merge,
check the real saved Maven and Go entry sizes and correct the numbers (arithmetic in the `examples.yml` comment).
`cache-cleanup.yml` drops a PR ref's caches when the PR closes (same-repo PRs only).

Check usage with `gh api repos/patterncatalyst/cloud-native-design-patterns/actions/cache/usage`. Drop one PR's
caches with
`gh cache list --ref refs/pull/<N>/merge --limit 100 --json id --jq '.[].id' | xargs -r -n1 gh cache delete`.
The pre-S8 entries use other key prefixes than the current ones, so deleting them is safe at any time, even
after the first main run with the new keys: `conan-Linux-` (old Conan), `setup-java-Linux-x64-maven-` and
`setup-go-Linux-x64-ubuntu24-go-` (old Maven and Go). Current keys start `Linux-conan2-`, `maven-Linux-`, `go-Linux-`.

```bash
for k in conan-Linux- setup-java-Linux-x64-maven- setup-go-Linux-x64-ubuntu24-go-; do
  gh cache list --key "$k" --limit 100 --json id --jq '.[].id' | xargs -r -n1 gh cache delete
done
```

Do not use `gh cache delete --all`: it also removes the entries the current policy just wrote.

## Locked language stacks (do not substitute)

- **Go** 1.27: `net/http` stdlib (1.22 ServeMux, no chi/gin/echo); `franz-go` (Kafka); pgx v5;
  go-redis v9; gqlgen; golang-jwt v5; OTel Go SDK + `log/slog`; sony/gobreaker +
  cenkalti/backoff; gopher-lua; **goka** (stream processing); coder/websocket; OpenFeature +
  flagd; `signal.NotifyContext` + `atomic.Bool` shutdown.
  - Go builds use `docker.io/library/golang:1.27.2` (pinned) on a `ubi10/ubi-minimal` runtime. HOLD:
    the UBI 10 `go-toolset` ships only Go 1.26.x, so it is not used as the builder.
- **C++**: C++23 (`CMAKE_CXX_STANDARD 23`, required, no extensions); Drogon (REST +
  WebSocket); grpc++ sync; cppgraphqlgen; **librdkafka C++ API (`rdkafka++`)** for Kafka
  (modern-cpp-kafka is archived upstream); **libpq direct (not libpqxx)**; sw/redis++;
  jwt-cpp; boost::sml (saga); sol2 + Lua; OTel C++ + spdlog; Conan 2.33.0 + CMake 4.4.4 +
  Ninja 1.13.2 + GCC 15 (`gcc-toolset-15`).
  - C++ builds use `ubi10/ubi:10.2` (pinned) as the builder with `gcc-toolset-15`; CMake and Ninja
    come from the upstream release binaries (sha256-verified; UBI ships cmake 3.31 / ninja 1.11)
    and Conan from a pinned pip venv. The runtime is `ubi10/ubi-minimal` with libstdc++/libgcc linked
    statically (the toolset's libstdc++ is newer than the one in the minimal image).
  - ConanCenter lags upstream for some libraries (see `_plans/modernization-plan.md` S7); take the newest
    ConanCenter version and record the gap. cppgraphqlgen is not on ConanCenter: its recipe lives next to
    the examples that use it.
  - Locks are regenerated with `conan lock create --update` (no lockfile in) so transitive packages take
    the newest ConanCenter version; stale transitive pins are lifted with `override=True` in the
    conanfile (fmt, lz4, util-linux-libuuid, jsoncpp). Held back: abseil 20260107.1 (protobuf 6.33.5),
    protobuf 6.33.5 (grpc is below 7), opentelemetry-proto 1.7.0 (opentelemetry-cpp), taocpp-pegtl 3.2.8
    (cppgraphqlgen needs 3.x), lua 5.4.8 (sol2), librdkafka 2.14.2 and opentelemetry-cpp 1.26.0 (ConanCenter
    behind upstream). flex and bison get `MAKEINFO=true` through a scoped Conan conf, not a fake binary.
    The Conan cache mount id is `cndp-conan2`; CI persists it with buildkit-cache-dance.
  - ⚠️ Reconcile: the r76 outbox codetab in `_docs/05-event-driven.md` used `pqxx` for
    brevity; it now shows libpq, as the example does.
- **JVM / .NET / Python** (as used in the site codetabs): Spring Boot (Spring Kafka,
  `spring-boot-starter-websocket`, Kafka Streams); Quarkus (`websockets-next`, SmallRye
  Reactive Messaging, Kafka Streams); .NET 10.0.12 (**Confluent.Kafka** 2.16.0 for Kafka —
  MassTransit dropped: its abstraction hides the Kafka semantics the examples teach, and v9
  moved to a commercial license; **Streamiz** 1.8.2 for stream processing; Grpc.Net for gRPC;
  images `ubi9/dotnet-100:9.8-1791421718` and `ubi9/dotnet-100-aspnet:9.8-1791363520`, held on
  ubi9 because Red Hat publishes no ubi10 .NET image; every NuGet package pinned exactly); Python (FastAPI, **aiokafka**, **faust-streaming** for
  stateful processing, grpcio).
- **Idiomatic framework features (S13; do not hand-roll what the framework provides):**
  - Schema: `db/init` owns every schema. Hibernate runs `validate`; EF Core has no migrations and no
    `EnsureCreated`. HTTP responses are DTOs, never serialized entities.
  - Quarkus: Hibernate ORM with Panache (JSONB via `@JdbcTypeCode(SqlTypes.JSON)` plus
    `quarkus.hibernate-orm.mapping.format.global=ignore`); SmallRye Health on `/healthz` and `/readyz`;
    `quarkus.shutdown.delay` for draining; REST Client, never `java.net.http`; `@RestPath`/`@RestQuery`/`@RestHeader`
    with `<parameters>true</parameters>` in the compiler plugin (a REST client is not registered without it);
    `@ServerExceptionMapper`.
  - Spring Boot: Spring Data JPA (`open-in-view=false`); Actuator health groups on `/healthz` and `/readyz`;
    `server.shutdown=graceful` plus a `SmartLifecycle` drain bean; `ProblemDetail`; Spring Kafka JSON serdes;
    `RestClient`; Spring Cache for read-through only.
  - .NET: EF Core `DbContext`; `AddHealthChecks` + `MapHealthChecks`; `IHostedLifecycleService` for draining;
    `BackgroundService` for consumers and workers; IConfiguration/Options; typed `AddHttpClient`;
    `AddProblemDetails`; `ILogger`; HybridCache for read-through only.
  - Python: uv with `pyproject.toml` and a committed `uv.lock`; pydantic-settings for configuration.
  - Caching (25): the framework cache serves read-through only; the other strategies keep explicit Redis
    clients so they can report `"source"` and survive a Redis outage.
  - Go: `any`, not `interface{}` (generated `*.pb.go` files excepted). C++ logging: Drogon services use
    Drogon's `LOG_*`; services without Drogon use spdlog. `std::cout`/`std::cerr` only for CLI and test output.
    Adding a Conan dependency to an existing lock uses `conan lock create --lockfile=conan.lock
    --lockfile-partial`, so the other pins stay.
- **Resilience and gRPC through libraries (S14):**
  - Breaker, retry and bulkhead: Spring Boot uses Resilience4j (`resilience4j-spring-boot4` 2.4.0 with
    `spring-boot-starter-aspectj`; annotations on a separate bean, limits in properties; per-tenant
    bulkheads from the `BulkheadRegistry`); Quarkus uses SmallRye Fault Tolerance (annotations on a CDI bean;
    per-tenant bulkheads with the programmatic `Guard`); .NET uses Polly v8 pipelines through
    Microsoft.Extensions.Http.Resilience 10.10.0 with Polly.Extensions and Polly.RateLimiting pinned to 8.8.0
    (the package only sets a floor), and System.Threading.RateLimiting's `PartitionedRateLimiter` for
    per-tenant limits; Python uses tenacity (retry) and pybreaker (breaker, around awaited calls with
    `calling()`), bulkheads on `asyncio.Semaphore`; Go keeps sony/gobreaker and cenkalti/backoff and uses
    `golang.org/x/sync/semaphore` for bulkheads. C++ has no maintained library on ConanCenter, so its breaker
    and bulkhead stay in the service, in Drogon coroutine handlers that never block an event-loop thread.
  - Contract: a full bulkhead refuses at once with 429 (never queues); `/breaker-state` is `{name, state}`
    with `closed|open|half-open`, plus whatever metrics the library exposes. Shared breaker settings:
    5 failures open it, 10 s open, 2 trial successes close it (Polly lets one trial through).
  - Spring gRPC 1.1.1 (managed by Boot 4.1.1): servers are `@GrpcService` beans hosted by
    `spring-boot-starter-grpc-server` on `spring.grpc.server.port` (graceful shutdown, standard health and
    reflection services); callers take channels from `GrpcChannelFactory`
    (`spring.grpc.client.channel.<name>.target`). Never `ServerBuilder` or `ManagedChannelBuilder` by hand.
    The protobuf plugin stays xolstice 0.6.1: the Boot-managed `io.github.ascopes` plugin fails under the
    UBI image's packaged Maven. .NET callers use the gRPC client factory (`AddGrpcClient`).

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
- **Professional voice:** `scripts/voice-scan.sh` must report 0 ban-tier hits (CI gate in
  `content-ok`). Watch-tier hits are reviewed in context: rewrite them unless the word is
  literal (a machine that fails silently, minikube as the subject, a result table). Scope:
  `_docs`, `_parts`, `_example_pages`, `_includes`, `_layouts`, `index.html`, `README.md`,
  `assets/diagrams/*.svg`, `examples/**/*.md`, and the Markdown in `lgtm-presentation/` (the text copies under `text/`, the policy-deck companions, `BUILD.md`; the `.pptx` and `.docx` files are not scanned). When a
  diagram label changes, change the SVG, both `text` and `originalText` in the `.excalidraw`,
  and any alt text or caption that repeats it. The scanner is vendored from lgtm-skills
  (`scripts/voice/README.md`): fix it upstream and re-vendor, never edit the copy.
  Check a few files while writing with `scripts/voice-scan.sh --tier all --hits all <paths>`
  (paths relative to the current directory; `examples/` paths are scanned as Markdown).

## The decks (`lgtm-presentation/`)

Eight decks: Python, Spring Boot, Quarkus, .NET, Go and C++ (`Designing-Cloud-Native-APIs-<Lang>.pptx`,
Appendix R on minikube in all six, no Appendix S) plus `K8s-Environment-Access-Policies` and
`Network-Policy-Process-Advisory` with their `.md` and `.docx` companions. No generator exists: change a deck
in place with `scripts/deck_edit.py` and an edit file under `lgtm-presentation/edits/` (applied once, to the
committed deck; the S12 venv holds python-pptx and cairosvg), then run `python3 scripts/deck_text.py --write`
to refresh the Markdown copies in `lgtm-presentation/text/`. CI fails when a copy is stale
(`deck_text.py --check`). `scripts/deck_render.sh` renders slides for inspection (brand fonts required) and
`scripts/deck_fit.py` checks a render for overflow. Code on a slide follows `examples/`; the decks are
vendor-neutral and name no cloud SDK. `lgtm-presentation/BUILD.md` records the method, slide counts and pins.

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
