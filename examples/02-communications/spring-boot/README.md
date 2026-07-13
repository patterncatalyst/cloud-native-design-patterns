# Example 02 — Communications (Spring Boot)

Four communication styles — REST, gRPC, async events (Kafka), and GraphQL — in one order+inventory system.

## Framework & libraries

- **Framework**: Spring Boot (Web, GraphQL, gRPC)
- **Libraries**: spring-boot-starter-graphql, spring-kafka, grpc-netty-shaded, grpc-protobuf
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
| `order-service/` | OrderController.java — REST + GraphQL; KafkaProducerConfig — async events; InventoryGrpcClient — gRPC calls |
| `inventory-service/` | InventoryGrpcService.java — gRPC server |

## Implementation notes

GraphQL schema in `resources/graphql/`. gRPC stubs generated via protobuf-maven-plugin.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.datasource.url, spring.kafka.bootstrap-servers, inventory.grpc.host`

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
