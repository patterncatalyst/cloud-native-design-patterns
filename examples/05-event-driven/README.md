# Example 05 — Event-Driven Architecture

Demonstrates **event-driven fan-out** with Kafka: the order-service publishes
`order.placed` events, and two independent consumer groups (shipping, notification)
each react to the same stream — with **idempotent deduplication** via database
UNIQUE constraints.

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) with
  [podman-compose](https://github.com/containers/podman-compose) or the
  Docker Compose plugin
- `curl` and `jq` for driving the API
- ~3 GB free memory (LGTM + Postgres + Kafka + 3 app services)

See the [shared infrastructure README](../_infra/README.md) for ports,
credentials, and the container naming convention.

## What it shows

| Pattern | Where | What |
|---------|-------|------|
| Event production | `POST /orders` | Order written to DB, `order.placed` published to Kafka |
| Fan-out (two consumer groups) | shipping + notification | Both consume the same topic independently |
| Commit-after-side-effect | consumers | DB insert happens first; Kafka offset committed only after success |
| Idempotent consumers | UNIQUE constraint | Duplicate events are silently skipped (no double shipment/notification) |

## Architecture

```
 curl ──▶ order-service ──▶ Postgres (orders)
               │
               ▼
       Kafka (order.placed)
          ┌────┴────┐
          ▼         ▼
  shipping-consumer  notification-consumer
  (shipping-group)   (notification-group)
          │                   │
          ▼                   ▼
  Postgres (shipments)  Postgres (notifications)
```

## Run it

```bash
podman compose up --build -d
```

Wait for all services:

```bash
podman compose ps
```

## Drive it

```bash
# Place an order
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"sku":"widget-a","quantity":5}' \
  localhost:8080/orders | jq .

# List orders
curl -s localhost:8080/orders | jq .

# Check that both consumers processed
podman exec cndp-postgres psql -U appuser -d appdb \
  -c "SELECT * FROM shipments;"
podman exec cndp-postgres psql -U appuser -d appdb \
  -c "SELECT * FROM notifications;"

# Verify consumer groups
podman exec cndp-kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --list
```

## Verify

```bash
./verify.sh
```

## Observe

Open Grafana at http://localhost:3000:

- **Tempo** — traces from order-service, shipping-consumer, notification-consumer
- **Loki** — search for `order.placed` to see the event flow across services

## Ports

| Service | Port |
|---------|------|
| order-service | 8080 |
| Grafana | 3000 |
| Postgres | 5432 |
| Kafka (host) | 9092 |
| Kafka UI | 8090 |
| OTLP HTTP | 4318 |
