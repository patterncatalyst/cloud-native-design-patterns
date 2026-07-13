# Example 03 — Composition (Python)

API gateway pattern — BFF gateway aggregating order-api and inventory-service via GraphQL + gRPC.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: strawberry-graphql (GraphQL gateway), grpcio (gRPC client), asyncpg
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
| `gateway/` | main.py — GraphQL gateway federating order-api and inventory |
| `order-api/` | main.py — REST order service |
| `inventory-service/` | main.py — gRPC inventory service |

## Implementation notes

Gateway composes responses by calling both backends and merging results in the GraphQL resolver.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`ORDER_API_URL, INVENTORY_GRPC_HOST`

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
