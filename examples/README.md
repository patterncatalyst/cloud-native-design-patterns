# Runnable Examples

Each example demonstrates a cloud-native API design pattern from the tutorial
site. Every example ships with a `verify.sh` that asserts expected behavior
and an architecture diagram.

See [PREREQUISITES.md](PREREQUISITES.md) for setup instructions.

## Examples

| # | Pattern | Languages | Infra | Complexity |
|---|---------|-----------|-------|------------|
| 01 | [Cloud-Native Principles](01-cloud-native-principles/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | Postgres, LGTM | Simple |
| 02 | [Communications](02-communications/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | Postgres, Kafka, LGTM | Medium |
| 03 | [Composition](03-composition/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | Postgres, LGTM | Medium |
| 04 | [Data](04-data/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | Postgres, LGTM | Simple |
| 05 | [Event-Driven Architecture](05-event-driven/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | Postgres, Kafka, LGTM | Medium |
| 06 | [Stream Processing](06-stream-processing/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | Postgres, Kafka, LGTM | Medium |
| 09 | [API Registry](09-api-registry/) | Config only | Apicurio, LGTM | Simple |
| 11 | [Observability](11-observability/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | Postgres, Kafka, LGTM | Complex |
| 12 | [Security](12-security/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | LGTM | Simple |
| 16 | [WebSockets](16-websockets/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | Redis, LGTM | Medium |
| 17 | [Saga State & Compensation](17-sagas/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | Postgres, LGTM | Medium |
| 18 | [Errors & Problem Details](18-errors/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | LGTM | Simple |
| 19 | [DDD & Hexagonal Architecture](19-ddd-hexagonal/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | Postgres | Simple |
| 21 | [Graceful Shutdown](21-graceful-shutdown/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | Postgres, LGTM | Simple |
| 22 | [L7 Routing](22-l7-routing/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | Kafka, Envoy, LGTM | Complex |
| 24 | [Monolith to Microservices](24-monolith-to-microservices/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | Kafka, Redis, LGTM | Complex |
| 25 | [Caching](25-caching/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | Postgres, Redis, LGTM | Medium |
| 26 | [Failure Modes](26-failure-modes/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | LGTM | Simple |
| 27 | [Feature Flags](27-feature-flags/) | Spring Boot · Quarkus · .NET · Python · C++ · Go | flagd, LGTM | Simple |
| 28 | [Newman API Testing](28-newman/) | Postman collection | LGTM | Simple |
| 30 | [Blazor Server + SignalR](30-blazor-signalr/) | .NET only | Postgres, Redis, LGTM | Medium |

## Quick start

```bash
# Pick an example and a language
cd 05-event-driven/python
docker compose up -d --build --wait

# Wait for healthy
docker compose ps

# Run the verification suite
cd ..
bash verify.sh

# Observe in Grafana
xdg-open http://localhost:3000

# Tear down
cd python && docker compose down -v
```

## Shared infrastructure

The [`_infra/`](_infra/) directory contains composable infrastructure fragments:

| Fragment | Provides |
|----------|----------|
| `compose-lgtm.yaml` | Grafana, Loki, Tempo, Mimir (observability) |
| `compose-postgres.yaml` | PostgreSQL 16 |
| `compose-postgres-logical.yaml` | PostgreSQL with logical replication |
| `compose-kafka.yaml` | Kafka (KRaft mode, no ZooKeeper) |
| `compose-redis.yaml` | Redis 7 |
| `compose-debezium.yaml` | Debezium CDC connector |
| `compose-flagd.yaml` | flagd feature flag sidecar |

Each example's per-language `compose.yaml` uses `include:` to pull in only the
infrastructure it needs. All containers use the `cndp-` prefix.

## Conventions

- **Same API contract**: All language implementations expose identical REST/gRPC/GraphQL
  endpoints on the same ports — `verify.sh` works with any language.
- **Red Hat UBI base images**: Application containers use UBI10 (Spring Boot and Quarkus on JDK 25, Python 3.14, C++23 built with `gcc-toolset-15` on `ubi10/ubi` and run on `ubi-minimal`, and Go 1.27.2 as static binaries on `ubi-minimal`; the Go builder is the official `golang:1.27.2` image because the UBI 10 go-toolset ships only Go 1.26) or
  UBI9 (.NET); infrastructure services use upstream images.
- **Per-language README**: Each language directory has its own README with framework details,
  implementation notes, and local development instructions.
- **Six language stacks**: Spring Boot 4.1.1, Quarkus 3.40.1 LTS, .NET 10.0.12, Python 3.14 (FastAPI 0.143, faust-streaming 0.15.3), C++23
  (GCC 15, CMake 4.4.4, Conan 2.33.0; Drogon, grpc++, librdkafka, libpq, cppgraphqlgen, jwt-cpp, sml, sol2) and Go 1.27.2 (`net/http`, goka, gqlgen, golang-jwt, gopher-lua, franz-go, pgx) — all sharing the same API contract and `verify.sh`.
  C++ dependency pins live in each `conan.lock`; versions held below the newest upstream
  (protobuf 6.33.5 under grpc, abseil 20260107.1, taocpp-pegtl 3.2.8, lua 5.4.8, librdkafka 2.14.2 and
  opentelemetry-cpp 1.26.0 on ConanCenter) are listed in `_plans/modernization-plan.md` (S7).
- **Build files**: each service builds from a `Containerfile` (`Containerfile.<svc>` for
  .NET); compose references it with `build.dockerfile: Containerfile`.
- **Host ports**: Prometheus-compatible metrics (Mimir) are on host port 19090, because
  Cockpit holds 9090 on Fedora and RHEL. All other ports are unchanged.
