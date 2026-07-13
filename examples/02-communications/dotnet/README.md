# Example 02 — Communications (.NET)

Four communication styles — REST, gRPC, async events (Kafka), and GraphQL — in one order+inventory system.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) minimal API
- **Libraries**: HotChocolate.AspNetCore (GraphQL), Confluent.Kafka, Grpc.Net.Client, Google.Protobuf
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
| `OrderService/` | Program.cs — REST + GraphQL + Kafka producer + gRPC client |
| `InventoryService/` | Program.cs — gRPC server |

## Implementation notes

GraphQL via HotChocolate (code-first). gRPC stubs generated via Grpc.Tools at build time from `Protos/inventory.proto`.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL, KAFKA_BOOTSTRAP, INVENTORY_GRPC_HOST`

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
