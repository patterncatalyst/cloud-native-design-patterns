# Example 01 — Cloud-Native Principles (Python)

Twelve-factor env-based config and liveness/readiness probes.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: asyncpg (Postgres), OpenTelemetry auto-instrumentation
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
| `order-service/` | main.py — single-file API with /orders, /healthz, /readyz endpoints |

## Implementation notes

Uses `asyncpg` for async Postgres access. Config read from environment variables via `pydantic-settings`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL, OTEL_EXPORTER_OTLP_ENDPOINT`

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
