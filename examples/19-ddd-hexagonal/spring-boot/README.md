# Example 19 — DDD & Hexagonal Architecture (Spring Boot)

Hexagonal (ports-and-adapters) architecture — domain logic isolated from infrastructure with explicit port interfaces.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web, JDBC)
- **Libraries**: spring-boot-starter-webmvc, spring-boot-starter-jdbc
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
| `order-service/` | Domain layer (Order.java, OrderStatus.java), port interfaces (OrderRepository.java), adapters (JdbcOrderRepository.java), driving adapter (OrderController.java) |

## Implementation notes

Clean package structure: `domain/`, `port/`, `adapter/`. Spring DI wires adapters to ports. Controller depends only on port interfaces, never on JDBC directly.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.datasource.url`

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

## CLI driving adapter

`cli-place-order <sku> <qty>` is on PATH in the image and drives the same PlaceOrder use case:

```bash
docker exec cndp-order-service cli-place-order bolt-x 5
```
