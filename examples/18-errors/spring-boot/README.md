# Example 18 — Errors & Problem Details (Spring Boot)

RFC 9457 Problem Details for REST errors, gRPC status codes with rich error details, and retry-aware error responses.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web, gRPC)
- **Libraries**: spring-boot-starter-webmvc, grpc-netty-shaded, grpc-protobuf, OpenTelemetry Java agent 2.32.0
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
| `order-service/` | OrderController.java — @ExceptionHandler returning ProblemDetail; GrpcErrorMapper — status code mapping |
| `inventory-service/` | InventoryGrpcService.java — gRPC server with StatusRuntimeException + Metadata |

## Implementation notes

Uses Spring's `ProblemDetail` class (built-in since Spring 6). gRPC errors include trailing metadata with structured error info.

The gRPC contract lives in `proto/` next to the services. The poms set the protobuf-maven-plugin `protoSourceRoot` to `${project.basedir}/../proto`, so `mvn package` works from a service directory with no copy into `src/main/proto`. Containerfiles copy `proto/` beside the service sources for the same reason.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`inventory.grpc.host`

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
