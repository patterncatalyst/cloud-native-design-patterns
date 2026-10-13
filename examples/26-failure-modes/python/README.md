# Example 26 — Failure Modes (Python)

Circuit breaker, retry with backoff, timeout, and fallback — edge-service calling an unreliable backend.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: httpx (HTTP client), tenacity (retry), pybreaker (circuit breaker), pydantic-settings
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
| `edge-service/` | main.py — client-side resilience (circuit breaker, retry, timeout, fallback) calling backend |
| `backend-service/` | main.py — unreliable service that can be configured to fail, slow down, or crash |

## Implementation notes

Retry is tenacity's `AsyncRetrying` with exponential jitter; the circuit breaker is pybreaker, used around the awaited call through its `calling()` context manager. The bulkhead is an `asyncio.Semaphore` that answers 429 when full. One `httpx.AsyncClient`, opened in the lifespan, serves every call. The backend's failure mode is set with `POST /mode`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`BACKEND_URL`

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
