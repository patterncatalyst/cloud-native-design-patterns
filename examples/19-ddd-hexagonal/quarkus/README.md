# Example 19 — DDD & Hexagonal Architecture (Quarkus)

Hexagonal (ports-and-adapters) architecture — domain logic isolated from infrastructure with explicit port interfaces.

## Framework & libraries

- **Framework**: Quarkus 3.33 LTS (REST, JDBC)
- **Libraries**: quarkus-rest, quarkus-rest-jackson, quarkus-jdbc-postgresql, quarkus-agroal
- **Container base**: UBI10 / OpenJDK 25

## Run

```bash
podman compose up --build -d
```

Wait for healthy, then verify from the example root:

```bash
cd .. && LANG_DIR=quarkus bash verify.sh
```

## Project structure

| Path | Description |
|------|-------------|
| `order-service/src/.../domain/` | Domain layer — Order aggregate, PlaceOrderCmd value object, OrderPlaced event, port interfaces (OrderRepository, EventPublisher), PlaceOrderUseCase. Zero framework imports. |
| `order-service/src/.../adapter/` | Driven adapters — PostgresOrderRepository (raw JDBC via DataSource), LogEventPublisher (JBoss Logger). Driving adapter — OrderResource (JAX-RS REST). |
| `order-service/src/.../OrderServiceApp.java` | CDI @Produces method wiring PlaceOrderUseCase from its ports — proves domain has no CDI dependency. |
| `order-service/src/.../CliPlaceOrder.java` | CLI driving adapter — standalone main(), raw JDBC, no Quarkus/CDI. Proves port replaceability. |

## Implementation notes

Clean package structure: `domain/`, `adapter/`. CDI wires adapter beans to port interfaces. PlaceOrderUseCase is a plain Java class instantiated via a @Produces factory method — it never imports jakarta.* or io.quarkus.*. The CLI adapter proves the same domain works without any framework at all.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`QUARKUS_DATASOURCE_JDBC_URL`, `QUARKUS_DATASOURCE_USERNAME`, `QUARKUS_DATASOURCE_PASSWORD`

## Local development (without containers)

Requires JDK 25+, Maven.

```bash
mvn quarkus:dev
```

Requires a running Postgres — see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
