# Example 27 — Feature Flags (Quarkus)

OpenFeature SDK with flagd provider — runtime feature toggles without redeployment.

## Framework & libraries

- **Framework**: Quarkus 3.33.2 (REST + Jackson)
- **Libraries**: OpenFeature Java SDK, flagd provider
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
| `flag-service/` | FlagResource.java — JAX-RS API checking feature flags via OpenFeature; OpenFeatureSetup.java — OpenFeature client setup with flagd provider |

## Implementation notes

Uses `dev.openfeature:sdk` and `dev.openfeature.contrib.providers:flagd` as plain Maven dependencies (not Quarkus extensions). Flag evaluation in request handlers — no custom annotation magic.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`flagd.host, flagd.port`

## Local development (without containers)

Requires JDK 25+, Maven (wrapper included).

```bash
./mvnw quarkus:dev
```

Requires a running flagd — see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
