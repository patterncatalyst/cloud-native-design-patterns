# Example 17 — Saga State & Compensation (Python)

DB-backed saga orchestrator — three steps forward, reverse-order compensation on failure, crash-resumable.

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
| `saga-orchestrator/` | main.py — POST /sagas creates and runs a saga; advance() executes steps or compensates on failure |

## Implementation notes

Saga state persisted in `sagas` table with `step_index` and `status`. On restart, `RUNNING` sagas are re-entered. Uses `SELECT FOR UPDATE` for row-level locking.

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
