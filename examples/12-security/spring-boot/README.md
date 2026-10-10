# Example 12 — Security (Spring Boot)

Three security patterns — sidecar trust (mTLS header check), valet key (HMAC-signed time-bound tokens), and per-tenant bulkhead.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web)
- **Libraries**: spring-boot-starter-webmvc (no Spring Security — patterns are hand-rolled)
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
| `order-service/` | SidecarTrustFilter.java — servlet filter; ValetKeyService.java — HMAC signing; BulkheadService.java — Semaphore per tenant |

## Implementation notes

Each pattern is a separate class. SidecarTrustFilter rejects requests without mTLS client cert header. Bulkhead uses `java.util.concurrent.Semaphore`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`HMAC_SECRET`

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
