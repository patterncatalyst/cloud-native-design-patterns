# Example 17 — Saga State & Compensation (.NET)

DB-backed saga orchestrator — three steps forward, reverse-order compensation on failure, crash-resumable.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10.0.12) minimal API
- **Libraries**: EF Core with Npgsql, Npgsql.OpenTelemetry, OTel
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
| `SagaOrchestrator/` | Program.cs — minimal API; SagaEngine.cs — advance/compensate logic; SagaContext.cs — EF Core mapping |

## Implementation notes

`SagaEngine` loads the saga with `FromSql(... FOR UPDATE)` inside an EF Core transaction, so concurrent advances of one saga serialize on the row lock. Saga steps and compensation are method calls within that transaction.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL`

## Local development (without containers)

Requires the .NET 10 SDK (10.0.112, runtime 10.0.12).

```bash
dotnet run --project SagaOrchestrator
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
