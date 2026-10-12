# Example 01 — Cloud-Native Principles (Spring Boot)

Twelve-factor env-based config and liveness/readiness probes.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web, Data JPA, Actuator)
- **Libraries**: spring-boot-starter-webmvc, spring-boot-starter-data-jpa, spring-boot-starter-actuator, PostgreSQL JDBC driver, OpenTelemetry Java agent
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
| `order-service/` | OrderController.java — REST endpoints; probes come from Actuator health groups at `/healthz` and `/readyz` (see application.yaml) |

## Implementation notes

Config in application.yaml with `${ENV_VAR:default}` syntax. Uses Spring Data JPA (`OrderRepository`) for database access.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL, OTEL_EXPORTER_OTLP_ENDPOINT`

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
