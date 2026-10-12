# Example 25 — Caching (.NET)

Six caching patterns in one service — cache-aside, read-through, write-through, write-around, write-back, and refresh-ahead.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10.0.12) minimal API
- **Libraries**: StackExchange.Redis, Microsoft.Extensions.Caching.Hybrid with the Redis distributed cache, EF Core with Npgsql
- **Container base**: registry.access.redhat.com/ubi9/dotnet-100-aspnet:9.8-1791363520 (runtime), built with ubi9/dotnet-100:9.8-1791421718; runs as UID 1001

## Run

```bash
docker compose up -d --build --wait
```

Wait for healthy, then verify from the example root:

```bash
cd .. && bash verify.sh
```

## Project structure

| Path | Description |
|------|-------------|
| `CacheService/` | Program.cs — minimal API with six cache-pattern endpoints; CacheContext.cs — EF Core mapping; CacheWorkers.cs — the write-back flusher and refresh-ahead `BackgroundService`s |

## Implementation notes

Read-through goes through `HybridCache.GetOrCreateAsync` (in-process L1, Redis L2). The other five patterns spell out the cache steps on a StackExchange.Redis client, because the strategy is the lesson. The write-back flusher upserts with one `ExecuteSqlAsync` `ON CONFLICT` statement. Cache resilience: Redis failures fall back to DB.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL, REDIS_URL`

## Local development (without containers)

Requires the .NET 10 SDK (10.0.112, runtime 10.0.12).

```bash
dotnet run --project CacheService
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
