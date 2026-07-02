# Example 06 — Stream Processing

Demonstrates **stateful windowed aggregation**: the order-service publishes
`order.placed` events, and a stream processor groups them by merchant into
tumbling time windows, emitting a derived `revenue.by-merchant` stream.
The verify script also demonstrates **consumer lag** as a scaling signal —
pausing the processor to build lag, then resuming to drain it.

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) with
  [podman-compose](https://github.com/containers/podman-compose) or the
  Docker Compose plugin
- `curl` and `jq` for driving the API
- ~3 GB free memory (LGTM + Postgres + Kafka + 2 app services)

See the [shared infrastructure README](../_infra/README.md) for ports,
credentials, and the container naming convention.

## What it shows

| Pattern | Where | What |
|---------|-------|------|
| Windowed aggregation | stream-processor | Groups `order.placed` by merchant, 10s tumbling windows |
| Derived stream | `revenue.by-merchant` topic | Output is a new stream other services can consume |
| Consumer lag as scaling signal | verify.sh | Pause processor → lag builds; resume → lag drains |
| Stateful in-process | stream-processor | Running totals per merchant per window, flushed on expiry |

## Architecture

```
 curl ──▶ order-service ──▶ Postgres (orders)
               │
               ▼
       Kafka (order.placed)
               │
               ▼
       stream-processor
     [group by merchant_id]
     [tumbling 10s windows]
               │
               ▼
   Kafka (revenue.by-merchant)
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
# Place orders for different merchants
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"merchant_id":"acme","sku":"widget","quantity":3,"total":30.00}' \
  localhost:8080/orders | jq .

curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"merchant_id":"globex","sku":"gadget","quantity":1,"total":50.00}' \
  localhost:8080/orders | jq .

# Wait for the window to expire (10s), then read the derived stream
sleep 15
podman exec cndp-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic revenue.by-merchant \
  --from-beginning --timeout-ms 10000

# Check consumer lag
podman exec cndp-kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --describe --group stream-processor
```

## Verify

```bash
./verify.sh
```

## Observe

Open Grafana at http://localhost:3000:

- **Tempo** — traces from order-service and stream-processor show the flow
- **Loki** — search for `emitted revenue` to see window flush events

## Ports

| Service | Port |
|---------|------|
| order-service | 8080 |
| Grafana | 3000 |
| Postgres | 5432 |
| Kafka (host) | 9092 |
| Kafka UI | 8090 |
| OTLP HTTP | 4318 |
