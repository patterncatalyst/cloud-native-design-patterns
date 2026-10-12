# Example 21 — Graceful Shutdown (.NET)

SIGTERM handling — drain in-flight requests, stop accepting new ones, close DB connections, exit cleanly.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10.0.12) minimal API
- **Libraries**: Npgsql
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
| `OrderService/` | Program.cs — a SIGTERM registration flips readiness, waits the drain delay, then calls StopApplication; graceful drain via HostOptions.ShutdownTimeout |

## Implementation notes

A `PosixSignalRegistration` for SIGTERM (with `ManualLifetime` replacing `ConsoleLifetime`) flips readiness, waits `DRAIN_DELAY_SECONDS` (default 5), then calls `StopApplication()`: Kestrel stops accepting and finishes in-flight requests within `HostOptions.ShutdownTimeout` (20 s), the data source is disposed and the process exits 0. One SIGTERM, no second signal.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`ConnectionStrings__Default`, `DRAIN_DELAY_SECONDS`

## Local development (without containers)

Requires the .NET 10 SDK (10.0.112, runtime 10.0.12).

```bash
dotnet run --project OrderService
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
