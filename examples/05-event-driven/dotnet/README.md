# Example 05 — Event-Driven Architecture (.NET)

Kafka fan-out — order.placed events consumed independently by shipping and notification services with idempotent dedup.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10.0.12) minimal API + BackgroundService consumers
- **Libraries**: Confluent.Kafka 2.16.0, Npgsql, OTel
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
| `OrderService/` | Program.cs — REST API + Kafka producer (ProducerBuilder) |
| `ShippingConsumer/` | Program.cs — BackgroundService with ConsumerBuilder, manual commit after DB write |
| `NotificationConsumer/` | Program.cs — BackgroundService with ConsumerBuilder, manual commit after DB write |

## Implementation notes

Uses `Confluent.Kafka` directly for explicit consumer-group and offset-commit control (a bus abstraction such as MassTransit would hide them, and MassTransit v9 is commercially licensed). Each consumer is a `BackgroundService` with `EnableAutoCommit = false`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL, KAFKA_BOOTSTRAP`

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
