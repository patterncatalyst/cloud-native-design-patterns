# Example 21 — Graceful Shutdown (Spring Boot)

SIGTERM handling — drain in-flight requests, stop accepting new ones, close DB connections, exit cleanly.

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
| `order-service/` | OrderController.java — REST API; graceful shutdown via `server.shutdown=graceful` and `spring.lifecycle.timeout-per-shutdown-phase` |

## Implementation notes

Spring Boot's built-in graceful shutdown handles SIGTERM: stops accepting new connections, drains in-flight requests up to the configured timeout, then closes the ApplicationContext.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.datasource.url, server.shutdown=graceful`

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
