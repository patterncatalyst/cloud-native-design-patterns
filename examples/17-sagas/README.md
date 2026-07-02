# Example 17 — Saga State & Compensation

Demonstrates a **DB-backed saga orchestrator** with compensation. Three steps
(`charge_payment` → `reserve_stock` → `book_shipping`) execute forward; when
`book_shipping` fails, compensation runs in **reverse order** over only the
completed steps (`release_stock` → `refund_payment`). The saga state is
persisted so it resumes from `step_index` after a crash.

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) with
  [podman-compose](https://github.com/containers/podman-compose) or the
  Docker Compose plugin
- `curl` and `jq` for driving the API
- ~2 GB free memory (LGTM + Postgres + saga-orchestrator)

See the [shared infrastructure README](../_infra/README.md) for ports,
credentials, and the container naming convention.

## What it shows

| Pattern | Where | What |
|---------|-------|------|
| DB-backed state machine | `sagas` table | One row per saga: status, step_index, context JSON |
| Forward execution | `POST /sagas` | Steps execute in order; each result stored in context |
| Compensation | on failure | Reverse-order compensating actions over completed steps only |
| Resume after crash | startup scan | `RUNNING` sagas re-entered via `advance()` on restart |

## Architecture

```
 curl ──▶ saga-orchestrator ──▶ Postgres (sagas + saga_log)
               │
               ├── charge_payment
               ├── reserve_stock
               └── book_shipping (can fail)
                        │
                        ▼ on failure
               ├── release_stock  (reverse)
               └── refund_payment (reverse)
```

## Run it

```bash
podman compose up --build -d
```

## Drive it

```bash
# Happy path (all steps succeed)
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"order_id":"order-1","sku":"widget-a","total":29.99}' \
  localhost:8080/sagas | jq .

# Unhappy path (shipping fails → compensation)
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"order_id":"order-2","sku":"widget-b","total":49.99,"fail_shipping":true}' \
  localhost:8080/sagas | jq .

# Check the saga log
SAGA_ID=<from above>
curl -s localhost:8080/sagas/$SAGA_ID/log | jq .
```

## Verify

```bash
./verify.sh
```

## Observe

Open Grafana at http://localhost:3000:

- **Tempo** — traces show saga.charge_payment → saga.reserve_stock →
  saga.book_shipping (happy), or the compensation spans (unhappy)

## Ports

| Service | Port |
|---------|------|
| saga-orchestrator | 8080 |
| Grafana | 3000 |
| Postgres | 5432 |
| OTLP HTTP | 4318 |
