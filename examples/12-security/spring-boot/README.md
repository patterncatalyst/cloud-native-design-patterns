# Example 12 — Security (Spring Boot)

Three security patterns — sidecar trust (mTLS header check), valet key (HMAC-signed time-bound tokens), and per-tenant bulkhead.

## Framework & libraries

- **Framework**: Spring Boot (Web)
- **Libraries**: spring-boot-starter-web (no Spring Security — patterns are hand-rolled)
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
| `order-service/` | SidecarTrustFilter.java — servlet filter; ValetKeyService.java — HMAC signing; BulkheadService.java — Semaphore per tenant |

## Implementation notes

Each pattern is a separate class. SidecarTrustFilter rejects requests without mTLS client cert header. Bulkhead uses `java.util.concurrent.Semaphore`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`HMAC_SECRET`

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
