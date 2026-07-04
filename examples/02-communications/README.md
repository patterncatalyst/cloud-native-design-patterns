# Example 02 — Communications

Demonstrates the four interaction styles from the communications chapter:
**REST** at the edge, **gRPC** for internal calls, **GraphQL** for composed
reads, and **async events** via Kafka for decoupled facts.

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) with
  [podman-compose](https://github.com/containers/podman-compose) or the
  Docker Compose plugin
- `curl` and `jq` for driving the API
- ~3.5 GB free memory (LGTM + Postgres + Kafka + two app services)

See the [shared infrastructure README](../_infra/README.md) for ports,
credentials, and the container naming convention.

## What it shows

| Style | Where | What |
|-------|-------|------|
| REST | `POST /orders`, `GET /orders` | Validated input (Pydantic), 201 on create, cursor pagination |
| gRPC | order → inventory (`:50051`) | `ReserveStock` RPC from `.proto` contract; order status depends on stock |
| GraphQL | `POST /graphql` | Strawberry schema querying orders — one round-trip, client picks fields |
| Async | order → Kafka `order.placed` | Fire-and-forget fact; consumers catch up from the log independently |

## Architecture

```
                     ┌──────────────┐
  curl / browser ──▶ │ order-service │──gRPC──▶ inventory (:50051)
   REST :8080        │  + GraphQL   │
                     │  + Kafka     │──async──▶ Kafka (order.placed)
                     └──────────────┘
```

## Run it

```bash
# Python (FastAPI)
cd python && podman compose up --build -d

# Spring Boot (coming soon)
# cd spring-boot && podman compose up --build -d
```

Wait for all services to report healthy:

```bash
podman compose ps
```

## Drive it

```bash
# REST — create an order (201 Created)
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"sku":"widget-a","quantity":5}' \
  localhost:8080/orders | jq .

# REST — validation rejects bad input (422)
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"sku":"","quantity":0}' \
  localhost:8080/orders | jq .

# REST — cursor pagination
curl -s 'localhost:8080/orders?limit=2' | jq .

# GraphQL — query orders, pick your fields
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"query":"{ orders(limit: 5) { id sku status } }"}' \
  localhost:8080/graphql | jq .

# gRPC — order with enough stock → confirmed; too much → rejected
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"sku":"rare-item","quantity":1}' \
  localhost:8080/orders | jq .status

curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"sku":"rare-item","quantity":200}' \
  localhost:8080/orders | jq .status

# Async — check Kafka received the event
podman exec cndp-kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --list
```

## Verify

From the example root (not the language directory):

```bash
cd ..  # if you're still in python/
./verify.sh
```

## Observe

Open Grafana at http://localhost:3000 and explore:

- **Tempo** — traces show the REST→gRPC call chain and Kafka publish
- **Loki** — structured logs from both services
- **Prometheus** — HTTP request metrics

## Ports

| Service | Port |
|---------|------|
| order-service (REST + GraphQL) | 8080 |
| inventory (gRPC) | 50051 |
| Grafana | 3000 |
| Postgres | 5432 |
| Kafka (host) | 9092 |
| Kafka UI | 8090 |
| OTLP HTTP | 4318 |
