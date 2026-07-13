# Example 05 — Event-Driven Architecture (Spring Boot)

Kafka fan-out — order.placed events consumed independently by shipping and notification services with idempotent dedup.

## Framework & libraries

- **Framework**: Spring Boot (Web, Kafka)
- **Libraries**: spring-kafka, spring-boot-starter-jdbc, PostgreSQL driver
- **Container base**: eclipse-temurin:21-jre

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
| `order-service/` | OrderController.java — REST + KafkaTemplate publish |
| `shipping-consumer/` | ShippingListener.java — @KafkaListener with manual ack + JDBC insert |
| `notification-consumer/` | NotificationListener.java — @KafkaListener with manual ack + JDBC insert |

## Implementation notes

Uses `AckMode.MANUAL_IMMEDIATE` — offset committed only after successful DB insert. UNIQUE constraint prevents double processing.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.kafka.bootstrap-servers, spring.datasource.url`

## Local development (without containers)

Requires JDK 21+, Maven (wrapper included).

```bash
./mvnw spring-boot:run
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
