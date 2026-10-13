# Example 12 — Security (.NET)

Three security patterns — sidecar trust (mTLS header check), valet key (HMAC-signed time-bound tokens), and per-tenant bulkhead.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10.0.12) minimal API
- **Libraries**: ASP.NET Core and System.Threading.RateLimiting (in the box) for the bulkhead; the sidecar-trust and valet-key patterns are written in the service
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
| `OrderService/` | Program.cs — middleware pipeline with sidecar trust check, HMAC valet key, partitioned concurrency-limiter bulkhead |

## Implementation notes

All three patterns in one `Program.cs`. The per-tenant bulkhead is a `PartitionedRateLimiter` with one `ConcurrencyLimiter` per tenant (5 permits, no queue); a full pool answers 429. No external packages required.

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
