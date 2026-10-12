# Example 11 — Observability (Python)

Distributed tracing, structured logging, and metrics across REST + gRPC + Kafka services with the LGTM stack.

## Framework & libraries

- **Framework**: FastAPI (order-service), standalone consumers
- **Libraries**: OpenTelemetry SDK with OTLP export and FastAPI/gRPC instrumentation, aiokafka, grpcio, asyncpg
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
| `order-service/` | main.py — REST + gRPC client + Kafka producer, fully instrumented |
| `inventory-service/` | main.py — gRPC server with OTel instrumentation |
| `notification-consumer/` | main.py — Kafka consumer with trace context propagation |

## Implementation notes

Uses OTel auto-instrumentation (`opentelemetry-instrument`) for FastAPI. Manual span creation for Kafka consumer. Trace context propagated via Kafka headers.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME`

## Local development (without containers)

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14. In the service directory, `uv sync` installs the locked dependencies.

```bash
uv run opentelemetry-instrument uvicorn main:app --port 8080
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
