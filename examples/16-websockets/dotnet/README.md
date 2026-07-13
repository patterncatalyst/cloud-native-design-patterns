# Example 16 — WebSockets (.NET)

WebSocket scale-out with Redis pub/sub backplane — two server pods sharing state for cross-pod message delivery.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) minimal API
- **Libraries**: StackExchange.Redis (pub/sub), OTel
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
| `WsServer/` | Program.cs — native WebSocket middleware with Redis backplane via StackExchange.Redis subscriber |

## Implementation notes

Uses ASP.NET Core's built-in `WebSocket` middleware (not SignalR). Redis `ISubscriber` for cross-pod broadcast. All logic in one `Program.cs`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`REDIS_URL`

## Local development (without containers)

Requires .NET 10 SDK.

```bash
dotnet run --project WsServer
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
