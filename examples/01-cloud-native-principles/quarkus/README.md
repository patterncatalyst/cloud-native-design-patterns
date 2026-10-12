# Example 01 — Cloud-Native Principles (Quarkus)

Twelve-factor env-based config and liveness/readiness probes.

## Framework & libraries

- **Framework**: Quarkus 3.40.1 LTS (Quarkus REST, Hibernate ORM with Panache, SmallRye Health)
- **Libraries**: quarkus-rest, quarkus-jdbc-postgresql, quarkus-opentelemetry
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
| `OrderResource.java` | JAX-RS endpoints for order CRUD |
| `Order.java` | Panache entity over the shared `orders` table; `OrderDto` is the response shape |

The probes (`/healthz`, `/readyz`) come from SmallRye Health; readiness includes the datasource check.

## Implementation notes

Uses Hibernate ORM with Panache over the schema in `db/init` (`quarkus.hibernate-orm.schema-management.strategy=validate`).
Config in `application.properties` with `${ENV_VAR:default}` syntax.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`QUARKUS_DATASOURCE_JDBC_URL, OTEL_EXPORTER_OTLP_ENDPOINT, SERVICE_VERSION`

## Local development (without containers)

Requires JDK 25+, Maven.

```bash
mvn quarkus:dev
```

Requires a running Postgres — see the compose.yaml `depends_on` for which
infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
