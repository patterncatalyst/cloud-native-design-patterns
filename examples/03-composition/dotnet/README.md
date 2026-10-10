# Example 03 — Composition (.NET)

API gateway pattern — BFF gateway aggregating order-api and inventory-service via GraphQL + gRPC.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10.0.12) minimal API
- **Libraries**: HotChocolate.AspNetCore (GraphQL), Grpc.Net.Client, Google.Protobuf
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
| `Gateway/` | Program.cs — HotChocolate GraphQL gateway calling order-api and inventory via gRPC |
| `OrderApi/` | Program.cs — REST order service with Npgsql |
| `InventoryService/` | Program.cs — gRPC inventory service |

## Implementation notes

Gateway uses HotChocolate code-first GraphQL with resolvers that aggregate from both backends.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`ORDER_API_URL, INVENTORY_GRPC_HOST`

## Local development (without containers)

Requires the .NET 10 SDK (10.0.12).

```bash
dotnet run --project Gateway
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
