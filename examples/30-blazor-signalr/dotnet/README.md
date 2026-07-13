# Example 30 — Blazor Server + SignalR (.NET)

Real-time order dashboard built with Blazor Server and SignalR — orders placed
via the REST API appear on the dashboard in real time, pushed over the SignalR
circuit with no polling.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) Blazor Server
- **Libraries**: SignalR (hub + client), SignalR.StackExchangeRedis (backplane), Npgsql (Postgres), OTel
- **Container base**: registry.access.redhat.com/ubi9/dotnet-100-aspnet (runtime)

## Run

```bash
podman compose up --build -d
```

Wait for healthy, then verify from the example root:

```bash
cd .. && bash verify.sh
```

## Project structure

| Path | Description |
|------|-------------|
| `BlazorDashboard/Program.cs` | Host setup — REST API (GET/POST /orders), SignalR hub mapping, Redis backplane, OTel |
| `BlazorDashboard/Hubs/OrderHub.cs` | SignalR hub — JoinDashboard group method |
| `BlazorDashboard/OrderDto.cs` | Shared DTO record (Id, Sku, Quantity, Status) |
| `BlazorDashboard/Components/Pages/Dashboard.razor` | Blazor component — live order table with HubConnection subscription |
| `BlazorDashboard/Components/App.razor` | Root layout with InteractiveServer render mode |

## Implementation notes

This is a .NET-specific example (no Python or Spring Boot equivalent). Blazor Server
keeps all UI logic on the server — the browser runs a thin JS runtime connected by a
SignalR "circuit" (persistent WebSocket). DOM diffs travel over the wire.

The `OrderHub` manages connection groups. When `POST /orders` creates an order in
Postgres, it calls `hub.Clients.Group("dashboard").SendAsync("OrderPlaced", order)`
to push the event to all connected dashboard clients.

The Redis backplane (`AddStackExchangeRedis`) ensures that push messages reach clients
connected to any pod — the same scaling solution discussed in Appendix C, built into
SignalR with one line of config.

## Environment variables

Key variables (set by compose.yaml):

`DATABASE_URL, REDIS_URL, OTEL_EXPORTER_OTLP_ENDPOINT`

## Local development (without containers)

```bash
# .NET 10 SDK required
dotnet run --project BlazorDashboard
```

Requires a running Postgres and Redis — see compose.yaml for the connection strings.

## Tear down

```bash
podman compose down -v
```
