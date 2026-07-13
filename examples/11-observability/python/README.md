# Example 11 — Observability (Python)

Distributed tracing, structured logging, and metrics across REST + gRPC + Kafka services with the LGTM stack.

## Framework & libraries

- **Framework**: FastAPI (order-service), standalone consumers
- **Libraries**: opentelemetry-distro (auto-instrumentation), aiokafka, grpcio, asyncpg
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
| `order-service/` | main.py — REST + gRPC client + Kafka producer, fully instrumented |
| `inventory-service/` | main.py — gRPC server with OTel instrumentation |
| `notification-consumer/` | main.py — Kafka consumer with trace context propagation |

## Implementation notes

Uses OTel auto-instrumentation (`opentelemetry-instrument`) for FastAPI. Manual span creation for Kafka consumer. Trace context propagated via Kafka headers.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME`

## Local development (without containers)

Requires pip install -r requirements.txt.

```bash
opentelemetry-instrument uvicorn main:app --port 8080
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
