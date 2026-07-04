# Example 19 — DDD & Hexagonal Architecture

Demonstrates **hexagonal architecture** (ports and adapters) with a clean
domain core that has **zero framework imports**. The same `PlaceOrder` use
case is driven by two independent adapters — REST and CLI — proving that
the domain is protocol-agnostic.

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) with
  [podman-compose](https://github.com/containers/podman-compose) or the
  Docker Compose plugin
- `curl` and `jq` for driving the API
- ~1 GB free memory (Postgres + 1 app service)

See the [shared infrastructure README](../_infra/README.md) for ports,
credentials, and the container naming convention.

## What it shows

| Concept | Where | What |
|---------|-------|------|
| Pure domain core | `domain/` | Models, ports (Protocol), and service with zero framework imports |
| Outbound ports | `domain/ports.py` | `OrderRepository` and `EventPublisher` as Python Protocols |
| Application service | `domain/service.py` | `PlaceOrder` — imports only domain types |
| REST driving adapter | `adapters/rest_adapter.py` | FastAPI routes calling the use case |
| CLI driving adapter | `cli_place_order.py` | CLI script calling the same use case |
| Postgres driven adapter | `adapters/postgres_repo.py` | Implements `OrderRepository` via asyncpg |
| Log driven adapter | `adapters/log_publisher.py` | Implements `EventPublisher` via stdlib logging |
| Dependency inversion | `main.py` | Wires adapters into domain service at startup |

## Architecture

```
              ┌─────────────────────────────────────────┐
              │           domain/ (pure Python)         │
              │  models.py   ports.py   service.py      │
              │  (Order)   (Protocol)  (PlaceOrder)     │
              └────────┬──────────────────┬─────────────┘
                       │                  │
            outbound ports          inbound call
                       │                  │
        ┌──────────────┴──┐    ┌──────────┴───────────┐
        │  Driven adapters │    │  Driving adapters    │
        │  postgres_repo   │    │  rest_adapter (HTTP) │
        │  log_publisher   │    │  cli_place_order     │
        └─────────────────┘    └──────────────────────┘
```

## Run it

```bash
# Start the service
# Python (FastAPI)
cd python && podman compose up --build -d

# Spring Boot (coming soon)
# cd spring-boot && podman compose up --build -d

# Place an order via REST
curl -s -X POST http://localhost:8080/orders \
  -H 'Content-Type: application/json' \
  -d '{"sku":"widget-a","quantity":3}' | jq .

# Place an order via CLI (same use case, different adapter)
podman exec cndp-order-service python cli_place_order.py bolt-x 5

# Verify both orders appear
curl -s http://localhost:8080/orders | jq .
```

## The cross-check

```bash
# 1. Grep domain/ for framework imports — should find nothing
grep -r 'fastapi\|asyncpg\|pydantic\|uvicorn' order-service/domain/

# 2. The CLI adapter calls the same PlaceOrder use case
#    without touching any domain file — only a new adapter appears
```

## Verify

From the example root (not the language directory):

```bash
cd ..  # if you're still in python/
./verify.sh
```

## Ports

| Service | Port |
|---------|------|
| order-service | 8080 |
| Postgres | 5432 |
