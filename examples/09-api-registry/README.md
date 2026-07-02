# Example 09 — API Registry

Demonstrates **Apicurio Registry** as the single authoritative home for API
contracts. The verify script registers an Avro schema, sets a `BACKWARD`
compatibility rule, then proves the gate: a **breaking change** (renamed
fields) is rejected with `409 Conflict`, while an **additive change** (new
optional field) is accepted.

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) with
  [podman-compose](https://github.com/containers/podman-compose) or the
  Docker Compose plugin
- `curl` and `jq` for driving the API
- ~2 GB free memory (Apicurio + LGTM)

See the [shared infrastructure README](../_infra/README.md) for ports,
credentials, and the container naming convention.

## What it shows

| Pattern | Where | What |
|---------|-------|------|
| Schema registration | `POST /groups/orders/artifacts` | Register an Avro schema as a versioned artifact |
| Compatibility rules | `POST .../rules` | Set `BACKWARD` — new consumers must read old data |
| Breaking change gate | `POST .../versions` | Renamed fields → `409 Conflict` (blocked) |
| Additive change | `POST .../versions` | New optional field → `200 OK` (accepted) |

## Architecture

```
 curl ──▶ Apicurio Registry (v3 API)
              │
              ├── Register artifact (Avro schema)
              ├── Set compatibility rule (BACKWARD)
              ├── POST new version (breaking) → 409
              └── POST new version (additive) → 200
```

## Run it

```bash
podman compose up -d
```

Wait for Apicurio to be ready:

```bash
curl -sf http://localhost:8081/health/ready | jq .
```

## Drive it

```bash
# Register the initial schema
curl -sf -X POST http://localhost:8081/apis/registry/v3/groups/orders/artifacts \
  -H "Content-Type: application/json" \
  -d '{
    "artifactId": "order-placed",
    "artifactType": "AVRO",
    "firstVersion": {
      "version": "1.0.0",
      "content": {
        "content": "...(v1 schema JSON string)...",
        "contentType": "application/json"
      }
    }
  }' | jq .

# Set compatibility rule
curl -sf -X POST \
  http://localhost:8081/apis/registry/v3/groups/orders/artifacts/order-placed/rules \
  -H "Content-Type: application/json" \
  -d '{ "ruleType": "COMPATIBILITY", "config": "BACKWARD" }'

# Try a breaking change
curl -s -w "\n%{http_code}" -X POST \
  http://localhost:8081/apis/registry/v3/groups/orders/artifacts/order-placed/versions \
  -H "Content-Type: application/json" \
  -d '{ "version": "2.0.0", "content": { "content": "...", "contentType": "application/json" } }'
# → 409 Conflict

# Try an additive change
# → 200 OK
```

## Verify

```bash
./verify.sh
```

## Observe

Open Grafana at http://localhost:3000:

- **Loki** — Apicurio logs show compatibility check decisions

## Ports

| Service | Port |
|---------|------|
| Apicurio Registry | 8081 |
| Grafana | 3000 |
| OTLP HTTP | 4318 |
