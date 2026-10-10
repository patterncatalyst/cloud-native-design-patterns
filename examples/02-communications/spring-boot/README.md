# Example 02 — Communications (Spring Boot)

Four communication styles — REST, gRPC, async events (Kafka), and GraphQL — in one order+inventory system.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web, GraphQL, gRPC)
- **Libraries**: spring-boot-starter-graphql, spring-boot-starter-kafka (Spring Kafka 4), grpc-netty-shaded, grpc-protobuf
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
| `order-service/` | OrderController.java — REST + GraphQL; KafkaProducerConfig — async events; InventoryGrpcClient — gRPC calls |
| `inventory-service/` | InventoryGrpcService.java — gRPC server |

## Implementation notes

GraphQL schema in `resources/graphql/`. gRPC stubs generated via protobuf-maven-plugin.

The gRPC contract lives in `proto/` next to the services. The poms set the protobuf-maven-plugin `protoSourceRoot` to `${project.basedir}/../proto`, so `mvn package` works from a service directory with no copy into `src/main/proto`. Containerfiles copy `proto/` beside the service sources for the same reason.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.datasource.url, spring.kafka.bootstrap-servers, inventory.grpc.host`

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
