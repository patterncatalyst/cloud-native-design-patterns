# Example 27 — Feature Flags (Spring Boot)

OpenFeature SDK with flagd provider — runtime feature toggles without redeployment.

## Framework & libraries

- **Framework**: Spring Boot 4.1.1, Java 25 (Web)
- **Libraries**: spring-boot-starter-webmvc, OpenFeature Java SDK, flagd provider
- **Container base**: `ubi10/openjdk-25-runtime:1.24-15` (UID 185)

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
| `flag-service/` | FlagController.java — REST API checking feature flags via OpenFeature; FlagConfig.java — OpenFeature client setup with flagd provider |

## Implementation notes

Uses `dev.openfeature:sdk` and `dev.openfeature.contrib.providers:flagd`. Flag evaluation in request handlers — no custom annotation magic.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`flagd.host, flagd.port`

## Local development (without containers)

Requires JDK 25 and Maven 3.9+.

```bash
mvn spring-boot:run
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
