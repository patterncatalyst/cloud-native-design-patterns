# Example 19 — DDD & Hexagonal Architecture (.NET)

Hexagonal (ports-and-adapters) architecture — domain logic isolated from infrastructure with explicit port interfaces.

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10.0.12) minimal API
- **Libraries**: Npgsql
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
| `OrderService/` | Program.cs — composition root and minimal API driving adapter; `Domain/` (entities, ports, use case); `Adapters/` (Npgsql repository, log publisher) |
| `OrderService/Adapters/CliPlaceOrder.cs` | CLI driving adapter — `OrderService place-order <sku> <qty>`, handled before the web host is built; calls `PlaceOrderUseCase`, never the repository |
| `cli-place-order` | Wrapper installed on PATH in the image: `cli-place-order <sku> <qty>` |

## Implementation notes

Explicit interface boundaries: C# interfaces for ports, DI registration for adapter binding. The CLI adapter proves replaceability:

```bash
docker exec cndp-order-service cli-place-order bolt-x 5
```

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`DATABASE_URL`

## Local development (without containers)

Requires the .NET 10 SDK (10.0.12).

```bash
dotnet run --project OrderService
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
