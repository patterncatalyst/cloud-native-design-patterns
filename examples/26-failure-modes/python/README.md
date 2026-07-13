# Example 26 — Failure Modes (Python)

Circuit breaker, retry with backoff, timeout, and fallback — edge-service calling an unreliable backend.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: httpx (HTTP client), pydantic
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
| `edge-service/` | main.py — client-side resilience (circuit breaker, retry, timeout, fallback) calling backend |
| `backend-service/` | main.py — unreliable service that can be configured to fail, slow down, or crash |

## Implementation notes

Circuit breaker implemented manually (state machine with CLOSED/OPEN/HALF-OPEN). Retry uses exponential backoff with jitter. Backend failure modes configurable via query params.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`BACKEND_URL`

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
