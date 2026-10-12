# Example 21 — Graceful Shutdown (Spring Boot)

SIGTERM handling — drain in-flight requests, stop accepting new ones, close DB connections, exit cleanly.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web, Data JPA, Actuator)
- **Libraries**: spring-boot-starter-webmvc, spring-boot-starter-data-jpa, spring-boot-starter-actuator
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

On SIGTERM, Spring stops lifecycle beans from the highest phase down. `DrainLifecycle` (a `SmartLifecycle` bean at `DEFAULT_PHASE - 512`) stops first: it flips readiness with an `AvailabilityChangeEvent`, then sleeps `DRAIN_DELAY_SECONDS` (default 5) while endpoints update. The readiness group includes a `drain` health indicator, so `/readyz` returns 503 with the reason `shutting down` while `/healthz` stays 200. Then the web server's graceful shutdown (`server.shutdown=graceful`) drains in-flight requests up to `spring.lifecycle.timeout-per-shutdown-phase` (20 s) and the ApplicationContext closes. The JVM exits with 143 (128 + SIGTERM) after a clean shutdown.

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
