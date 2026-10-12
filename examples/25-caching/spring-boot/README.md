# Example 25 — Caching (Spring Boot)

Six caching patterns in one service — cache-aside, read-through, write-through, write-around, write-back, and refresh-ahead.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web, Data JPA, Actuator, Data Redis)
- **Libraries**: spring-boot-starter-data-redis, spring-boot-starter-data-jpa, spring-boot-starter-actuator
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
| `cache-service/` | CacheController.java — REST endpoints; SafeRedis.java — resilient Redis wrapper; BackgroundTasks.java — write-back flush + refresh-ahead |

## Implementation notes

Uses `StringRedisTemplate` for cache operations. `SafeRedis` wraps Redis calls with try/catch so cache outage doesn't break reads (falls back to DB). Background tasks use `@Scheduled`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.data.redis.host, spring.datasource.url`

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
