# Example 24 — Monolith to Microservices (.NET)

Strangler fig pattern — router proxies to the monolith, decorator intercepts and enriches, new services peel off incrementally.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10.0.12) minimal API
- **Libraries**: StackExchange.Redis, Confluent.Kafka 2.16.0
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
| `DecoratorService/` | Program.cs — HTTP proxy with Redis caching and Kafka publish |
| `RouterService/` | Program.cs — path-based reverse proxy |
| `StubService/` | Program.cs — placeholder microservice |

## Implementation notes

Uses `HttpClient` for proxying, `StackExchange.Redis` for caching, `Confluent.Kafka` for event publishing. Three separate .csproj projects.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`REDIS_URL, KAFKA_BOOTSTRAP, MONOLITH_URL`

## Local development (without containers)

Requires the .NET 10 SDK (10.0.112, runtime 10.0.12).

```bash
dotnet run --project RouterService
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
