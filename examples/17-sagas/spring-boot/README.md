# Example 17 — Saga State & Compensation (Spring Boot)

DB-backed saga orchestrator — three steps forward, reverse-order compensation on failure, crash-resumable.

## Framework & libraries

- **Framework**: Spring Boot (Web, JDBC)
- **Libraries**: spring-boot-starter-jdbc, PostgreSQL driver, OTel
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
| `saga-orchestrator/` | SagaController.java — REST; SagaService.java — advance/compensate logic; StepExecutor.java — step dispatch; model classes for Saga, SagaStep, SagaLogEntry |

## Implementation notes

Most decomposed: controller/service/executor/model layers. Uses `@Transactional` with `SELECT FOR UPDATE` for saga row locking. StartupRunner rescans `RUNNING` sagas.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.datasource.url`

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
