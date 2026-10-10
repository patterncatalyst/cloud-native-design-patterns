# Example 06 — Stream Processing (.NET)

Kafka Streams-style topology on Streamiz: tumbling-window revenue per merchant.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10.0.12) order service; console host for the processor
- **Libraries**: Confluent.Kafka 2.16.0 (order service), Streamiz.Kafka.Net 1.8.2 (processor), OTel 1.19
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
| `OrderService/` | Program.cs — REST API + Kafka producer |
| `StreamProcessor/` | Program.cs — Streamiz topology: re-key by merchant, tumbling window, aggregate |

## Implementation notes

Same contract as the Quarkus and Spring Boot stream processors: `order.placed` is re-keyed by `merchant_id`, aggregated in a tumbling window with no grace period (`WINDOW_SECONDS`, default 10), and every update is written to `revenue.by-merchant` as `window_start`, `window_end` (epoch seconds), `merchant_id`, `order_count`, `revenue`. `application.id` is `stream-processor` (also the consumer group). A total that is not a number is skipped with a warning; an undeserializable record is logged and skipped. The window state lives in RocksDB under `/tmp/kafka-streams`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`KAFKA_BOOTSTRAP`, `WINDOW_SECONDS`

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
