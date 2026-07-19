# Example 26 — Failure Modes (Quarkus)

Circuit breaker, retry with backoff, timeout, and fallback — edge-service calling an unreliable backend.

## Framework & libraries

- **Framework**: Quarkus 3.33.2 (REST + Jackson)
- **Libraries**: quarkus-rest, quarkus-rest-jackson, java.net.http.HttpClient (JDK)
- **Container base**: UBI10/openjdk-25

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
| `edge-service/` | EdgeResource.java — resilience patterns calling backend |
| `backend-service/` | BackendResource.java — configurable failure injection |

## Implementation notes

Resilience patterns hand-rolled (no SmallRye Fault Tolerance) to show the mechanics explicitly. Circuit breaker uses `AtomicReference<State>`. HTTP client uses JDK stdlib `java.net.http.HttpClient`.

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
podman compose down -v
```
