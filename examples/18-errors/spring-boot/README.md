# Example 18 — Errors & Problem Details (Spring Boot)

RFC 9457 Problem Details for REST errors, gRPC status codes with rich error details, and retry-aware error responses.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web, gRPC)
- **Libraries**: spring-boot-starter-webmvc, spring-boot-starter-grpc-server (inventory) and spring-boot-starter-grpc-client (callers), Spring gRPC 1.1.1, OpenTelemetry Java agent 2.32.0
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
| `order-service/` | OrderController.java and ApiErrors.java — `@ExceptionHandler` returning `ProblemDetail`, gRPC status codes mapped to 409/503; InventoryClient.java — Spring gRPC stub with a per-call deadline |
| `inventory-service/` | InventoryServiceImpl.java — `@GrpcService` bean returning gRPC status codes |

## Implementation notes

Uses Spring's `ProblemDetail` class (built-in since Spring 6). gRPC errors include trailing metadata with structured error info.

The gRPC contract lives in `proto/` next to the services. The poms set the protobuf-maven-plugin `protoSourceRoot` to `${project.basedir}/../proto`, so `mvn package` works from a service directory with no copy into `src/main/proto`. Containerfiles copy `proto/` beside the service sources for the same reason.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.grpc.client.channel.inventory.target` (from `INVENTORY_ADDR`), `inventory.deadline-ms` (from `GRPC_DEADLINE_MS`)

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
