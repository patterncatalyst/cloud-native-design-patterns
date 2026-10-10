# Example 22 — L7 Routing (Spring Boot)

Two-part routing — Envoy weighted splits (90/10 + header override) and in-app rule-driven routing (VIP orders to priority topic).

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web)
- **Libraries**: spring-boot-starter-webmvc
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
| `order-service/` | OrderController.java — backend API |
| `router-service/` | RouterController.java — rule-based routing logic |

## Implementation notes

Envoy handles L7 weighted splits. Spring service implements application-level routing rules (VIP detection, topic selection).

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`KAFKA_BOOTSTRAP`

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
