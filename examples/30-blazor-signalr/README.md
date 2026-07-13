# Example 30 — Blazor Server + SignalR

A real-time order dashboard built with Blazor Server and SignalR. Orders placed
via the REST API appear on the dashboard in real time — pushed over the SignalR
circuit, no polling.

## Prerequisites

- Podman & podman-compose
- curl / jq
- ~1.5 GB memory (Postgres + Redis + LGTM + Blazor app)

## What it shows

| Concept | Where | What |
|---|---|---|
| SignalR hub | `OrderHub.cs` | Server-to-client push via hub groups |
| Blazor Server circuit | `Dashboard.razor` | Server-rendered UI, DOM diffs over WebSocket |
| Redis backplane | `Program.cs` | `AddStackExchangeRedis` for multi-pod scale-out |
| REST API | `Program.cs` | Same POST/GET /orders contract as other examples |
| OTel integration | `Program.cs` | Traces exported to Tempo via OTLP |

## Run it

```bash
cd dotnet && podman compose up --build -d
```

Wait for healthy (~30s), then verify:

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
| Blazor Dashboard (REST + UI) | 8080 |
| Grafana (LGTM) | 3000 |
| Postgres | 5432 |
| Redis | 6379 |

## Tear down

```bash
cd dotnet && podman compose down -v
```
