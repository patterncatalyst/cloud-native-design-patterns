# Example 27 — Feature Flags (Python)

OpenFeature SDK with flagd provider — runtime feature toggles without redeployment.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: openfeature-sdk, openfeature-provider-flagd
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
| `flag-service/` | main.py — REST API with feature-flag-gated behavior, OpenFeature client evaluating flags from flagd |

## Implementation notes

Uses OpenFeature's vendor-neutral API. flagd sidecar reads flag definitions from `flags/flags.json`. Flag evaluation is synchronous per-request.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`FLAGD_HOST, FLAGD_PORT`

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
