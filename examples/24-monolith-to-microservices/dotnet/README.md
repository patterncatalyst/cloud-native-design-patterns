# Example 24 — Monolith to Microservices (.NET)

Strangler fig pattern — router proxies to the monolith, decorator intercepts and enriches, new services peel off incrementally.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) minimal API
- **Libraries**: StackExchange.Redis, Confluent.Kafka
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
| `DecoratorService/` | Program.cs — HTTP proxy with Redis caching and Kafka publish |
| `RouterService/` | Program.cs — path-based reverse proxy |
| `StubService/` | Program.cs — placeholder microservice |

## Implementation notes

Uses `HttpClient` for proxying, `StackExchange.Redis` for caching, `Confluent.Kafka` for event publishing. Three separate .csproj projects.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`REDIS_URL, KAFKA_BOOTSTRAP, MONOLITH_URL`

## Local development (without containers)

Requires .NET 10 SDK.

```bash
dotnet run --project RouterService
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
