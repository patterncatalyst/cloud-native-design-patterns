# Example 12 — Security (Quarkus)

Three security patterns — sidecar trust (mTLS header check), valet key (HMAC-signed time-bound tokens), and per-tenant bulkhead.

## Framework & libraries

- **Framework**: Quarkus 3.40.1 LTS (RESTEasy Reactive + Jackson)
- **Libraries**: quarkus-rest, quarkus-rest-jackson, quarkus-smallrye-fault-tolerance for the bulkhead (no Quarkus Security: the sidecar-trust and valet-key patterns are written in the service)
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
| `order-service/` | SidecarTrustFilter.java — JAX-RS ContainerRequestFilter; ValetKeyService.java — HMAC signing; BulkheadService.java — one SmallRye Fault Tolerance guard per tenant |

## Implementation notes

Each pattern is a separate class. SidecarTrustFilter is a @PreMatching ContainerRequestFilter that rejects requests without mTLS client cert header. The bulkhead is one SmallRye Fault Tolerance `Guard` per tenant (the programmatic API, since an annotation cannot be keyed by tenant), 5 concurrent calls and no queue; a full pool answers 429.

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
