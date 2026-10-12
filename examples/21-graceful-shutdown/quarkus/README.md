# Example 21 — Graceful Shutdown (Quarkus)

SIGTERM handling — drain in-flight requests, stop accepting new ones, close DB connections, exit cleanly.

## Framework & libraries

- **Framework**: Quarkus 3.40.1 LTS (Quarkus REST, Hibernate ORM with Panache, SmallRye Health)
- **Libraries**: quarkus-rest, quarkus-rest-jackson, quarkus-jdbc-postgresql, quarkus-hibernate-orm-panache, quarkus-smallrye-health
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
| `order-service/ShutdownState.java` | CDI `@ApplicationScoped` bean: observes `ShutdownDelayInitiatedEvent` (flips the `shuttingDown` flag) and `ShutdownEvent`, and counts `inFlight` requests |
| `order-service/DrainReadinessCheck.java` | SmallRye Health `@Readiness` check that reports DOWN (`reason: shutting down`) once the drain starts |
| `order-service/OrderEntity.java` | Panache entity over the shared `orders` table |
| `order-service/OrderResource.java` | REST API — `/orders`, `/debug/state` (`/healthz` and `/readyz` come from SmallRye Health) |
| `application.properties` | `quarkus.shutdown.delay-enabled`, `quarkus.shutdown.delay` (`DRAIN_DELAY_SECONDS`, default 5) and `quarkus.shutdown.timeout=20s` |

## SIGTERM behavior

1. `docker kill --signal SIGTERM cndp-order-service` fires
2. Quarkus fires `ShutdownDelayInitiatedEvent`; `ShutdownState` flips the flag
3. `/readyz` immediately returns 503 — the load balancer (or Kubernetes kubelet) stops routing new traffic
4. The service keeps serving for `DRAIN_DELAY_SECONDS` (default 5) so endpoints update
5. When the delay ends Quarkus fires `ShutdownEvent`, stops accepting connections, waits for in-flight requests (`quarkus.shutdown.timeout=20s`), closes the pool and exits, inside the 30 s `stop_grace_period`

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
