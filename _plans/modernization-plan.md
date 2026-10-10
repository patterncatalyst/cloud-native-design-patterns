# Modernization plan — cloud-native-design-patterns

Approved by the user 2026-10-10. Relay: Opus plans, Sonnet executes, Opus validates.
Each step gets its own branch, a PR, green CI and a squash-merge before the next step starts.

## User decisions (2026-10-10)

1. Go → **1.27.2** (builder `docker.io/library/golang:1.27.2`, runtime `ubi10/ubi-minimal` pinned). Update the CLAUDE.md lock.
2. minikube: S9 adds a real minikube deployment of 05-event-driven plus its own appendix (docker driver, containerd, K8s v1.36.5, loopback `--ports` NodePorts).
3. Locked stacks: **rewrite the examples to use the locked libraries**, not just record deviations:
   - .NET: MassTransit (Kafka), Streamiz (stream processing)
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
| S1 | feature/docker-engine-runtime | 6 | in progress |
| S2 | chore/quarkus-3.40-lts | 1 | pending |
| S3 | chore/spring-boot-4.1 | 1 | pending |
| S4 | chore/dotnet-10-pins (+ MassTransit/Streamiz) | 3 | pending |
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
