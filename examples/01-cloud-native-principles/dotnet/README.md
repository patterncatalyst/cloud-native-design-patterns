# Example 01 — Cloud-Native Principles (.NET)

Twelve-factor env-based config and liveness/readiness probes.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10.0.12) minimal API
- **Libraries**: Npgsql (Postgres), OpenTelemetry hosting/OTLP exporter
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
| `OrderService/` | Program.cs — minimal API with MapGet/MapPost for orders and probes |

## Implementation notes

All logic in a single `Program.cs`. Uses raw Npgsql (no EF Core). Config via `IConfiguration` / env vars.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL, OTEL_EXPORTER_OTLP_ENDPOINT`

## Local development (without containers)

Requires the .NET 10 SDK (10.0.12).

```bash
dotnet run --project OrderService
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
