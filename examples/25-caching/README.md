# Example 25 — Caching Patterns

Demonstrates six standard caching patterns — **cache-aside**, **read-through**,
**write-through**, **write-around**, **write-back**, and **refresh-ahead** — each
with its consistency story, failure mode, and a resilience test that proves the
cache is an optimisation, not a dependency.

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) with
  [podman-compose](https://github.com/containers/podman-compose) or the
  Docker Compose plugin
- `curl` and `jq` for driving the API
- ~1 GB free memory (Postgres + Redis + 1 app service)

See the [shared infrastructure README](../_infra/README.md) for ports,
credentials, and the container naming convention.

## What it shows

| Pattern | Endpoint | Behaviour |
|---------|----------|-----------|
| Cache-aside | `GET/PUT /cache-aside/products/{pid}` | App checks cache, misses to DB, populates; invalidates on write |
| Read-through | `GET /read-through/products/{pid}` | Wrapper class hides the cache/DB decision from callers |
| Write-through | `PUT /write-through/products/{pid}` | Writes DB first, then SETs cache (never stale for writer) |
| Write-around | `POST /write-around/events`, `GET .../events/{eid}` | Writes skip cache; reads populate lazily |
| Write-back | `PUT /write-back/metrics/{mid}` | Writes land in cache; background flusher persists to DB |
| Refresh-ahead | `GET /refresh-ahead/products/{pid}` | Background task pre-warms hot keys before TTL expires |

## Architecture

```
 Client
   │
   ▼
 cache-service (FastAPI)
   ├── Redis (cache tier)
   └── Postgres (source of truth)
       │
       └── Background tasks:
           ├── flusher  (write-back → DB)
           └── refresher (hot keys → cache)
```

## Run it

```bash
podman compose up --build -d
```

## Drive it

```bash
# Cache-aside: first read = miss, second = hit
curl -s localhost:8080/cache-aside/products/p1 | jq .
curl -s localhost:8080/cache-aside/products/p1 | jq .

# Write-through: write + immediate read returns new value from cache
curl -s -X PUT -H 'Content-Type: application/json' \
  -d '{"name":"Gizmo Deluxe","price_cents":2999}' \
  localhost:8080/write-through/products/p3 | jq .
curl -s localhost:8080/write-through/products/p3 | jq .

# Write-back: write to cache, wait for flush
curl -s -X PUT -H 'Content-Type: application/json' \
  -d '{"value":99.9,"tags":{"env":"test"}}' \
  localhost:8080/write-back/metrics/m1 | jq .
sleep 3
curl -s localhost:8080/write-back/flush-status | jq .

# Cache outage: stop Redis and confirm reads still work
podman stop cndp-redis
curl -s localhost:8080/cache-aside/products/p1 | jq .  # source: db
podman start cndp-redis
```

## Verify

```bash
./verify.sh
```

## Ports

| Service | Port |
|---------|------|
| cache-service | 8080 |
| Postgres | 5432 |
| Redis | 6379 |
