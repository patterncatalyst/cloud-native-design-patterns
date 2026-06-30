# Example 01 — Cloud-Native Principles

Demonstrates the two twelve-factor concerns you still write per service:
**config from the environment** (factor III) and **liveness vs readiness probes**.

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) with
  [podman-compose](https://github.com/containers/podman-compose) or the
  Docker Compose plugin
- `curl` and `jq` for driving the API
- ~2 GB free memory (LGTM + Postgres + app service)

See the [shared infrastructure README](../_infra/README.md) for ports,
credentials, and the container naming convention.

## What it shows

- `Settings` reads `DATABASE_URL`, `KAFKA_BOOTSTRAP`, `SERVICE_VERSION` from
  environment variables via `pydantic-settings` — one image, many environments.
- `/healthz` (liveness) always returns ok if the process is up — it never checks
  dependencies, so a transient DB outage does not trigger a restart loop.
- `/readyz` (readiness) checks the database — when it fails, Kubernetes stops
  routing traffic but leaves the pod running. When the DB recovers, readiness
  recovers with it.
- OpenTelemetry auto-instrumentation sends traces and metrics to the LGTM stack.

## Run it

```bash
podman compose up --build -d
```

Wait for all services to report healthy:

```bash
podman compose ps
```

## Drive it

```bash
# Check liveness
curl -s localhost:8080/healthz | jq .

# Check readiness
curl -s localhost:8080/readyz | jq .

# Create an order
curl -s -X POST 'localhost:8080/orders?customer=alice&total=42.50' | jq .

# List orders
curl -s localhost:8080/orders | jq .

# Stop Postgres and watch readiness flip (liveness stays ok)
podman stop cndp-postgres
curl -s localhost:8080/readyz | jq .   # → "status": "down"
curl -s localhost:8080/healthz | jq .  # → "status": "ok"

# Restart Postgres and watch readiness recover
podman start cndp-postgres
sleep 3
curl -s localhost:8080/readyz | jq .   # → "status": "ready"
```

## Verify

```bash
./verify.sh
```

## Observe

Open Grafana at http://localhost:3000 and explore:

- **Tempo** — traces for each HTTP request
- **Loki** — structured logs from the order-service
- **Prometheus** — HTTP request metrics (duration, count)

## Ports

| Service | Port |
|---------|------|
| order-service | 8080 |
| Grafana | 3000 |
| Postgres | 5432 |
| OTLP HTTP | 4318 |
