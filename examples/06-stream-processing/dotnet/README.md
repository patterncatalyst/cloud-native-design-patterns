# Example 06 — Stream Processing (.NET)

Kafka stream processor with tumbling-window aggregation — real-time order counts per SKU.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) + BackgroundService processor
- **Libraries**: Confluent.Kafka, OTel
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
| `OrderService/` | Program.cs — REST API + Kafka producer |
| `StreamProcessor/` | Program.cs — BackgroundService with manual tumbling-window aggregation using Confluent.Kafka consumer/producer |

## Implementation notes

Implements tumbling windows manually (no Streamiz in this example) — time-bucketed dictionary flushed on window close. Uses `Confluent.Kafka` consumer + producer directly.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`KAFKA_BOOTSTRAP`

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
