# Example 03 — Composition (.NET)

API gateway pattern — BFF gateway aggregating order-api and inventory-service via GraphQL + gRPC.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) minimal API
- **Libraries**: HotChocolate.AspNetCore (GraphQL), Grpc.Net.Client, Google.Protobuf
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
| `Gateway/` | Program.cs — HotChocolate GraphQL gateway calling order-api and inventory via gRPC |
| `OrderApi/` | Program.cs — REST order service with Npgsql |
| `InventoryService/` | Program.cs — gRPC inventory service |

## Implementation notes

Gateway uses HotChocolate code-first GraphQL with resolvers that aggregate from both backends.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`ORDER_API_URL, INVENTORY_GRPC_HOST`

## Local development (without containers)

Requires .NET 10 SDK.

```bash
dotnet run --project Gateway
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
