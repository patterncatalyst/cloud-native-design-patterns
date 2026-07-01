# Example 04 — Data (Transactional Outbox + CDC)

Demonstrates the **transactional outbox pattern** with **Debezium CDC**: the
order-service writes an order row and an outbox row in a single database
transaction. Debezium tails the Postgres WAL and publishes outbox events to
Kafka — no dual writes, no lost events.

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) with
  [podman-compose](https://github.com/containers/podman-compose) or the
  Docker Compose plugin
- `curl` and `jq` for driving the API
- ~4 GB free memory (LGTM + Postgres + Kafka + Debezium Connect + app service)

See the [shared infrastructure README](../_infra/README.md) for ports,
credentials, and the container naming convention.

## What it shows

| Pattern | Where | What |
|---------|-------|------|
| Transactional outbox | `POST /orders` | Order + outbox row in one `BEGIN/COMMIT` — atomically consistent |
| CDC (Debezium) | Postgres WAL → Kafka | Debezium tails `wal_level=logical`, routes outbox rows to `order.placed` topic |
| No dual writes | by design | The service never writes to both DB and Kafka — Debezium handles the second hop |

## Architecture

```
 curl ──▶ order-service ──▶ Postgres (orders + outbox tables)
                                 │
                          WAL (logical)
                                 │
                          Debezium Connect
                                 │
                           Kafka (order.placed)
```

## Run it

```bash
podman compose up --build -d
```

Wait for all services including Kafka Connect:

```bash
podman compose ps
```

Register the Debezium connector:

```bash
./debezium/register-connector.sh
```

## Drive it

```bash
# Place an order (writes order + outbox in one transaction)
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"sku":"widget-a","quantity":3}' \
  localhost:8080/orders | jq .

# Check the outbox table
curl -s localhost:8080/outbox | jq .

# After ~5s, Debezium publishes to Kafka
podman exec cndp-kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --list

# Read the event
podman exec cndp-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic order.placed \
  --from-beginning --max-messages 1 --timeout-ms 10000
```

## Verify

```bash
./verify.sh
```

## Observe

Open Grafana at http://localhost:3000:

- **Tempo** — traces show the single transaction span
- **Loki** — order-service logs confirm outbox writes

## Ports

| Service | Port |
|---------|------|
| order-service | 8080 |
| Kafka Connect (Debezium) | 8083 |
| Grafana | 3000 |
| Postgres | 5432 |
| Kafka (host) | 9092 |
| Kafka UI | 8090 |
| OTLP HTTP | 4318 |
