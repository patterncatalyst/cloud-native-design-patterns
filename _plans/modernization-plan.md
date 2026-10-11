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
| S4 | chore/dotnet-10-pins | 3 | done (19/19 .NET PASS after the Opus review; closes #33) |
| S5 | chore/python-3.14 | 5 | done (19/19 Python + 28 PASS after the Opus review) |
| S6 | chore/go-toolchain | 2+4 | done (18/18 Go + 06 in all six languages PASS after the Opus review; closes #34) |
| S7 | chore/cpp-toolchain-ubi10 | 2+4 | done (111/111 PASS after two Opus repair rounds; closes #35) |
| S8 | chore/infra-images | 2 | done (111/111 PASS; two Opus repair rounds; PR #66; lgtm-skills #45 + r5.x; main run green, Actions cache 2.4 GB) |
| S9 | docs/minikube-docker-driver (+ 05 on minikube) | 7 | executed (awaiting validation) |
| S10 | feature/openshift-local-appendix | 8 | pending |
| S11 | docs/professional-voice | 9 | pending |
| S12 | docs/deck-refresh | 10 (expanded 2026-10-11) | pending |

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
| Apicurio | docker.io/apicurio/apicurio-registry:3.3.3 |
| flagd | ghcr.io/open-feature/flagd:v0.17.0 |
| LGTM | grafana/otel-lgtm:0.36.0 |
| Envoy | envoyproxy/envoy:v1.39.3 |
| kafka-ui | removed (use kcat) |
| Test tools | newman 6.2.3, htmlextra 1.23.1, hey v0.1.5, ghz v0.121.0, conftest 0.71.1 |
| minikube | v1.39.0, Kubernetes v1.36.5, profile `cndp-k8s` (NodePorts 30080 and 30300 on 127.0.0.1) |
| kubectl | v1.36.5 (kustomize v5.8.1) |
| Helm | v4.3.0 |
| kubeconform | v0.8.0, CRDs-catalog commit 63669a570e231d4f1f8396d229a1de512bcf0a34 |
| Operators | Strimzi 1.2.0 (chart `oci://quay.io/strimzi-helm/strimzi-kafka-operator` 1.2.0; Kafka image `quay.io/strimzi/kafka:1.2.0-kafka-4.3.1`), CNPG v1.30.1, KEDA v2.21.0, Istio 1.31.1 |
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
- S10: Appendix S with evidence for 5 languages; scrub clean; CRC stopped and clean.
- S11: voice scan reports zero ban-tier hits and is enforced in CI.
- S12 (scope expanded by the user 2026-10-11): review every presentation in `lgtm-presentation/` (the six Designing-Cloud-Native-APIs decks, K8s-Environment-Access-Policies, Network-Policy-Process-Advisory, and their .md/.docx companions) for:
  - version changes (every version on a slide matches the S2–S8 pins);
  - stack changes (Docker Engine, not the old container engine; locked libraries such as Streamiz, faust-streaming, goka, librdkafka C++, C++23; kafka-ui removed);
  - code changes (every code snippet on a slide matches the current example code and APIs, e.g. Spring Boot 4 / Jackson 3, Quarkus 3.40, .NET 10, Python 3.14, Go 1.27, C++23);
  - wording and professionalism (lgtm-professional-voice: zero ban-tier hits);
  - 0 references to the old container engine; minikube and OpenShift Local slides; every deck rendered and inspected.

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

### S4 .NET 10 (2026-10-10)

- 32 csproj on net10.0 (SDK 10.0.112, runtime 10.0.12 LTS); every PackageReference exact and newest stable; all licenses open source (checked on nuget.org). Example 30's preview SignalR packages replaced with 10.0.12.
- Images `ubi9/dotnet-100:9.8-1791421718` and `ubi9/dotnet-100-aspnet:9.8-1791363520` (no ubi10 .NET image exists), non-root 1001, NuGet cache mount.
- Lock changed (user decision): Kafka stays on Confluent.Kafka 2.16.0; MassTransit dropped (it hides the Kafka semantics the examples teach, and v9 is commercial). 06 stream processor rewritten on Streamiz.Kafka.Net 1.8.2 (same contract as Kafka Streams).
- Example 30: second dashboard instance on the Redis backplane; verify.sh grows from 5 to 10 checks (cross-instance delivery both ways, restart asserted).
- Chapter .NET codetabs (05, 06, 18, 22) compile against the pinned packages.
- Live: **19/19 .NET targets PASS** on the final tree after the Opus review.

### S9 minikube (2026-10-11)

Fedora 44, Docker Engine 29.8.2, minikube v1.39.0, kubectl v1.36.5 (kustomize v5.8.1), **Helm v4.3.0**, profile `cndp-k8s` (docker driver, containerd 2.3.4, Kubernetes v1.36.5, 8 GB, 4 CPUs, 40 GB), NodePorts 30080 and 30300 published on 127.0.0.1 only (`docker port cndp-k8s`). Evidence: `/tmp/claude-1000/-home-rsedor-Dev/0dea024d-0bf0-4ae5-bddd-7dec0cf60b22/scratchpad/s9/` (`00-prechecks.txt`, `01-setup-profile.log`, `matrix/` with `results.tsv`, per-language logs and evidence, `docker-path/`, `10-static-checks.txt`, `11-final-state.txt`).

Pins re-verified at the start: Strimzi chart and operator 1.2.0 (Kafka image `quay.io/strimzi/kafka:1.2.0-kafka-4.3.1`, Kafka 4.3.1, Kafka CR `kafka.strimzi.io/v1`), postgres 18.6-alpine, otel-lgtm 0.36.0, kubeconform v0.8.0, actionlint 1.7.12, shellcheck 0.11.0, CRDs-catalog commit 63669a5. Kubernetes 1.37.1 exists upstream and minikube v1.39.0 lists 1.37.0 as its newest; v1.36.5 stays because the host kubectl and the other profiles are 1.36.5 and the plan was approved with it.

**Live run: 6/6 languages `==> Results: 10 passed, 0 failed`** with `RUNTIME=kubernetes` (`k8s/verify-matrix.sh`, fresh namespace per language, images built with docker and loaded with `minikube image load`, all pods 0 restarts, Grafana `/api/health` `database: ok` on 127.0.0.1:30300):

| Language | Result | Time |
|---|---|---|
| spring-boot | 10 passed, 0 failed | 361 s |
| quarkus | 10 passed, 0 failed | 135 s |
| dotnet | 10 passed, 0 failed | 134 s |
| python | 10 passed, 0 failed | 116 s |
| cpp | 10 passed, 0 failed | 103 s |
| go | 10 passed, 0 failed | 104 s |

An earlier single-language Spring Boot run (205 s) also passed first time. Docker-path regression: `scripts/verify-matrix.sh 05-event-driven/go` PASS 10/10 (57 s). A hand cross-check (scale shipping-consumer to 0, place an order, 0 shipments; scale to 1, 1 shipment) passed.

End state: `teardown.sh --operator` removed the `cndp-05` namespace, the Strimzi release, all Strimzi CRDs and the `strimzi` namespace; `minikube stop -p cndp-k8s` left the profile Stopped (not deleted); every other profile unchanged (helm4dev still broken, left alone); kubectl current-context unset before and after; no containers running.

Repair round 1 (validator findings):

- Current-context: the earlier "never changed" claim was wrong for restarts. When a stopped docker-driver profile restarts and its API-server host port changes, minikube v1.39.0 sets current-context to the profile even with `--keep-context` (reproduced: a raw `minikube start -p cndp-k8s --keep-context` after a stop left `cndp-k8s` as current-context). `setup-profile.sh` now records the context before any start, restores it (unset or `use-context`) and fails if it differs. Tested on a copy of the kubeconfig: restart from unset, restart from a throwaway context, already-running no-op; then on the real kubeconfig, which stayed unset. The create path was not re-run (it needs a new profile name or a delete, both out of bounds).
- `setup-profile.sh` also runs the host-port check whenever the profile is not running and compares Driver, ContainerRuntime and KubernetesVersion with docker, containerd and v1.36.5 (tested: `KUBERNETES_VERSION=v1.35.0` fails with a clear message).
- `teardown.sh --operator` is idempotent (`grep` guarded under `pipefail`, `--ignore-not-found` on the CRD delete); two runs in a row both exit 0.
- Quarkus OTLP: Quarkus defaults to gRPC but 4318 is OTLP/HTTP, so exports failed with "First received frame was not SETTINGS" and Tempo listed no services. `quarkus.otel.exporter.otlp.protocol=http/protobuf` added to the ten `application.properties` of Examples 02, 03, 05 and 06 that export to 4318 without it (01, 04 and 18 already had it; 11 and 17 use 4317). Compose regression, one at a time: 02/quarkus 10/10, 03/quarkus 8/8, 05/quarkus 10/10, 06/quarkus 11/11, all PASS.
- Traces per language on k8s, from Tempo through the lgtm pod after each `verify.sh` (a non-counted step in `k8s/verify-matrix.sh`; `verify.sh` is still 10 checks): Spring Boot, Quarkus and .NET report order-service, shipping-consumer and notification-consumer; Python reports order, shipping and notification. The .NET exporter defaulted to gRPC against 4318 and the consumers never registered their `ActivitySource`; both fixed (HTTP protobuf with `/v1/traces`, `AddSource`), compose 05/dotnet 10/10. Go and C++ report no services: Example 05 carries no tracing code in those languages (compose too), so Appendix R says so instead of claiming six.
- All six languages 10/10 on k8s in the repair run (spring-boot 185 s, quarkus 382 s, python 145 s, cpp 131 s, go 133 s; dotnet re-run after the fix 173 s). A stale BuildKit cache mount made one .NET build fail with NETSDK1064; `DOCKER_BUILD_OPTS=--no-cache` on `build-images.sh` is the documented workaround.
- `ci_changed_projects.py`: a deleted or missing file under `k8s/` still selects the directory while it exists (tested with `--files`: existing manifest, deleted `base/x.yaml`, `.sh`, README, `db/init`).
- shellcheck `source-path=SCRIPTDIR` added; clean on the k8s scripts. `verify-matrix.sh` no longer prints the language twice. `verify.sh`: a failed duplicate-event send no longer aborts and cannot pass the two idempotency checks vacuously. The .NET overlay sets `SERVICE_VERSION` on the order-service only, as compose does.
- End state: `teardown.sh --operator` twice (0, 0), `minikube stop -p cndp-k8s`, current-context unset, no containers running.

Static checks: `validate_site.py` 0 errors, Jekyll build OK (ruby:3.3 container, because the host has no ruby-devel for native gems), actionlint 1.7.12 clean, shellcheck clean on the k8s scripts and `verify.sh`, kubeconform v0.8.0 `-strict` against 1.36.5: infra 9/9 valid, six overlays 4/4 valid each, 0 invalid; selector cases: `k8s/base/*.yaml` selects only `k8s`, `k8s/*.sh` selects only `scripts`, `db/init/*.sql` selects `k8s`, `k8s/README.md` selects nothing, `_infra` selects everything.

Deviations from the plan: added `k8s/lib.sh` (shared settings for the five scripts); two plan lines naming the old container engine were reworded because `validate_site.py` scans `_plans/`; `kraftMetadata` and `metadataVersion` are left to the Strimzi defaults (4.3-IV0).

### S7 C++23 (2026-10-10)

- 31 C++ projects on C++23 (`CMAKE_CXX_STANDARD 23`, required, no extensions), CMake policy 3.31, `-Wall -Wextra` clean on GCC 15.2. Builder `ubi10/ubi:10.2-1791444044` with `gcc-toolset-15`; CMake 4.4.4 and Ninja 1.13.2 from the upstream release binaries (sha256-verified; UBI ships cmake 3.31 and ninja 1.11); Conan 2.33.0 in a pinned venv. The Conan home is a BuildKit cache mount, packages are deployed next to the sources (`--deployer=full_deploy`) so later layers and the GHA layer cache do not need the mount. Runtime `ubi10/ubi-minimal:10.2-1791444377`, UID 1001 group 0, libstdc++/libgcc linked statically (gcc-toolset-15's libstdc++ is newer than the one in ubi-minimal; proven by running the binaries on ubi-minimal).
- Versions (ConanCenter newest): drogon 1.9.13, grpc 1.84.0, protobuf 6.33.5, librdkafka 2.14.2, libpq 17.11, redis-plus-plus 1.3.15, jwt-cpp 0.7.2, sml 1.2.0, sol2 3.5.0, lua 5.4.8, opentelemetry-cpp 1.26.0, spdlog 1.17.0, nlohmann_json 3.12.0, cppgraphqlgen 4.5.9 with taocpp-pegtl 3.2.8 and boost 1.91.0 (schemagen stage only). cppgraphqlgen is not on ConanCenter: each of 02 and 03 carries a local recipe (`conan-recipes/cppgraphqlgen`) and the committed schemagen output.
- Transitive refresh: every `conan.lock` is regenerated with `conan lock create --update` (no lockfile in, GCC 15, C++23, Release, static), so transitive packages take the newest ConanCenter version in range: openssl 3.6.3 to 3.6.5, libcurl 8.21.0 to 8.22.0 (26 also pins it directly), cmake tool 4.4.0 to 4.4.4. Overrides in each `conanfile.py` (`override=True`, build and ctest proven on all 31 images): fmt 12.1.0 to 12.2.0 (spdlog), lz4 1.9.4 to 1.10.0 (librdkafka, libpq), util-linux-libuuid 2.39.2 to 2.41.2 and jsoncpp 1.9.5 to 1.9.8 (drogon). None had to be dropped. The schemagen stage of 02 and 03 has its own `schemagen.lock` (boost 1.90.0 to 1.91.0; boost 1.91 builds boost_regex whatever `without_regex` says and its recipe rejects an unused built library, so regex is no longer disabled there).
- Corrections to earlier claims: openssl is not capped at 3.6.3 (3.6.5 is current in the 3.6 line; only the 4.x line is outside drogon's `<4` range), libcurl is 8.22.0 (not 8.21.0), and jsoncpp is 1.9.8 everywhere (the locks held 1.9.5 transitively until the override).
- Held versions (legitimate, with the reason): abseil 20260107.1 (protobuf 6.33.5 caps it), protobuf 6.33.5 (grpc 1.84.0 requires protobuf below 7; 7.36.2 exists), opentelemetry-proto 1.7.0 (required as a tool by opentelemetry-cpp 1.26.0), taocpp-pegtl 3.2.8 (cppgraphqlgen 4.5.9 needs the 3.x API; 4.x is newer), lua 5.4.8 (sol2's recipe pins 5.4.x; 5.5.0 is newer), openssl 3.6.x (drogon and trantor accept `<4`; 4.0.3 is newer), librdkafka 2.14.2 (upstream 2.16.0) and opentelemetry-cpp 1.26.0 (upstream 1.29.0), both ConanCenter behind upstream.
- Build tooling: flex and bison (libpq build tools) ran makeinfo; the fake `makeinfo` binary is gone, replaced by scoped `-c:a 'flex/*:tools.gnu:extra_configure_args=["MAKEINFO=true"]'` (and bison) in the 14 projects whose lock contains flex. The Conan cache mount has an explicit `id=cndp-conan2`.
- CI (cpp job): the Conan cache mount does not persist across jobs, and a cold build of the largest projects takes about 33 minutes on 4 CPUs (55-75 minutes estimated on a hosted runner). The job restores a `conan-cache` directory with actions/cache (key: runner OS, UBI 10.2, GCC 15, Conan 2.33.0, `hashFiles` of the project's `conan.lock`; restore-key on the toolchain) and injects it into the `cndp-conan2` mount with buildkit-cache-dance v3.4.0 (`cache-map`, extraction skipped on an exact hit). Image layers use `type=gha,mode=min` (`mode=max` across 31 scopes would exceed the 10 GB quota); the timeout is 120 minutes. Open risk: 31 projects can still exceed 10 GB of Conan cache and evict each other, which the toolchain restore-key softens.
- Repair rounds (after the first build): Lua sandbox swallowing limit errors (22); hand-escaped or concatenated SQL and an unprotected shared connection (25, 03, 04); Kafka delivery reports awaited before replying 201, with 503 on failure (05, 06, 11, 24); notification insert retry and SQLSTATE duplicate detection (11); OTLP exporters in the 11 inventory service and the W3C propagator in the Go inventory service so the inventory span lands in the order's trace (11); range-checked decimal sums and non-zero exit on delivery failure in the stream processor (06); every libpq result released and checked, unknown saga status rejected (17); the alg=none test token differing from a valid one only by algorithm (12). First live run: 18/18 C++ PASS.
- Licenses: all open source. spdlog is MIT and librdkafka BSD-2-Clause (confirmed from their LICENSE files; GitHub shows NOASSERTION); libpq is the PostgreSQL license, sml BSL-1.0, grpc/opentelemetry-cpp/redis-plus-plus Apache-2.0, the rest MIT or BSD.
- Locked stack (user decisions): Kafka on librdkafka's C++ API (modern-cpp-kafka is archived); C++23. Deviations fixed: 02/03 GraphQL on cppgraphqlgen (03 keeps the request-scoped stock batch), 12 valet keys as HS256 JWTs with jwt-cpp (algorithm pinned), 17 saga on boost::sml, 22 router on sol2 + sandboxed Lua, 06 stream processor as an explicit tumbling-window aggregation on rdkafka++ (exact fixed-point cents, offsets committed after the output is delivery-reported), 01 exports OpenTelemetry traces (OTLP/HTTP) with trace_id in spdlog lines, 11 on opentelemetry-cpp. 01 already used libpq; every Postgres user links the Conan libpq.
- Fixed on the way: dangling `c_str()` parameters in 05/06 order services, SQL string concatenation in 02, an unprotected shared PGconn.
- Chapter C++ tabs (05, 07, 11, 15, 17, 18, 22) match the libraries now used; the r76 outbox tab uses libpq.

### S6 Go 1.27.2 (2026-10-10)

- 31 Go modules on `go 1.27.2` (no `toolchain` line), versions unified across modules: grpc 1.84.0, protobuf 1.36.12, OTel 1.47.0 (otelhttp/otelgrpc 0.72.0), pgx 5.11.0, franz-go 1.22.1, go-redis 9.23.0, coder/websocket 1.8.15, gobreaker v2.4.0, OpenFeature go-sdk 1.19.0 + flagd provider 0.7.1. All OSS (MIT, BSD, ISC, Apache-2.0).
- Containerfiles: builder `docker.io/library/golang:1.27.2`, `CGO_ENABLED=0 -trimpath`, BuildKit cache mounts for `/go/pkg/mod` and `/root/.cache/go-build`, runtime `ubi10/ubi-minimal:10.2-1791444377`, USER 1001, group-0 files. HOLD: the UBI 10 go-toolset ships only Go 1.26.x, so the Go builder is the official image.
- Locked stack: 06 stream processor on goka 1.1.17 (sarama 1.61.1, `sarama.V4_3_1_0`); 02/03 GraphQL on gqlgen 0.17.95 (schema-first, generated code committed); 12 valet key as HS256 JWT via golang-jwt 5.3.1; 22 router on gopher-lua 1.1.2 (embedded `routing.lua`, sandboxed libs); 26 retry on cenkalti/backoff v7.0.1; every server shuts down with `signal.NotifyContext`.
- goka processor tested on throwaway private-network brokers: apache/kafka:3.8.0 and apache/kafka:4.3.1 both processed, emitted, rounded HALF_UP, skipped bad records and drained lag after a pause, so S8 is low risk for Go.
- 01 Go now exports OTLP traces (otelhttp server spans, trace_id/span_id in slog JSON).
- Go build outputs are now gitignored (22 module-root binaries).
- Chapter Go tabs for 03, 06 and 26 match the libraries now used.

- S7 live: the full matrix was rerun after both repair rounds: **111/111 PASS** (111/111 after the S7 repairs). The stricter 11 check (inventory span inside the order's own trace) found and fixed missing trace propagation in Go (no global propagator) and Python (grpc.aio channel not instrumented).

Carried forward:
- S7: example 01 C++ still sets OTEL_* in compose but exports nothing.

### S5 Python 3.14 (2026-10-10)

- 32 Python services (+ 28's) on `ubi10/python-314-minimal:10.2-1791464217` (Python 3.14.8), non-root 1001, working pip cache mount (the base image's PIP_NO_CACHE_DIR had disabled it).
- Every requirements.txt is a full `==` freeze from a python3.14 venv; direct deps newest stable and open source (fastapi 0.143.0, pydantic 2.14.0, aiokafka 0.14.0, grpcio 1.84.0, strawberry 0.333.0, redis 8.1.0, OTel 1.45.1 / contrib 0.66b1 — contrib only publishes b versions, documented per file). The S1 graphql-core pin is gone.
- FastAPI `on_event` replaced by lifespan; chapter 25 and 04 snippets fixed.
- Locked stack: 06 stream processor rewritten on faust-streaming 0.15.3 (memory store; same contract incl. HALF_UP rounding). Tested by the validator against apache/kafka:4.3.1: works (aiokafka 0.14 negotiates API versions), so S8 is low risk for Faust.
- 01 Python now really auto-instruments with opentelemetry-instrument; 03/04 wire asyncpg instrumentation.
- Live: **19/19 PASS** (18 Python + 28) on the final tree after the Opus review.

Carried forward:

### S4 .NET 10.0.12 (2026-10-10)

- 32 .NET projects (including example 30) on net10.0 with every PackageReference pinned exactly: OpenTelemetry 1.19.1 (AspNetCore instrumentation 1.19.0), Npgsql 10.0.3, Confluent.Kafka 2.16.0, Streamiz.Kafka.Net 1.8.2, Grpc.AspNetCore/Grpc.Net.Client/Grpc.Tools 2.84.0, Google.Protobuf 3.36.2, StackExchange.Redis 3.4.0, HotChocolate 16.6.8, OpenFeature 2.14.1, OpenFeature.Contrib.Providers.Flagd 0.5.0, SignalR 10.0.12 (the preview.5 packages are gone).
- Images `ubi9/dotnet-100:9.8-1791421718` and `ubi9/dotnet-100-aspnet:9.8-1791363520`, non-root UID 1001, group-0 ownership, BuildKit NuGet cache mount. HOLD: Red Hat publishes no ubi10 .NET image.
- Locked stack: 06 stream processor rewritten on Streamiz (same contract as Quarkus/Spring). Kafka producers/consumers stay on Confluent.Kafka; MassTransit dropped by user decision.
- 30: second dashboard instance on port 8081 behind the same Redis backplane; verify.sh now has 10 checks (backplane both directions, restart). Circuit reconnection is framework default and not scripted.

### S8 infra images (2026-10-10)

Docker 29.8.2, compose 5.5.1, Fedora 44. Pins re-verified with skopeo list-tags: all targets were the newest stable (Kafka 4.3.1, Postgres 18.6-alpine, Redis 8.10.2-alpine, Debezium 3.7.0.Final on quay.io, Apicurio 3.3.3, flagd v0.17.0, otel-lgtm 0.36.0, Envoy v1.39.3); test tools newman 6.2.3, htmlextra 1.23.1, hey v0.1.5, ghz v0.121.0, conftest 0.71.1 were also still the newest.

**111/111 targets PASS** (`OUT=.../matrix-s8 scripts/verify-matrix.sh`). `grep ':latest|-latest|kafka-ui'` over examples, _docs and _example_pages has no hits except the deliberate `sketchy:latest` policy fixture.

Breaking changes handled:

| Change | Fix |
|---|---|
| Debezium 3.7 was OOM-killed (exit 137) at 1 GB: it scans every bundled connector | `compose-debezium.yaml`: `mem_limit: 2g`, `HEAP_OPTS=-Xms256M -Xmx1G` |
| Apicurio 3.3 serves `/health/ready` on the management port 9000, not 8080 | `compose-apicurio.yaml` healthcheck on 9000, host port 19000 published; 09 verify.sh and README updated |
| Apicurio 3.3 answers 400 (was 409) to an incompatible schema | 09 verify.sh, README, `_docs/09-api-registry.md`, appendix B, registry-gate and architecture diagrams |
| Tempo 3 `/api/search` returns no traces without a time window and indexes later | 11 verify.sh passes start/end and retries up to 60 s; quarkus README example |
| otel-lgtm 0.36 ships `grafana-datasources.yaml`; our file beside it was ignored | `compose-lgtm.yaml` mounts ours over that name (Prometheus default, localhost URLs kept) |
| Postgres 18 PGDATA moved | volume mounted at `/var/lib/postgresql` |
| kafka-ui removed | compose overrides, port tables and the 04 README now use kcat or `kafka-console-consumer.sh` |

No change needed: Kafka 4 KRaft env vars and the `nc` healthcheck, the Debezium connector JSON (`topic.prefix`, `table.include.list`, `pgoutput`), Envoy 1.39 `envoy.yaml`, flagd flag file and start args, the `/apis/registry/v3` paths, Prometheus on 19090, Redis commands. Redis 8 is RSALv2/SSPLv1/AGPLv3; the AGPLv3 option is free and needs no key.

CI cache (12.4 GB, 170 entries before): Conan 8.6 GB in 20 entries (350-700 MB each, one per conan.lock, written by PRs too), Go 2.3 GB in 20 entries, BuildKit layers 0.2 GB. Now every run restores and only main writes. Maven and Go are one shared entry each, written by main-only `warm-maven` / `warm-go` jobs that resolve all projects (62 poms, 31 go.mod) and delete the superseded entry; Conan stays one entry per distinct conan.lock (22), pruned on main (measured on 25-caching/cpp: 1.6 GB to 163 MB, the following `conan install` all cache hits) and with the builder stage forced to run on a miss. Steady state on main: typical 22 x 82 MB + Maven 1.0 + Go 0.6 + layers 0.25 + Pages 0.05 = about 3.7 GB, bound 4.9 GB, peak about 8 GB when a Conan key bump or bulk lock change leaves superseded per-lock entries and layer blobs age out after 7 days unused. Measured: unpruned Conan entries (API), BuildKit layers (27 blobs = 200 MB); partly measured: prune ratio (one project); estimated: Maven <=1.0 GB, Go <=0.6 GB, Pages. Check the first real Maven/Go saved entry sizes after merge. `cache-cleanup.yml` deletes a closed same-repo PR's caches. New key prefixes (`Linux-conan2-`, `maven-Linux-`, `go-Linux-`) differ from the old ones (`conan-Linux-`, `setup-java-Linux-x64-maven-`, `setup-go-Linux-x64-ubuntu24-go-`), so delete the old entries by prefix (command in CLAUDE.md, "CI cache budget"), safe at any time; never `gh cache delete --all`.

#### Repair round 1 (validator findings)

- Conan miss on main (HIGH): reproduced with a fresh buildx builder and a local layer cache standing in for `type=gha`: with `cache-from` alone the `conan install` RUN is CACHED and the `cndp-conan2` mount stays empty. With `--no-cache-filter builder` the RUN executes and the mount is populated (1.6 GB, 13 built packages after pruning to 163 MB). `examples.yml` now passes `no-cache-filters: builder,schemagen` on a main miss (all 31 Containerfiles have a `builder` stage; an unknown stage name is accepted), and the prune RUN fails when no `p/b/<id>/p` package is left (negative test on an empty mount fails, populated mount passes). The key-shape comment now reads `<OS>-conan2-ubi10.2-gcc15-conan2.33.0-<lock hash>`.
- Cache size (HIGH): the estimate had ignored per-pom Maven keys (62 projects) and per-go.sum Go keys (31). Maven and Go are now one shared key each, restored by every leg and written only by the main-only `warm-maven` / `warm-go` jobs, which resolve every project and delete the superseded entry (a build leg cannot be the writer: it only downloads its own dependencies). Go caches the module cache only. Conan stays per-lock (22 x <=135 MB). Arithmetic: bound 22 x 135 = 3.0 GB + 1.0 + 0.6 + 0.25 + 0.05 = 4.9 GB; typical about 3.7 GB; peak about 8 GB (see above). Maven retry args (`aether.transport.http.retryHandler.*`) are set on the warm job and the build leg.
- Cleanup advice (MEDIUM): `gh cache delete --all` replaced by deleting the old prefixes (`conan-Linux-`, `setup-java-Linux-x64-maven-`, `setup-go-Linux-x64-ubuntu24-go-`), safe at any time because the new keys use other prefixes (CLAUDE.md).
- 09 verify.sh: the breaking-schema check needs HTTP 400 and `RuleViolationException` in the body; the version count uses `jq -e '.count == 2'`. Check count unchanged (8). 11 verify.sh (shared by all six variants, service name `order-service` in each): the Tempo search filters `service.name=order-service`.
- `cache-cleanup.yml` skips fork pull requests and tolerates a failed delete. `_infra/README.md` lists compose-apicurio.yaml, ports 8081 and 19000 and `cndp-apicurio`. kcat (`sudo dnf install -y kcat`, Fedora package `kcat` 1.7.1) is in both prerequisites files. The ghz install creates `~/.local/bin` and verifies the published `.sha256`; the Newman appendix installs with `--prefix ~/.local`; conftest 0.71.1 is in the test-tools table.
- buildkit-cache-dance `utility-image` pinned to `ghcr.io/containerd/busybox:1.36@sha256:7b3c...2627c` (1.36 is the newest tag on ghcr, multi-arch; the action default is `:latest`).
- Verification: actionlint 1.7.12 clean on all workflows; `validate_site.py` 0 errors; live `verify-matrix.sh`: 09 (8 checks), 11 spring-boot, quarkus, dotnet, python, cpp, go (10 checks each) and 25-caching/cpp (26) all PASS.

#### Repair round 2

- Eviction guard: the "Delete the superseded" steps first confirm the new key exists (`gh cache list --key` is a prefix match, `--limit 1000`) and keep the old entries with a warning otherwise, since `actions/cache/save` only warns on failure.
- `warm-maven` and `warm-go` have job-level `concurrency` (`warm-maven-<ref>` / `warm-go-<ref>`, no cancel).
- Both start with an exact-key `lookup-only` probe; on a hit every later step is skipped. On a miss: restore with restore-keys, warm, save, evict.
- `warm-go` uses `go-version-file` (examples/01-cloud-native-principles/go/go.mod, go 1.27.2) instead of `stable`.
- Stale `warm-caches` references renamed to `warm-maven` / `warm-go` in examples.yml and CLAUDE.md.
- Estimate relabelled measured / partly measured / estimated; typical 3.7 GB, bound 4.9 GB, peak about 8 GB; check real Maven/Go entry sizes after merge.
- Verification: actionlint clean on all workflows; `validate_site.py` 0 errors.
