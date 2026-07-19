# Example 25 — Caching (Quarkus)

Six caching patterns in one service — cache-aside, read-through, write-through, write-around, write-back, and refresh-ahead.

## Framework & libraries

- **Framework**: Quarkus 3.33.2 LTS (RESTEasy Reactive, Agroal JDBC, Redis Client, Scheduler)
- **Libraries**: quarkus-redis-client, quarkus-jdbc-postgresql
- **Container base**: UBI10 / OpenJDK 25

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
| `cache-service/` | CacheResource.java — REST endpoints; SafeRedis.java — resilient Redis wrapper; BackgroundTasks.java — write-back flush + refresh-ahead |

## Implementation notes

Uses `RedisDataSource` from quarkus-redis-client for cache operations. `SafeRedis` wraps Redis calls with try/catch so cache outage does not break reads (falls back to DB). Background tasks use Quarkus `@Scheduled`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`QUARKUS_REDIS_HOSTS, QUARKUS_DATASOURCE_JDBC_URL`

## Local development (without containers)

Requires JDK 25+, Maven (wrapper included).

```bash
./mvnw quarkus:dev
```

Requires a running Postgres and Redis —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
