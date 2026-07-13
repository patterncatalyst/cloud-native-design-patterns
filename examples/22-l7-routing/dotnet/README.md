# Example 22 — L7 Routing (.NET)

Two-part routing — Envoy weighted splits (90/10 + header override) and in-app rule-driven routing (VIP orders to priority topic).

## Framework & libraries

- **Framework**: ASP.NET Core (.NET 10) minimal API
- **Libraries**: None beyond ASP.NET Core
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
| `OrderService/` | Program.cs — backend API |
| `RouterService/` | Program.cs — rule-based routing |

## Implementation notes

Two minimal API projects. Envoy handles infrastructure routing; RouterService handles application routing. No Kafka client needed — routing decision is demonstrated via HTTP response.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`KAFKA_BOOTSTRAP`

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
