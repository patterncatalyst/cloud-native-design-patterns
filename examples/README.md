# Runnable Examples

Each example demonstrates a cloud-native API design pattern from the tutorial
site. Every example ships with a `verify.sh` that asserts expected behavior
and an architecture diagram.

See [PREREQUISITES.md](PREREQUISITES.md) for setup instructions.

## Examples

| # | Pattern | Languages | Infra | Complexity |
|---|---------|-----------|-------|------------|
| 01 | [Cloud-Native Principles](01-cloud-native-principles/) | Python · Spring Boot · Quarkus · .NET | Postgres, LGTM | Simple |
| 02 | [Communications](02-communications/) | Python · Spring Boot · Quarkus · .NET | Postgres, Kafka, LGTM | Medium |
| 03 | [Composition](03-composition/) | Python · Spring Boot · Quarkus · .NET | Postgres, LGTM | Medium |
| 04 | [Data](04-data/) | Python · Spring Boot · Quarkus · .NET | Postgres, LGTM | Simple |
| 05 | [Event-Driven Architecture](05-event-driven/) | Python · Spring Boot · Quarkus · .NET | Postgres, Kafka, LGTM | Medium |
| 06 | [Stream Processing](06-stream-processing/) | Python · Spring Boot · Quarkus · .NET | Postgres, Kafka, LGTM | Medium |
| 09 | [API Registry](09-api-registry/) | Config only | Apicurio, LGTM | Simple |
| 11 | [Observability](11-observability/) | Python · Spring Boot · Quarkus · .NET | Postgres, Kafka, LGTM | Complex |
| 12 | [Security](12-security/) | Python · Spring Boot · Quarkus · .NET | LGTM | Simple |
| 16 | [WebSockets](16-websockets/) | Python · Spring Boot · Quarkus · .NET | Redis, LGTM | Medium |
| 17 | [Saga State & Compensation](17-sagas/) | Python · Spring Boot · Quarkus · .NET | Postgres, LGTM | Medium |
| 18 | [Errors & Problem Details](18-errors/) | Python · Spring Boot · Quarkus · .NET | LGTM | Simple |
| 19 | [DDD & Hexagonal Architecture](19-ddd-hexagonal/) | Python · Spring Boot · Quarkus · .NET | Postgres | Simple |
| 21 | [Graceful Shutdown](21-graceful-shutdown/) | Python · Spring Boot · Quarkus · .NET | Postgres, LGTM | Simple |
| 22 | [L7 Routing](22-l7-routing/) | Python · Spring Boot · Quarkus · .NET | Kafka, Envoy, LGTM | Complex |
| 24 | [Monolith to Microservices](24-monolith-to-microservices/) | Python · Spring Boot · Quarkus · .NET | Kafka, Redis, LGTM | Complex |
| 25 | [Caching](25-caching/) | Python · Spring Boot · Quarkus · .NET | Postgres, Redis, LGTM | Medium |
| 26 | [Failure Modes](26-failure-modes/) | Python · Spring Boot · Quarkus · .NET | LGTM | Simple |
| 27 | [Feature Flags](27-feature-flags/) | Python · Spring Boot · Quarkus · .NET | flagd, LGTM | Simple |
| 28 | [Newman API Testing](28-newman/) | Postman collection | LGTM | Simple |
| 30 | [Blazor Server + SignalR](30-blazor-signalr/) | .NET only | Postgres, Redis, LGTM | Medium |

## Quick start

```bash
# Pick an example and a language
cd 05-event-driven/python
podman compose up --build -d

# Wait for healthy
podman compose ps

# Run the verification suite
cd ..
bash verify.sh

# Observe in Grafana
open http://localhost:3000

# Tear down
cd python && podman compose down -v
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
- **Red Hat UBI base images**: Application containers use UBI10 (Quarkus/JDK 25) or
  UBI9 (Python, .NET, Spring Boot); infrastructure services use upstream images.
- **Per-language README**: Each language directory has its own README with framework details,
  implementation notes, and local development instructions.
- **Four JVM/.NET/Python stacks**: Python (FastAPI), Spring Boot, Quarkus 3.33 LTS, and
  .NET 10 — all sharing the same API contract and `verify.sh`.
