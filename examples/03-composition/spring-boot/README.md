# Example 03 — Composition (Spring Boot)

API gateway pattern — BFF gateway aggregating order-api and inventory-service via GraphQL + gRPC.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web, GraphQL, gRPC)
- **Libraries**: spring-boot-starter-graphql, grpc-netty-shaded, grpc-protobuf
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
| `gateway/` | GraphQL gateway with Spring @QueryMapping resolvers |
| `order-api/` | REST order service |
| `inventory-service/` | gRPC service |

## Implementation notes

GraphQL schema stitching in the gateway. Uses `@SchemaMapping` and `@QueryMapping` annotations.

The gRPC contract lives in `proto/` next to the services. The poms set the protobuf-maven-plugin `protoSourceRoot` to `${project.basedir}/../proto`, so `mvn package` works from a service directory with no copy into `src/main/proto`. Containerfiles copy `proto/` beside the service sources for the same reason.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`order-api.url, inventory.grpc.host`

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
