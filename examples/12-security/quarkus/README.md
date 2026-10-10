# Example 12 — Security (Quarkus)

Three security patterns — sidecar trust (mTLS header check), valet key (HMAC-signed time-bound tokens), and per-tenant bulkhead.

## Framework & libraries

- **Framework**: Quarkus 3.40.1 LTS (RESTEasy Reactive + Jackson)
- **Libraries**: quarkus-rest, quarkus-rest-jackson (no Quarkus Security — patterns are hand-rolled)
- **Container base**: `registry.access.redhat.com/ubi10/openjdk-25:1.24-15` (build), `registry.access.redhat.com/ubi10/openjdk-25-runtime:1.24-15` (runtime)

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
| `order-service/` | SidecarTrustFilter.java — JAX-RS ContainerRequestFilter; ValetKeyService.java — HMAC signing; BulkheadService.java — Semaphore per tenant |

## Implementation notes

Each pattern is a separate class. SidecarTrustFilter is a @PreMatching ContainerRequestFilter that rejects requests without mTLS client cert header. Bulkhead uses `java.util.concurrent.Semaphore`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`VALET_SECRET`

## Local development (without containers)

Requires JDK 25+, Maven.

```bash
mvn quarkus:dev
```

## Tear down

```bash
docker compose down -v
```
