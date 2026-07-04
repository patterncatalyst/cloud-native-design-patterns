# Example 28 — API Testing with Newman

Demonstrates **Newman** (the Postman CLI runner) as an automated API test
gate: a Postman collection with assertions runs headlessly against the
order-service, producing human-readable CLI output and machine-readable
JUnit XML for CI.

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) with
  [podman-compose](https://github.com/containers/podman-compose) or the
  Docker Compose plugin
- [Newman](https://www.npmjs.com/package/newman): `npm install -g newman`
- `curl` and `jq` for driving the API
- ~1 GB free memory (Postgres + 1 app service)

See the [shared infrastructure README](../_infra/README.md) for ports,
credentials, and the container naming convention.

## What it shows

| Concept | Where | What |
|---------|-------|------|
| CRUD assertions | `orders.postman_collection.json` | Status codes, response shape, chained variables |
| Validation tests | Collection > Validation | 422 for bad input, 404 for missing |
| Flow chaining | Create → Get → Cancel → Verify | Variables chain requests into a full flow |
| CI reporter | `--reporters junit` | JUnit XML for CI pipeline integration |
| Black-box testing | Any backend | Same collection tests any implementation |

## Architecture

```
 Newman CLI
   │
   ├── orders.postman_collection.json
   │     ├── Health check (200, status ok)
   │     ├── Create order (201, returns id, chains variable)
   │     ├── Get order (200, id matches)
   │     ├── List orders (200, array with items)
   │     ├── Cancel order (204)
   │     ├── Get cancelled (status = cancelled)
   │     ├── Reject zero quantity (422)
   │     ├── Reject missing sku (422)
   │     ├── Reject negative quantity (422)
   │     └── Get nonexistent (404)
   │
   └──→ order-service (port 8080) → Postgres
```

## Run it

```bash
# Start the service
podman compose up --build -d

# Run the collection
newman run collections/orders.postman_collection.json

# With JUnit XML for CI
newman run collections/orders.postman_collection.json \
  --reporters cli,junit \
  --reporter-junit-export newman.xml
```

## Verify

```bash
./verify.sh
```

## Ports

| Service | Port |
|---------|------|
| order-service | 8080 |
| Postgres | 5432 |
