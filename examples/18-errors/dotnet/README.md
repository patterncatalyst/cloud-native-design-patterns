# Example 18 — Errors & Problem Details (.NET)

RFC 9457 Problem Details for REST errors, gRPC status codes with rich error details, and retry-aware error responses.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) minimal API
- **Libraries**: Grpc.Net.Client, Google.Protobuf, Grpc.Tools
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
| `OrderService/` | Program.cs — `Results.Problem()` for RFC 9457 responses; gRPC client with RpcException handling |
| `InventoryService/` | Program.cs — gRPC server throwing `RpcException` with `Metadata` trailers |

## Implementation notes

Uses ASP.NET Core's built-in `Results.Problem()` which produces compliant Problem Details JSON. gRPC errors use `Grpc.Core.RpcException` with status codes.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`INVENTORY_GRPC_HOST`

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
