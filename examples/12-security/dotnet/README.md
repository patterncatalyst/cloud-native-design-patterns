# Example 12 — Security (.NET)

Three security patterns — sidecar trust (mTLS header check), valet key (HMAC-signed time-bound tokens), and per-tenant bulkhead.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10.0.12) minimal API
- **Libraries**: None beyond ASP.NET Core (patterns are hand-rolled)
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
| `OrderService/` | Program.cs — middleware pipeline with sidecar trust check, HMAC valet key, SemaphoreSlim bulkhead |

## Implementation notes

All three patterns in one `Program.cs`. Uses `SemaphoreSlim` for per-tenant bulkhead. No external packages required.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`HMAC_SECRET`

## Local development (without containers)

Requires the .NET 10 SDK (10.0.112, runtime 10.0.12).

```bash
dotnet run --project OrderService
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
