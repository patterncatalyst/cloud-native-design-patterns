# Example 06 — Stream Processing (Spring Boot)

Kafka stream processor with tumbling-window aggregation — real-time order counts per SKU.

## Framework & libraries

- **Framework**: Spring Boot (Web, Kafka, Kafka Streams)
- **Libraries**: spring-kafka (includes Kafka Streams binder), spring-boot-starter-jdbc
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
| `order-service/` | OrderController.java — REST + Kafka publish |
| `stream-processor/` | StreamTopology.java — Kafka Streams tumbling window with TimeWindows.ofSizeWithNoGrace() |

## Implementation notes

Uses Kafka Streams DSL for declarative windowing. The topology is defined as a `@Bean` and managed by Spring's Kafka Streams auto-config.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.kafka.bootstrap-servers`

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
