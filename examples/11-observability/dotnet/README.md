# Example 11 — Observability (.NET)

Distributed tracing, structured logging, and metrics across REST + gRPC + Kafka services with the LGTM stack.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10)
- **Libraries**: OpenTelemetry.Extensions.Hosting, OpenTelemetry.Instrumentation.AspNetCore, Confluent.Kafka, Grpc.Net.Client
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
| `OrderService/` | Program.cs — REST + gRPC client + Kafka producer with OTel hosting |
| `InventoryService/` | Program.cs — gRPC server with OTel |
| `NotificationConsumer/` | Program.cs — BackgroundService Kafka consumer with manual trace propagation |

## Implementation notes

Uses `AddOpenTelemetry()` with `AddAspNetCoreInstrumentation()`. Kafka trace context manually injected/extracted via message headers since Confluent.Kafka has no built-in OTel support.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME`

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
