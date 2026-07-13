# Example 04 — Data (Spring Boot)

Database-per-service pattern — schema isolation, versioned migrations, and transactional consistency.

## Framework & libraries

- **Framework**: Spring Boot (Web, JDBC)
- **Libraries**: spring-boot-starter-jdbc, PostgreSQL driver, OTel
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
| `order-service/` | OrderController.java — REST API with JdbcTemplate transactional access |

## Implementation notes

Uses `@Transactional` for write operations. Schema managed via init scripts in `db/init/`.

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
