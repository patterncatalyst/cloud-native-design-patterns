# Example 25 — Caching (.NET)

Six caching patterns in one service — cache-aside, read-through, write-through, write-around, write-back, and refresh-ahead.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) minimal API
- **Libraries**: StackExchange.Redis, Npgsql
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
| `CacheService/` | Program.cs — minimal API with six cache-pattern endpoints, StackExchange.Redis for caching, Npgsql for Postgres |

## Implementation notes

All six patterns in one `Program.cs`. Uses `IConnectionMultiplexer` for Redis. Write-back pattern uses a `BackgroundService` for periodic flush. Cache resilience: Redis failures fall back to DB.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL, REDIS_URL`

## Local development (without containers)

Requires .NET 10 SDK.

```bash
dotnet run --project CacheService
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
