# Example 01 — Cloud-Native Principles (Quarkus)

Twelve-factor env-based config and liveness/readiness probes.

## Framework & libraries

- **Framework**: Quarkus 3.33 LTS (RESTEasy Reactive, Agroal)
- **Libraries**: quarkus-rest, quarkus-jdbc-postgresql, quarkus-opentelemetry
- **Container base**: registry.access.redhat.com/ubi10/openjdk-25-runtime

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
| `OrderResource.java` | JAX-RS endpoints for order CRUD |
| `HealthResource.java` | Probe endpoints (`/healthz`, `/readyz`, `/`) |

## Implementation notes

Uses `AgroalDataSource` (via `javax.sql.DataSource` injection) for JDBC.
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
podman compose down -v
```
