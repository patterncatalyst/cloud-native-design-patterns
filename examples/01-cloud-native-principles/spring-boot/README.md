# Example 01 — Cloud-Native Principles (Spring Boot)

Twelve-factor env-based config and liveness/readiness probes.

## Framework & libraries

- **Framework**: Spring Boot (Web, JDBC)
- **Libraries**: spring-boot-starter-web, spring-boot-starter-jdbc, PostgreSQL JDBC driver, OTel
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
| `order-service/` | OrderController.java — REST endpoints; HealthController.java — probe endpoints |

## Implementation notes

Config in application.yaml with `${ENV_VAR:default}` syntax. Uses `JdbcTemplate` for database access.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL, OTEL_EXPORTER_OTLP_ENDPOINT`

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
