# Example 26 — Failure Modes (Spring Boot)

Circuit breaker, retry with backoff, timeout, and fallback — edge-service calling an unreliable backend.

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
| `edge-service/` | EdgeController.java — resilience patterns calling backend |
| `backend-service/` | BackendController.java — configurable failure injection |

## Implementation notes

Resilience patterns hand-rolled (no Resilience4j) to show the mechanics explicitly. Circuit breaker uses `AtomicReference<State>`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`backend.url`

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
