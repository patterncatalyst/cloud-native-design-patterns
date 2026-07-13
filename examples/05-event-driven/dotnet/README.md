# Example 05 — Event-Driven Architecture (.NET)

Kafka fan-out — order.placed events consumed independently by shipping and notification services with idempotent dedup.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) minimal API + BackgroundService consumers
- **Libraries**: Confluent.Kafka, Npgsql, OTel
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
| `OrderService/` | Program.cs — REST API + Kafka producer (ProducerBuilder) |
| `ShippingConsumer/` | Program.cs — BackgroundService with ConsumerBuilder, manual commit after DB write |
| `NotificationConsumer/` | Program.cs — BackgroundService with ConsumerBuilder, manual commit after DB write |

## Implementation notes

Uses `Confluent.Kafka` directly (not MassTransit) for explicit consumer control. Each consumer is a `BackgroundService` with `EnableAutoCommit = false`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL, KAFKA_BOOTSTRAP`

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
