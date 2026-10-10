# Example 21 — Graceful Shutdown (Spring Boot)

SIGTERM handling — drain in-flight requests, stop accepting new ones, close DB connections, exit cleanly.

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
| `order-service/` | OrderController.java — REST API; graceful shutdown via `server.shutdown=graceful` and `spring.lifecycle.timeout-per-shutdown-phase` |

## Implementation notes

Spring Boot's built-in graceful shutdown handles SIGTERM: stops accepting new connections, drains in-flight requests up to the configured timeout, then closes the ApplicationContext.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.datasource.url, server.shutdown=graceful`

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
