# Example 04 — Data (.NET)

Database-per-service pattern — schema isolation, versioned migrations, and transactional consistency.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) minimal API
- **Libraries**: Npgsql, Npgsql.OpenTelemetry
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
| `OrderService/` | Program.cs — minimal API with raw Npgsql transactional access |

## Implementation notes

Uses `NpgsqlTransaction` for atomic writes. No ORM — raw SQL with parameterized queries.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL`

## Local development (without containers)

Requires .NET 10 SDK.

```bash
dotnet run --project OrderService
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
