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

The SIGTERM handler keeps uvicorn's own handler and chains to it. One SIGTERM flips readiness to 503 at once; after `DRAIN_DELAY_SECONDS` (default 5) the handler calls uvicorn's, which stops accepting, finishes in-flight requests (`--timeout-graceful-shutdown 20`) and runs the lifespan exit that closes the pool. The process exits 0. A handler installed before uvicorn starts would replace uvicorn's for good, so it is installed in the lifespan.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL`, `DRAIN_DELAY_SECONDS`

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
