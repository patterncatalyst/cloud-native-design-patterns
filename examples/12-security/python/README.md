# Example 12 — Security (Python)

Three security patterns — sidecar trust (mTLS header check), valet key (HMAC-signed time-bound tokens), and per-tenant bulkhead.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: pydantic (no external security libs — patterns are hand-rolled)
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
| `order-service/` | main.py — middleware checks X-Forwarded-Client-Cert, HMAC valet keys, asyncio.Semaphore bulkhead |

## Implementation notes

No OTel or DB in this example — purely demonstrates security middleware patterns. Bulkhead uses `asyncio.Semaphore` per tenant ID.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`HMAC_SECRET`

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
