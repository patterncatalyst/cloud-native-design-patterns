# Modernization plan — cloud-native-design-patterns

Approved by the user 2026-10-10. Relay: Opus plans, Sonnet executes, Opus validates.
Each step gets its own branch, a PR, green CI and a squash-merge before the next step starts.

## User decisions (2026-10-10)

1. Go → **1.27.2** (builder `docker.io/library/golang:1.27.2`, runtime `ubi10/ubi-minimal` pinned). Update the CLAUDE.md lock.
2. minikube: S9 adds a real minikube deployment of 05-event-driven plus its own appendix (docker driver, containerd, K8s v1.36.5, loopback `--ports` NodePorts).
3. Locked stacks: **rewrite the examples to use the locked libraries**, not just record deviations:
   - .NET: Streamiz (stream processing); Kafka stays on Confluent.Kafka (user decision during S4: MassTransit dropped, v9 is commercial and its abstraction hides Kafka semantics)
   - Go: goka, gqlgen, golang-jwt v5, gopher-lua, sony/gobreaker + cenkalti/backoff, OpenFeature + flagd
   - Python: faust-streaming
   - C++: cppgraphqlgen, jwt-cpp, boost::sml, sol2, libpq (not libpqxx)
   Do this in each language's branch. Close #31–#35 after.
4. lgtm-skills: add the branch-protection standard to lgtm-github; remove the old container-engine wording from lgtm-quarkus, lgtm-spring-boot, lgtm-python and lgtm-crc; update the version pins (including lgtm-docker-stack) to the newest stable.
5. C++: modernize to **C++23 (C++26 if the toolchain supports it)** and the newest tooling (GCC, CMake, Conan, Ninja). CRC appendix excludes C++, per the recommendation (interpretation; the user may correct it).

## Order and status

