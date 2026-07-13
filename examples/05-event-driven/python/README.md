# Example 05 — Event-Driven Architecture (Python)

Kafka fan-out — order.placed events consumed independently by shipping and notification services with idempotent dedup.

## Framework & libraries

- **Framework**: FastAPI (order-service), standalone consumers
- **Libraries**: aiokafka (Kafka), asyncpg (Postgres), OTel
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
| `order-service/` | main.py — REST API, writes order to DB, publishes order.placed to Kafka |
| `shipping-consumer/` | main.py — Kafka consumer, inserts into shipments table with UNIQUE dedup |
| `notification-consumer/` | main.py — Kafka consumer, inserts into notifications table with UNIQUE dedup |

## Implementation notes

Consumers use `enable_auto_commit=False` — offset committed only after the DB write succeeds (commit-after-side-effect).

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL, KAFKA_BOOTSTRAP`

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
