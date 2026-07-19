# Example 12 — Security (Quarkus)

Three security patterns — sidecar trust (mTLS header check), valet key (HMAC-signed time-bound tokens), and per-tenant bulkhead.

## Framework & libraries

- **Framework**: Quarkus 3.33.2 LTS (RESTEasy Reactive + Jackson)
- **Libraries**: quarkus-rest, quarkus-rest-jackson (no Quarkus Security — patterns are hand-rolled)
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
podman compose down -v
```
