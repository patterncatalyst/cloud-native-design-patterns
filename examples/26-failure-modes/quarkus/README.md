# Example 26 — Failure Modes (Quarkus)

Circuit breaker, retry with backoff, timeout, and fallback — edge-service calling an unreliable backend.

## Framework & libraries

- **Framework**: Quarkus 3.40.1 LTS (REST + Jackson)
- **Libraries**: quarkus-rest, quarkus-rest-jackson, quarkus-rest-client-jackson, quarkus-smallrye-health
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
| `edge-service/` | EdgeResource.java — resilience patterns calling backend |
| `backend-service/` | BackendResource.java — configurable failure injection |

## Implementation notes

Resilience patterns hand-rolled (no SmallRye Fault Tolerance) to show the mechanics explicitly. Circuit breaker uses `AtomicReference<State>`. The backend is called through a typed Quarkus REST Client (`BackendClient`).

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`BACKEND_URL`

## Local development (without containers)

Requires JDK 25+, Maven.

```bash
mvn quarkus:dev
```

## Tear down

```bash
docker compose down -v
```
