# Example 27 — Feature Flags (.NET)

OpenFeature SDK with flagd provider — runtime feature toggles without redeployment.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) minimal API
- **Libraries**: OpenFeature, OpenFeature.Contrib.Providers.Flagd
- **Container base**: registry.access.redhat.com/ubi9/dotnet-100-aspnet (runtime)

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
| `FlagService/` | Program.cs — minimal API evaluating feature flags via OpenFeature .NET SDK with flagd provider |

## Implementation notes

Uses `OpenFeature.Api.Instance` to get a client, evaluates flags per-request. flagd runs as a sidecar container.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`FLAGD_HOST, FLAGD_PORT`

## Local development (without containers)

Requires .NET 10 SDK.

```bash
dotnet run --project FlagService
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
