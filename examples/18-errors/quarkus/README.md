# Example 18 — Errors & Problem Details (Quarkus)

RFC 9457 Problem Details for REST errors, gRPC status codes with rich error details, and retry-aware error responses.

## Framework & libraries

- **Framework**: Quarkus 3.33.2 LTS (RESTEasy Reactive, gRPC)
- **Libraries**: quarkus-rest, quarkus-rest-jackson, quarkus-grpc, quarkus-opentelemetry
- **Container base**: UBI10 / OpenJDK 25

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
| `order-service/` | OrderResource.java — JAX-RS endpoints with structured error responses; InventoryClient — gRPC client with deadline |
| `inventory-service/` | InventoryServiceImpl.java — @GrpcService with stock tracking and fail modes |

## Implementation notes

Uses Quarkus RESTEasy Reactive with Jackson for REST and quarkus-grpc for inter-service communication. gRPC errors are mapped to structured JSON error responses with trace IDs from OpenTelemetry.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`QUARKUS_GRPC_CLIENTS_INVENTORY_HOST`, `QUARKUS_GRPC_CLIENTS_INVENTORY_PORT`, `GRPC_DEADLINE_MS`

## Local development (without containers)

Requires JDK 25+, Maven.

```bash
mvn quarkus:dev
```

## Tear down

```bash
podman compose down -v
```
