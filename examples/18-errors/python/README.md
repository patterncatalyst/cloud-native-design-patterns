# Example 18 — Errors & Problem Details (Python)

RFC 9457 Problem Details for REST errors, gRPC status codes with rich error details, and retry-aware error responses.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: grpcio, pydantic
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
| `order-service/` | main.py — REST API returning RFC 9457 Problem Details; gRPC client with status mapping |
| `inventory-service/` | main.py — gRPC server returning Status with error details |

## Implementation notes

REST errors return `application/problem+json` with type, title, status, detail, instance fields. gRPC errors use `google.rpc.Status` with `ErrorInfo` details.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`INVENTORY_GRPC_HOST`

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
