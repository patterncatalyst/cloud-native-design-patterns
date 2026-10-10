# Example 26 — Failure Modes (.NET)

Circuit breaker, retry with backoff, timeout, and fallback — edge-service calling an unreliable backend.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10.0.12) minimal API
- **Libraries**: None beyond ASP.NET Core
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
| `EdgeService/` | Program.cs — HttpClient with circuit breaker, retry, timeout, fallback |
| `BackendService/` | Program.cs — configurable failure injection endpoint |

## Implementation notes

Resilience patterns hand-rolled (no Polly) to show the mechanics. Uses `HttpClient` with custom delegating handlers or inline retry logic.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`BACKEND_URL`

## Local development (without containers)

Requires the .NET 10 SDK (10.0.12).

```bash
dotnet run --project EdgeService
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