| Step | Branch | Item | Status |
|---|---|---|---|
| 0a-1 | lgtm-skills feature/github-branch-protection | prereq | done (lgtm-skills PR #36, #37, release r4.x) |
| 0a-2 | lgtm-skills fix/docker-runtime-and-pins | 4 | done (lgtm-skills PR #36, #37, release r4.x) |
| 0b | feature/ci-branch-protection | prereq | done (PR #58; ruleset main 24831520: site, content-ok, examples-ok) |
| S1 | feature/docker-engine-runtime | 6 | done (111/111 PASS on Docker; final rerun after the Opus review) |
| S2 | chore/quarkus-3.40-lts | 1 | done (18/18 Quarkus PASS on 3.40.1; closes #32) |
| S3 | chore/spring-boot-4.1 | 1 | done (111/111 PASS after the Opus review; closes #31) |
| S4 | chore/dotnet-10-pins (+ Streamiz) | 3 | validated; 19/19 .NET PASS |
| S5 | chore/python-3.14 (+ faust) | 5 | pending |
| S6 | chore/go-toolchain (Go 1.27.2 + locked libraries) | 2+4 | pending |
| S7 | chore/cpp-toolchain-ubi10 (C++23/26 + locked libraries) | 2+4 | pending |
| S8 | chore/infra-images | 2 | pending |
| S9 | docs/minikube-docker-driver (+ 05 on minikube) | 7 | pending |
| S10 | feature/openshift-local-appendix | 8 | pending |
| S11 | docs/professional-voice | 9 | pending |
| S12 | docs/deck-refresh | 10 | pending |

## Target pins (verified 2026-10-09; re-check at the start of each branch)

| Component | Version or image |
|---|---|
| Quarkus | 3.40.1 |
| Spring Boot | 4.1.1, Java 25, Jackson 3, OTel Java agent |
| JVM images | ubi10/openjdk-25:1.24-15, ubi10/openjdk-25-runtime:1.24-15 |
| .NET | 10.0.12; images ubi9/dotnet-100:9.8-1791421718 and ubi9/dotnet-100-aspnet:9.8-1791363520 (no ubi10 image exists) |
| Python | 3.14; image ubi10/python-314-minimal:10.2-1791464217, fallback ubi9/python-314:9.8-1791466446 |
| Go | 1.27.2; runtime ubi10/ubi-minimal:10.2-1791444377 |
| C++ | builder ubi10/ubi:10.2-1791444044, Conan 2.33.0 |
| Kafka | apache/kafka:4.3.1 |
| Postgres | postgres:18.6-alpine (mount /var/lib/postgresql) |
| Redis | redis:8.10.2-alpine |
| Debezium | quay.io/debezium/connect:3.7.0.Final |
| Apicurio | apicurio-registry:3.3.3 |
| flagd | ghcr.io/open-feature/flagd:v0.17.0 |
| LGTM | grafana/otel-lgtm:0.36.0 |
| Envoy | envoyproxy/envoy:v1.39.3 |
| kafka-ui | removed (use kcat) |
| Test tools | newman 6.2.3, htmlextra 1.23.1, hey v0.1.5, ghz v0.121.0 |
| minikube | v1.39.0, Kubernetes v1.36.5 |
| Operators | Strimzi 1.2.0, CNPG v1.30.1, KEDA v2.21.0, Istio 1.31.1 |
| CRC | crc 2.64.0 / OCP 4.22.14; AMQ Streams per lgtm-crc (check packagemanifest) |

## Key facts from the inventory

- 21 example directories; 18 have all six languages (108 variants); 09 is configuration only, 28 is Newman, 30 is .NET only.
- 188 Dockerfile*, 0 Containerfile; 130 files mention the old container engine.
- 27 compose files carry a `devices: /dev/null` workaround for the old container engine.
- 04-data spring-boot and quarkus inline the infra instead of using `include:`.
- No unit tests anywhere. No example CI. Disabled ruleset `force-push` (18550149).
- 01/cpp uses libpqxx, which the stack lock forbids. Example 30 pins .NET preview packages.
- Docs say "four languages" and "appendices A–O"; they claim 09/12/22/24 run on a cluster, but none do.
- lgtm-skills install-all.sh would replace the symlinked skill installs with copies, so never run it.

## Acceptance criteria (summary; full list in the planner report)

- 0a: lgtm-github has the branch-protection section and gh-protect-branch.sh; lgtm-skills has CI (skills-ok) and an active ruleset; release r4.x is published.
- 0b: only the `main` ruleset (checks site, content-ok, examples-ok); a direct push to main is rejected; remote branches are main only.
- S1: 0 references to the old container engine outside _plans and the decks; 0 Dockerfile*; Fedora/RHEL-only prerequisites; baseline matrix green; #31–#35 handled.
- S2–S7: every project builds; verify.sh green for that language's variants; images pinned, with no :latest.
- S8: 0 :latest, -latest or kafka-ui; full matrix green.
- S9: minikube appendix with evidence; profile stopped.
- S10: Appendix R with evidence for 5 languages; scrub clean; CRC stopped and clean.
- S11: voice scan reports zero ban-tier hits and is enforced in CI.
- S12: 0 references to the old container engine in the decks; current versions; OpenShift Local slides; rendered and inspected.

## Evidence

Run every example with `scripts/verify-matrix.sh` (one target at a time: `docker compose up -d --build --wait`, `verify.sh`, `docker compose down -v`).

### S1 baseline on Docker Engine (2026-10-10)

Docker 29.8.2, compose v5.5.1, Fedora 44. Versions as found (Spring Boot 3.4.1, Quarkus 3.33.2, .NET 10 with floating packages, Python 3.12, Go 1.26.5, C++ on ubi9; Kafka 3.8.0, Postgres 16, otel-lgtm 0.8.1).

**111/111 targets PASS**: 18 examples × 6 languages, plus 09, 28 and 30. After the Opus validation round (footer claims aligned with verify.sh, conftest required, 21 restart check tightened, 30 summary format), the whole matrix was rerun from the final tree: 111/111 PASS with the same per-example counts.

| Example | Checks per language |
|---|---|
| 01 | 10 |
| 02 | 10 |
| 03 | 8 |
| 04 | 8 |
| 05 | 10 |
| 06 | 10 |
| 09 | 8 |
| 11 | 10 |
| 12 | 16 |
| 16 | 6 |
| 17 | 11 |
| 18 | 13 |
| 19 | 17 |
| 21 | 10 |
| 22 | 15 |
| 24 | 19 |
| 25 | 26 |
| 26 | 20 |
| 27 | 14 |
| 28 | 11 |
| 30 | 5 |

Defects the baseline found and fixed in S1:

| Example | Defect | Fix |
|---|---|---|
| 02, 03 python | strawberry 0.254 broke when graphql-core 3.3 (unpinned transitive) dropped `ExecutionContext` | pin graphql-core 3.2.9 |
| 11 | metric checks ran before the 60s SDK export interval | poll Prometheus for up to 90s |
| 12 | conftest policy used pre-v1 Rego and only ever "passed" because conftest was missing | Rego v1 syntax; conftest 0.71.1 now required |
| 16 | WebSocket checks needed `websockets` and `aiohttp` on the host | verify.sh installs pinned copies into a cached venv |
| 17, 21 | restart checks always recreated the Spring Boot service, so other languages died mid-script | stop/start the running container and poll |
| 18 | first check raced order-service startup (no healthcheck) | wait for healthz first |
| 19 | CLI adapter check ran Python shims; .NET had no CLI adapter | `cli-place-order` on PATH in every image; .NET CLI driving adapter added |
| 22 | envoy healthcheck used curl, which the image lacks | bash `/dev/tcp` with HTTP/1.1 (Envoy rejects 1.0 with 426) |
| all JVM | each image build re-downloaded every dependency; Maven Central throttled the host's IPv4 (HTTP 429) for hours | BuildKit cache mount for `~/.m2` and resolver retry on 429/503 |
| lgtm port 9090 | cockpit holds host 9090 on Fedora/RHEL | Prometheus published on host 19090 |

### S2 Quarkus 3.40.1 LTS (2026-10-10)

- 31/31 Quarkus projects on quarkus.platform.version 3.40.1, Java 25, pinned `ubi10/openjdk-25[-runtime]:1.24-15`, non-root UID 185 with group-0 ownership.
- gRPC projects read `../proto` through `quarkus.grpc.codegen.proto-directory`; plain `mvn package` works.
- Locked stack: 06 stream processor rewritten on `quarkus-kafka-streams` (windowed aggregation by merchant, running updates, bad totals skipped, LogAndContinue deserialization). Every other Quarkus Kafka path already used SmallRye Reactive Messaging; 16 uses websockets-next.
- Third-party pins: compiler 3.16.0, surefire/failsafe 3.6.0, micrometer-registry-otlp 3.7.0, OpenFeature sdk 1.23.0, flagd 0.14.2.
- No source changes were needed for 3.33 to 3.40.
- Live: **18/18 Quarkus targets PASS**, rerun from the final tree after the Opus review; counts unchanged.

### S3 Spring Boot 4.1.1 (2026-10-10)

- 31/31 Spring Boot projects on 4.1.1, Java 25, Spring Framework 7, Jackson 3 (`tools.jackson`), Boot 4 starters (`spring-boot-starter-webmvc`, `spring-boot-starter-kafka`), Spring Kafka 4 Jackson serializers.
- OpenTelemetry Java agent 2.32.0 (SHA-256 verified against Maven Central) replaces the starter in the 16 services that export telemetry; logback MDC supplies `trace_id`.
- Pinned `ubi10/openjdk-25[-runtime]:1.24-15`, non-root UID 185, group-0 ownership.
- gRPC projects read `../proto` via `protoSourceRoot`; CI no longer copies protos.
- Locked stack: 06 stream processor rewritten as a Kafka Streams topology (same contract as Quarkus); everything else already used Spring Kafka and spring-boot-starter-websocket.
- Every example compose file has a unique project name `cndp-<NN>-<lang>`: before this, examples of one language shared images, networks and named volumes.
- Live: 18/18 Spring Boot PASS on the first run; after the Opus review fixes (caching and observability codetabs, MDC-only trace_id, native access for RocksDB, dead OTEL env, compose names) the **full matrix was rerun: 111/111 PASS**.

Carried forward:
- S4: extend `examples/30-blazor-signalr/verify.sh` to cover Redis backplane scale-out and circuit recovery (the footer states they are not yet covered).

### S4 .NET 10.0.12 (2026-10-10)

- 32 .NET projects (including example 30) on net10.0 with every PackageReference pinned exactly: OpenTelemetry 1.19.1 (AspNetCore instrumentation 1.19.0), Npgsql 10.0.3, Confluent.Kafka 2.16.0, Streamiz.Kafka.Net 1.8.2, Grpc.AspNetCore/Grpc.Net.Client/Grpc.Tools 2.84.0, Google.Protobuf 3.36.2, StackExchange.Redis 3.4.0, HotChocolate 16.6.8, OpenFeature 2.14.1, OpenFeature.Contrib.Providers.Flagd 0.5.0, SignalR 10.0.12 (the preview.5 packages are gone).
- Images `ubi9/dotnet-100:9.8-1791421718` and `ubi9/dotnet-100-aspnet:9.8-1791363520`, non-root UID 1001, group-0 ownership, BuildKit NuGet cache mount. HOLD: Red Hat publishes no ubi10 .NET image.
- Locked stack: 06 stream processor rewritten on Streamiz (same contract as Quarkus/Spring). Kafka producers/consumers stay on Confluent.Kafka; MassTransit dropped by user decision.
- 30: second dashboard instance on port 8081 behind the same Redis backplane; verify.sh now has 10 checks (backplane both directions, restart). Circuit reconnection is framework default and not scripted.
