# Example 21 — Graceful Shutdown (Quarkus)

SIGTERM handling — drain in-flight requests, stop accepting new ones, close DB connections, exit cleanly.

## Framework & libraries

- **Framework**: Quarkus 3.40.1 LTS (RESTEasy Reactive, Agroal)
- **Libraries**: quarkus-rest, quarkus-rest-jackson, quarkus-jdbc-postgresql, quarkus-agroal
- **Container base**: `registry.access.redhat.com/ubi10/openjdk-25:1.24-15` (build), `registry.access.redhat.com/ubi10/openjdk-25-runtime:1.24-15` (runtime)

## Run

```bash
docker compose up -d --build --wait
```

Wait for healthy, then verify from the example root:

```bash
cd .. && ./verify.sh
```

## Project structure

| Path | Description |
|------|-------------|
| `order-service/SignalHandler.java` | Registers a `sun.misc.Signal` handler on `StartupEvent` that replaces the JVM default SIGTERM handler, flips readiness, waits `DRAIN_DELAY_SECONDS` (default 5), then calls `Quarkus.asyncExit(0)` |
| `order-service/ShutdownState.java` | CDI `@ApplicationScoped` bean tracking `shuttingDown` flag and `inFlight` counter via atomics |
| `order-service/OrderResource.java` | REST API — `/healthz`, `/readyz` (flips to 503 on SIGTERM), `/orders`, `/debug/state` |

## SIGTERM behavior

1. `docker kill --signal SIGTERM cndp-order-service` fires
2. `SignalHandler` catches SIGTERM, calls `shutdownState.markShuttingDown()`
3. `/readyz` immediately returns 503 — the load balancer (or Kubernetes kubelet) stops routing new traffic
4. The service keeps serving for `DRAIN_DELAY_SECONDS` (default 5) so endpoints update
5. The handler calls `Quarkus.asyncExit(0)`: Quarkus stops accepting connections, waits for in-flight requests (`quarkus.shutdown.timeout=20s`), closes the pool and exits 0, inside the 30 s `stop_grace_period`

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`QUARKUS_DATASOURCE_JDBC_URL, QUARKUS_DATASOURCE_USERNAME, QUARKUS_DATASOURCE_PASSWORD, DRAIN_DELAY_SECONDS`

## Local development (without containers)

Requires JDK 25+, Maven.

```bash
mvn quarkus:dev
```

Requires a running Postgres — see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
