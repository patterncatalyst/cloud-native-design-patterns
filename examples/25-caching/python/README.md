# Example 25 — Caching (Python)

Six caching patterns in one service — cache-aside, read-through, write-through, write-around, write-back, and refresh-ahead.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: redis[hiredis] (Redis), asyncpg (Postgres), pydantic
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
| `cache-service/` | main.py — six endpoints each demonstrating a different cache pattern, Redis as cache layer, Postgres as source of truth |

## Implementation notes

Each pattern is a separate endpoint (e.g., `/aside/{key}`, `/read-through/{key}`). Write-back uses a background flush task. Refresh-ahead uses TTL-based preemptive refresh.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL, REDIS_URL`

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
