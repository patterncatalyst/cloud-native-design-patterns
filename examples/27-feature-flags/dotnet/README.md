# Example 27 — Feature Flags (.NET)

OpenFeature SDK with flagd provider — runtime feature toggles without redeployment.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10.0.12) minimal API
- **Libraries**: OpenFeature, OpenFeature.Contrib.Providers.Flagd
- **Container base**: registry.access.redhat.com/ubi9/dotnet-100-aspnet:9.8-1791363520 (runtime), built with ubi9/dotnet-100:9.8-1791421718; runs as UID 1001

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
| `FlagService/` | Program.cs — minimal API evaluating feature flags via OpenFeature .NET SDK with flagd provider |

## Implementation notes

Uses `OpenFeature.Api.Instance` to get a client, evaluates flags per-request. flagd runs as a sidecar container.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`FLAGD_HOST, FLAGD_PORT`

## Local development (without containers)

Requires the .NET 10 SDK (10.0.112, runtime 10.0.12).

```bash
dotnet run --project FlagService
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
