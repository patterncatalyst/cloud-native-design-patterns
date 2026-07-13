# Example 24 — Monolith to Microservices (Spring Boot)

Strangler fig pattern — router proxies to the monolith, decorator intercepts and enriches, new services peel off incrementally.

## Framework & libraries

- **Framework**: Spring Boot (Web, Data Redis, Kafka)
- **Libraries**: spring-boot-starter-web, spring-boot-starter-data-redis, spring-kafka
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
| `decorator/` | REST proxy with Redis caching and Kafka event publishing |
| `router-service/` | Path-based routing to monolith or new services |
| `stub-service/` | Placeholder microservice |

## Implementation notes

Uses `RestTemplate` for proxying. Redis via `StringRedisTemplate`. Kafka via `KafkaTemplate`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.data.redis.host, spring.kafka.bootstrap-servers, monolith.url`

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
