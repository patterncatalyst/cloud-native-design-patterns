# Shared Infrastructure

Composable infrastructure services for the runnable examples. Each example
`include:`s the pieces it needs rather than duplicating service definitions.

## Compose files

| File | Services | Use when |
|------|----------|----------|
| `compose-lgtm.yaml` | Grafana LGTM (Loki, Grafana, Tempo, Mimir) + OTel Collector | Every example (observability) |
| `compose-postgres.yaml` | Postgres 16 | Example needs relational storage |
| `compose-postgres-logical.yaml` | Postgres 16 with `wal_level=logical` | Example uses CDC / Debezium |
| `compose-kafka.yaml` | Kafka 3.8 (KRaft) + Kafka UI | Example uses event streaming |
| `compose-redis.yaml` | Redis 7 | Example uses caching or pub/sub |
| `compose-debezium.yaml` | Debezium / Kafka Connect | Example uses change data capture |
| `compose-flagd.yaml` | flagd (OpenFeature) | Example uses feature flags |

## Usage

An example's `compose.yaml` includes the shared pieces and adds its own services:

```yaml
include:
  - path: ../_infra/compose-lgtm.yaml
  - path: ../_infra/compose-postgres.yaml
  - path: ../_infra/compose-kafka.yaml

services:
  order-service:
    build: .
    depends_on:
      lgtm:
        condition: service_healthy
      postgres:
        condition: service_healthy
      kafka:
        condition: service_healthy
    # ...
```

## Ports

| Service | Host port | Container port |
|---------|-----------|----------------|
| Grafana UI | 3000 | 3000 |
| OTLP HTTP | 4318 | 4318 |
| Prometheus/Mimir | 9090 | 9090 |
| Loki | 3100 | 3100 |
| Tempo | 3200 | 3200 |
| Postgres | 5432 | 5432 |
| Kafka (host) | 9092 | 9092 |
| Kafka (compose) | 9094 | 9094 |
| Kafka UI | 8090 | 8080 |
| Redis | 6379 | 6379 |
| Kafka Connect | 8083 | 8083 |
| flagd (gRPC) | 8013 | 8013 |

## Credentials

| Service | User | Password |
|---------|------|----------|
| Postgres | appuser | apppass |
| Grafana | (anonymous admin) | (none) |
| Redis | (none) | (none) |

## Container naming convention

All containers use the `cndp-` prefix to avoid collisions with other projects
on the same machine:

| Compose service | Container name |
|----------------|----------------|
| lgtm | cndp-lgtm |
| postgres | cndp-postgres |
| kafka | cndp-kafka |
| kafka-ui | cndp-kafka-ui |
| redis | cndp-redis |
| kafka-connect | cndp-kafka-connect |
| flagd | cndp-flagd |
| (app services) | cndp-{service-name} |

The shared network is named `cndp`. Service names (used for DNS inside compose)
remain unprefixed — only `container_name:` gets the prefix.

## Application base images

Application service containers use **Red Hat UBI** (Universal Base Image):
- Python: `registry.access.redhat.com/ubi9/python-312`
- Go: multi-stage with `registry.access.redhat.com/ubi9/ubi-minimal` as runtime
- Java: `registry.access.redhat.com/ubi9/openjdk-21`

Infrastructure services (Postgres, Kafka, Redis, etc.) keep their upstream images.
