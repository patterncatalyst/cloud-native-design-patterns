# Example 04 — Data (Python)

Database-per-service pattern — schema isolation, versioned migrations, and transactional consistency.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: asyncpg (Postgres), pydantic, OTel
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
| `order-service/` | main.py — CRUD API with transactional order creation and versioned schema |

## Implementation notes

Demonstrates SELECT FOR UPDATE, transactional writes, and schema migration via init SQL.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL`

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
