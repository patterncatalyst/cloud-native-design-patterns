# Example 22 — L7 Routing & Traffic Management

Demonstrates two halves of L7 routing: **mesh-level traffic splitting**
(Envoy weighted clusters + header-based override) and **in-app rule-driven
routing** (VIP orders to a priority topic, ordinary orders to default,
rules changeable without redeployment).

## Prerequisites

- [Podman](https://podman.io/getting-started/installation) with
  [podman-compose](https://github.com/containers/podman-compose) or the
  Docker Compose plugin
- `curl` for driving the API
- ~512 MB free memory (Envoy + 2 backends + router)

## What it shows

| Concept | Where | What |
|---------|-------|------|
| Weighted routing | Envoy config | 90/10 split between v1 and v2 backends |
| Header-based override | Envoy config | `x-route-to: v2` bypasses weight and always hits v2 |
| In-app rule routing | `router-service` | Orders above threshold go to priority topic |
| Runtime rule change | `PUT /rules` | Change routing without code change or redeploy |
| Version markers | Response body | Every response carries its backend version |

## Architecture

```
                        ┌───────────────┐
           Client ───── │  Envoy proxy  │ ──── port 8080
                        │  (L7 router)  │
                        └──┬─────────┬──┘
                  90%      │         │     10%
               ┌───────────┘         └───────────┐
               │                                 │
        ┌──────┴──────┐                   ┌──────┴──────┐
        │  order-v1   │                   │  order-v2   │
        │ version=v1  │                   │ version=v2  │
        └─────────────┘                   └─────────────┘

           Client ───── router-service ──── port 8090
                        │  rules engine │
                        │  VIP → priority │
                        │  default → default │
```

## Run it

```bash
# Start all services
podman compose up --build -d

# Weighted routing — observe version field in responses
for i in $(seq 1 20); do curl -s http://localhost:8080/orders | jq -r .version; done

# Header override — always v2
curl -s -H 'x-route-to: v2' http://localhost:8080/orders | jq .

# In-app routing — VIP vs ordinary
curl -s -X POST http://localhost:8090/orders \
  -H 'Content-Type: application/json' \
  -d '{"sku":"diamond","quantity":1,"amount":2500}' | jq .

curl -s -X POST http://localhost:8090/orders \
  -H 'Content-Type: application/json' \
  -d '{"sku":"widget","quantity":3,"amount":50}' | jq .

# Change rules at runtime
curl -s -X PUT http://localhost:8090/rules \
  -H 'Content-Type: application/json' \
  -d '{"vip_threshold": 500}' | jq .
```

## Verify

```bash
./verify.sh
```

## Ports

| Service | Port |
|---------|------|
| Envoy proxy | 8080 |
| router-service | 8090 |
