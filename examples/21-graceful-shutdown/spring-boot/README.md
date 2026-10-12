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

A `sun.misc.Signal` handler registered before Spring starts takes the single SIGTERM: it flips readiness, waits `DRAIN_DELAY_SECONDS` (default 5) while endpoints update, then calls `System.exit(0)`. Spring's shutdown hook and built-in graceful shutdown stop accepting new connections, drain in-flight requests up to `spring.lifecycle.timeout-per-shutdown-phase` (20 s) and close the ApplicationContext. The process exits 0.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.datasource.url, server.shutdown=graceful, DRAIN_DELAY_SECONDS`

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
