# Example 30 — Blazor Server + SignalR

A real-time order dashboard built with Blazor Server and SignalR. Orders placed
via the REST API appear on the dashboard in real time — pushed over the SignalR
circuit, no polling.

## Prerequisites

- Docker Engine with the Compose plugin (see [Prerequisites](../PREREQUISITES.md))
- curl / jq
- ~1.5 GB memory (Postgres + Redis + LGTM + Blazor app)

## What it shows

| Concept | Where | What |
|---|---|---|
| SignalR hub | `OrderHub.cs` | Server-to-client push via hub groups |
| Blazor Server circuit | `Dashboard.razor` | Server-rendered UI, DOM diffs over WebSocket |
| Redis backplane | `Program.cs`, `compose.yaml` | `AddStackExchangeRedis`; two dashboard instances (8080, 8081) share it, so a push published through one reaches clients on the other |
| REST API | `Program.cs` | Same POST/GET /orders contract as other examples |
| OTel integration | `Program.cs` | Traces exported to Tempo via OTLP |

## Run it

```bash
cd dotnet && docker compose up -d --build --wait
```

Wait for healthy (~30s), then verify (health, orders, the dashboard page, SignalR negotiate, and Redis backplane delivery across the two instances, including after a restart of one):

```bash
cd .. && bash verify.sh
```

## Drive it

```bash
# Place an order — the dashboard updates live
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{"sku":"WIDGET-1","quantity":5}'

# List orders
curl -s http://localhost:8080/orders | jq

# Open the dashboard in a browser
open http://localhost:8080/dashboard
```

## Observe

- **Grafana** at http://localhost:3000 — Tempo traces show the order flow
- **Dashboard** at http://localhost:8080/dashboard — orders appear in real time

## Ports

| Service | Port |
|---|---|
| Blazor Dashboard, instance 1 (REST + UI) | 8080 |
| Blazor Dashboard, instance 2 (same backplane) | 8081 |
| Grafana (LGTM) | 3000 |
| Postgres | 5432 |
| Redis | 6379 |

## Tear down

```bash
cd dotnet && docker compose down -v
```
