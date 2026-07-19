# Example 21 — Graceful Shutdown (Quarkus)

SIGTERM handling — drain in-flight requests, stop accepting new ones, close DB connections, exit cleanly.

## Framework & libraries

- **Framework**: Quarkus 3.33 LTS (RESTEasy Reactive, Agroal)
- **Libraries**: quarkus-rest, quarkus-rest-jackson, quarkus-jdbc-postgresql, quarkus-agroal
- **Container base**: UBI10 / OpenJDK 25

## Run

```bash
podman compose up --build -d
```

Wait for healthy, then verify from the example root:

```bash
cd .. && COMPOSE_FILE=quarkus/compose.yaml bash verify.sh
```

## Project structure

| Path | Description |
|------|-------------|
| `order-service/SignalHandler.java` | Registers a `sun.misc.Signal` handler on `StartupEvent` that replaces the JVM default SIGTERM handler — the process stays alive after SIGTERM |
| `order-service/ShutdownState.java` | CDI `@ApplicationScoped` bean tracking `shuttingDown` flag and `inFlight` counter via atomics |
| `order-service/OrderResource.java` | REST API — `/healthz`, `/readyz` (flips to 503 on SIGTERM), `/orders`, `/debug/state` |

## SIGTERM behavior

1. `podman kill --signal SIGTERM cndp-order-service` fires
2. `SignalHandler` catches SIGTERM, calls `shutdownState.markShuttingDown()`
3. `/readyz` immediately returns 503 — the load balancer (or Kubernetes kubelet) stops routing new traffic
4. In-flight requests finish normally (tracked by the `inFlight` counter)
5. The process remains alive until `podman stop` sends SIGKILL after `stop_grace_period` (30 s)

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`QUARKUS_DATASOURCE_JDBC_URL, QUARKUS_DATASOURCE_USERNAME, QUARKUS_DATASOURCE_PASSWORD`

## Local development (without containers)

Requires JDK 25+, Maven.

```bash
mvn quarkus:dev
```

Requires a running Postgres — see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
