# Example 11 — Observability (Spring Boot)

Distributed tracing, structured logging, and metrics across REST + gRPC + Kafka services with the LGTM stack.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web, gRPC, Kafka)
- **Libraries**: spring-boot-starter-webmvc, spring-boot-starter-kafka (Spring Kafka 4), spring-boot-starter-grpc-server (inventory) and spring-boot-starter-grpc-client (callers), Spring gRPC 1.1.1, OpenTelemetry API (agent supplies the SDK)
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
| `order-service/` | REST + gRPC client + Kafka publisher with auto-traced spans |
| `inventory-service/` | `@GrpcService` bean served by Spring gRPC; the OTel agent instruments grpc-java underneath |
| `notification-consumer/` | @KafkaListener with trace context extracted from headers |

## Implementation notes

The OpenTelemetry Java agent (2.32.0) is attached with `JAVA_TOOL_OPTIONS=-javaagent:/deployments/opentelemetry-javaagent.jar`. The Containerfile downloads the jar from Maven Central and checks it against a pinned SHA-256. The agent instruments Spring MVC, gRPC, JDBC and the Kafka clients, propagates W3C trace context across REST, gRPC and Kafka, and writes `trace_id` and `span_id` into the logback MDC. The services use only the OpenTelemetry API (`GlobalOpenTelemetry`) for the custom counters. The agent is used instead of the OpenTelemetry Spring Boot starter because one jar gives zero-code instrumentation of HTTP, gRPC, JDBC and Kafka, identical across services, plus `trace_id` injection into the MDC.

The gRPC contract lives in `proto/` next to the services. The poms set the protobuf-maven-plugin `protoSourceRoot` to `${project.basedir}/../proto`, so `mvn package` works from a service directory with no copy into `src/main/proto`. Containerfiles copy `proto/` beside the service sources for the same reason.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME, SPRING_KAFKA_BOOTSTRAP_SERVERS`

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
