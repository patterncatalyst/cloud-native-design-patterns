# Example 21 — Graceful Shutdown (Python)

SIGTERM handling — drain in-flight requests, stop accepting new ones, close DB connections, exit cleanly.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: asyncpg, pydantic
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
| `order-service/` | main.py — signal handler sets shutdown flag, /readyz flips to 503, in-flight requests complete before exit |

## Implementation notes

Uses `signal.signal(SIGTERM, ...)` to set a shutdown flag. Readiness probe returns 503 during drain. Uvicorn's graceful shutdown timeout allows in-flight requests to complete.

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
docker compose down -v
```
