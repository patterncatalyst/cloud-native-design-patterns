# Example 12 — Security (Python)

Three security patterns — sidecar trust (mTLS header check), valet key (HMAC-signed time-bound tokens), and per-tenant bulkhead.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: pydantic (no external security libs: the patterns are written in the service)
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
| `order-service/` | main.py — middleware checks X-Forwarded-Client-Cert, HMAC valet keys, asyncio.Semaphore bulkhead |

## Implementation notes

No OTel or DB in this example — purely demonstrates security middleware patterns. The bulkhead is an `asyncio.Semaphore` per tenant ID; a request that finds the tenant's permits taken gets 429 at once.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`HMAC_SECRET`

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
