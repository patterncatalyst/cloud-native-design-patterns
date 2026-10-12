# Example 04 — Data (Python)

Database-per-service pattern — schema isolation, versioned migrations, and transactional consistency.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: asyncpg (Postgres), pydantic, OTel
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
| `order-service/` | main.py — CRUD API with transactional order creation and versioned schema |

## Implementation notes

Demonstrates SELECT FOR UPDATE, transactional writes, and schema migration via init SQL.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL`

## Local development (without containers)

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14. In the service directory, `uv sync` installs the locked dependencies.

```bash
uv run uvicorn main:app --reload --port 8080
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
