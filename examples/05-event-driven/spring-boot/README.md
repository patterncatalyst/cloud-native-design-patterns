# Example 05 — Event-Driven Architecture (Spring Boot)

Kafka fan-out — order.placed events consumed independently by shipping and notification services with idempotent dedup.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web, Kafka)
- **Libraries**: spring-boot-starter-kafka (Spring Kafka 4), spring-boot-starter-jdbc, PostgreSQL driver, OpenTelemetry Java agent 2.32.0
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
| `order-service/` | OrderController.java — REST + KafkaTemplate publish |
| `shipping-consumer/` | ShippingListener.java — @KafkaListener with manual ack + JDBC insert |
| `notification-consumer/` | NotificationListener.java — @KafkaListener with manual ack + JDBC insert |

## Implementation notes

Uses `AckMode.MANUAL_IMMEDIATE` — offset committed only after successful DB insert. UNIQUE constraint prevents double processing.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.kafka.bootstrap-servers, spring.datasource.url`

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
