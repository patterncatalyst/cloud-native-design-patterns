# Example 06 — Stream Processing (Spring Boot)

Kafka stream processor with tumbling-window aggregation — real-time order counts per SKU.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web, Kafka, Kafka Streams)
- **Libraries**: spring-boot-starter-kafka (Spring Kafka 4), kafka-streams, spring-boot-starter-jdbc, OpenTelemetry Java agent
- **Container base**: `ubi10/openjdk-25-runtime:1.24-15` (UID 185)

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
| `order-service/` | OrderController.java — REST + Kafka publish |
| `stream-processor/` | RevenueTopology.java — Kafka Streams tumbling window per merchant with TimeWindows.ofSizeWithNoGrace() |

## Implementation notes

The stream processor is a Kafka Streams topology (`@EnableKafkaStreams` with a `StreamsBuilder` bean). `order.placed` is re-keyed by merchant, aggregated in tumbling windows (`TimeWindows.ofSizeWithNoGrace`) and written to `revenue.by-merchant` as JSON (`window_start`, `window_end`, `merchant_id`, `order_count`, `revenue`). The windowed aggregate is a KTable, so every update to a (merchant, window) row is emitted: a window yields a running total that settles when it closes, and consumers keep the latest record per `(merchant_id, window_start)`. `application.id` is `stream-processor`, which is also the consumer group. An order whose total is not a number is skipped with a warning, and a record that cannot be deserialized is logged and skipped (`LogAndContinueExceptionHandler`). The source topic is declared with a `NewTopics` bean because Kafka Streams stops when a source topic is missing.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`SPRING_KAFKA_BOOTSTRAP_SERVERS, WINDOW_SECONDS, OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME`

## Local development (without containers)

Requires JDK 25 and Maven 3.9+.

```bash
mvn spring-boot:run
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
