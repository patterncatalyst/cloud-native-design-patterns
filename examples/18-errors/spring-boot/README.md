# Example 18 — Errors & Problem Details (Spring Boot)

RFC 9457 Problem Details for REST errors, gRPC status codes with rich error details, and retry-aware error responses.

## Framework & libraries

- **Framework**: Spring Boot (Web, gRPC)
- **Libraries**: spring-boot-starter-web, grpc-netty-shaded, grpc-protobuf
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
| `order-service/` | OrderController.java — @ExceptionHandler returning ProblemDetail; GrpcErrorMapper — status code mapping |
| `inventory-service/` | InventoryGrpcService.java — gRPC server with StatusRuntimeException + Metadata |

## Implementation notes

Uses Spring's `ProblemDetail` class (built-in since Spring 6). gRPC errors include trailing metadata with structured error info.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`inventory.grpc.host`

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
