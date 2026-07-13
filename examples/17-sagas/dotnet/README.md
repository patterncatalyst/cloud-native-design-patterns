# Example 17 — Saga State & Compensation (.NET)

DB-backed saga orchestrator — three steps forward, reverse-order compensation on failure, crash-resumable.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) minimal API
- **Libraries**: Npgsql, Npgsql.OpenTelemetry, OTel
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
| `SagaOrchestrator/` | Program.cs — minimal API with saga advance/compensate logic, Npgsql transactions with SELECT FOR UPDATE |

## Implementation notes

All logic in one `Program.cs`. Uses `NpgsqlTransaction` with `FOR UPDATE` row locking. Saga steps and compensation are method calls within a transaction.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL`

## Local development (without containers)

Requires .NET 10 SDK.

```bash
dotnet run --project SagaOrchestrator
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
