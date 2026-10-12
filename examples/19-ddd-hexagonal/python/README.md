# Example 19 — DDD & Hexagonal Architecture (Python)

Hexagonal (ports-and-adapters) architecture — domain logic isolated from infrastructure with explicit port interfaces.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: asyncpg, pydantic
- **Container base**: `ubi10/python-314-minimal` (Python 3.14, non-root UID 1001)

## Run

```bash
docker compose up -d --build --wait
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

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14. In the service directory, `uv sync` installs the locked dependencies.

```bash
uv run uvicorn main:app --reload --port 8080
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```

## CLI driving adapter

`cli-place-order <sku> <qty>` is on PATH in the image and drives the same PlaceOrder use case:

```bash
docker exec cndp-order-service cli-place-order bolt-x 5
```
