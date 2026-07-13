# Example 22 — L7 Routing (Python)

Two-part routing — Envoy weighted splits (90/10 + header override) and in-app rule-driven routing (VIP orders to priority topic).

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: aiokafka (Kafka), pydantic
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
| `order-service/` | main.py — backend behind Envoy, responds to routed requests |
| `router-service/` | main.py — rule engine routing VIP orders to a priority Kafka topic |

## Implementation notes

Envoy config in `envoy/envoy.yaml` does weighted routing at the infrastructure level. The router-service applies business rules at the application level.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`KAFKA_BOOTSTRAP`

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
