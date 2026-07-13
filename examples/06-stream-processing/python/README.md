# Example 06 — Stream Processing (Python)

Kafka stream processor with tumbling-window aggregation — real-time order counts per SKU.

## Framework & libraries

- **Framework**: FastAPI (order-service), standalone processor
- **Libraries**: aiokafka (consumer + producer), asyncpg, OTel
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
| `order-service/` | main.py — REST API publishing order.placed events |
| `stream-processor/` | main.py — tumbling-window aggregation, consumes order.placed, produces sku-counts |

## Implementation notes

Stream processor implements windowing manually with time-bucketed dictionaries and periodic flush. Uses faust-streaming patterns without the full framework.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`KAFKA_BOOTSTRAP, DATABASE_URL`

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
