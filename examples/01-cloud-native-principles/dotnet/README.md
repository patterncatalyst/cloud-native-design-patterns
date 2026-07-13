# Example 01 — Cloud-Native Principles (.NET)

Twelve-factor env-based config and liveness/readiness probes.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) minimal API
- **Libraries**: Npgsql (Postgres), OpenTelemetry hosting/OTLP exporter
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
| `OrderService/` | Program.cs — minimal API with MapGet/MapPost for orders and probes |

## Implementation notes

All logic in a single `Program.cs`. Uses raw Npgsql (no EF Core). Config via `IConfiguration` / env vars.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL, OTEL_EXPORTER_OTLP_ENDPOINT`

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
