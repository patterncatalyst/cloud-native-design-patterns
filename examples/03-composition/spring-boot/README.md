# Example 03 — Composition (Spring Boot)

API gateway pattern — BFF gateway aggregating order-api and inventory-service via GraphQL + gRPC.

## Framework & libraries

- **Framework**: Spring Boot (Web, GraphQL, gRPC)
- **Libraries**: spring-boot-starter-graphql, grpc-netty-shaded, grpc-protobuf
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
| `gateway/` | GraphQL gateway with Spring @QueryMapping resolvers |
| `order-api/` | REST order service |
| `inventory-service/` | gRPC service |

## Implementation notes

GraphQL schema stitching in the gateway. Uses `@SchemaMapping` and `@QueryMapping` annotations.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`order-api.url, inventory.grpc.host`

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
