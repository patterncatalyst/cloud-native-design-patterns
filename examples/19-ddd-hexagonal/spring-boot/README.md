# Example 19 — DDD & Hexagonal Architecture (Spring Boot)

Hexagonal (ports-and-adapters) architecture — domain logic isolated from infrastructure with explicit port interfaces.

## Framework & libraries

- **Framework**: Spring Boot (Web, JDBC)
- **Libraries**: spring-boot-starter-web, spring-boot-starter-jdbc
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
| `order-service/` | Domain layer (Order.java, OrderStatus.java), port interfaces (OrderRepository.java), adapters (JdbcOrderRepository.java), driving adapter (OrderController.java) |

## Implementation notes

Clean package structure: `domain/`, `port/`, `adapter/`. Spring DI wires adapters to ports. Controller depends only on port interfaces, never on JDBC directly.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.datasource.url`

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
