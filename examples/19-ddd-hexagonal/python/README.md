# Example 19 — DDD & Hexagonal Architecture (Python)

Hexagonal (ports-and-adapters) architecture — domain logic isolated from infrastructure with explicit port interfaces.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: asyncpg, pydantic
- **Container base**: python:3.12-slim

## Run

```bash
podman compose up --build -d
```

Wait for healthy, then verify from the example root:

```bash
cd .. && bash verify.sh
```

## Project structure

| Path | Description |
|------|-------------|
| `order-service/` | main.py — domain model (Order, OrderStatus), port interfaces (OrderRepository), adapter implementations (PostgresOrderRepository), FastAPI driving adapter |

## Implementation notes

Domain types are plain dataclasses. Ports are abstract base classes. Adapters implement ports. FastAPI routes are the driving adapter — they call domain services, not DB directly.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL`

## Local development (without containers)

Requires pip install -r requirements.txt.

```bash
uvicorn main:app --reload --port 8080
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
