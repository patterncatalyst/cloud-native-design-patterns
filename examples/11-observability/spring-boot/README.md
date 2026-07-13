# Example 11 — Observability (Spring Boot)

Distributed tracing, structured logging, and metrics across REST + gRPC + Kafka services with the LGTM stack.

## Framework & libraries

- **Framework**: Spring Boot (Web, gRPC, Kafka)
- **Libraries**: spring-boot-starter-web, spring-kafka, grpc-netty-shaded, micrometer-tracing, OTel exporter
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
| `order-service/` | REST + gRPC client + Kafka publisher with auto-traced spans |
| `inventory-service/` | gRPC server with OTel instrumentation |
| `notification-consumer/` | @KafkaListener with trace context extracted from headers |

## Implementation notes

Spring Boot auto-configures OTel via Micrometer Tracing bridge. Kafka trace headers propagated automatically by Spring Kafka.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`management.otlp.tracing.endpoint, spring.kafka.bootstrap-servers`

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
