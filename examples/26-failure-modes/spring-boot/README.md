# Example 26 — Failure Modes (Spring Boot)

Circuit breaker, retry with backoff, timeout, and fallback — edge-service calling an unreliable backend.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web)
- **Libraries**: spring-boot-starter-webmvc, spring-boot-starter-restclient, resilience4j-spring-boot4 2.4.0, spring-boot-starter-aspectj
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
| `edge-service/` | EdgeController.java — resilience patterns calling backend |
| `backend-service/` | BackendController.java — configurable failure injection |

## Implementation notes

The breaker, retry and bulkhead are Resilience4j annotations (`@CircuitBreaker` with a fallback method, `@Retry`, `@Bulkhead`) on the `BackendClient` bean, so the calls go through a Spring proxy; their limits live in `application.properties` under `resilience4j.*`. A full bulkhead throws `BulkheadFullException`, which the controller answers with 429. `/breaker-state` reads the `CircuitBreakerRegistry`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`backend.url`

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
