# Example 22 — L7 Routing (Spring Boot)

Two-part routing — Envoy weighted splits (90/10 + header override) and in-app rule-driven routing (VIP orders to priority topic).

## Framework & libraries

- **Framework**: Spring Boot (Web)
- **Libraries**: spring-boot-starter-web
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
| `order-service/` | OrderController.java — backend API |
| `router-service/` | RouterController.java — rule-based routing logic |

## Implementation notes

Envoy handles L7 weighted splits. Spring service implements application-level routing rules (VIP detection, topic selection).

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`KAFKA_BOOTSTRAP`

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
