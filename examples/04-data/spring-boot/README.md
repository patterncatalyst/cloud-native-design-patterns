# Example 04 — Data (Spring Boot)

Database-per-service pattern — schema isolation, versioned migrations, and transactional consistency.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web, JDBC)
- **Libraries**: spring-boot-starter-jdbc, PostgreSQL driver, OpenTelemetry Java agent
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
| `order-service/` | OrderController.java — REST API with JdbcTemplate transactional access |

## Implementation notes

Uses `@Transactional` for write operations. Schema managed via init scripts in `db/init/`.

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
