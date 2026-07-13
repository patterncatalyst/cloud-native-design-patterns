# Example 02 — Communications (Python)

Four communication styles — REST, gRPC, async events (Kafka), and GraphQL — in one order+inventory system.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: aiokafka (Kafka), grpcio (gRPC), strawberry-graphql (GraphQL), asyncpg
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
| `order-service/` | main.py — REST, GraphQL, Kafka producer, gRPC client calling inventory |
| `inventory-service/` | main.py — gRPC server providing stock-check |

## Implementation notes

GraphQL uses Strawberry with FastAPI integration. gRPC stubs generated from `proto/inventory.proto`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL, KAFKA_BOOTSTRAP, INVENTORY_GRPC_HOST`

## Local development (without containers)

Requires pip install -r requirements.txt && python -m grpc_tools.protoc ....

```bash
uvicorn main:app --reload --port 8080
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
