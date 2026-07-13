# Example 12 — Security (.NET)

Three security patterns — sidecar trust (mTLS header check), valet key (HMAC-signed time-bound tokens), and per-tenant bulkhead.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) minimal API
- **Libraries**: None beyond ASP.NET Core (patterns are hand-rolled)
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
| `OrderService/` | Program.cs — middleware pipeline with sidecar trust check, HMAC valet key, SemaphoreSlim bulkhead |

## Implementation notes

All three patterns in one `Program.cs`. Uses `SemaphoreSlim` for per-tenant bulkhead. No external packages required.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`HMAC_SECRET`

## Local development (without containers)

Requires .NET 10 SDK.

```bash
dotnet run --project OrderService
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
