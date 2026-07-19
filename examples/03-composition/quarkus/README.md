# Example 03: API Composition Pattern (Quarkus)

This example demonstrates the API Composition pattern with three services communicating via REST and gRPC, composed through a GraphQL gateway with DataLoader batching.

## Architecture

- **gateway** (port 8080): GraphQL API that composes data from order-api (REST) and inventory (gRPC)
- **order-api** (port 8081): REST service reading orders from PostgreSQL
- **inventory-service** (gRPC port 9000): In-memory inventory with batch stock lookup

## What to observe

1. **GraphQL composition**: Query orders with optional stock field resolution
2. **DataLoader batching**: Single gRPC call for multiple SKUs (N+1 prevention)
3. **Multi-protocol integration**: REST + gRPC composed through GraphQL

## Running

```bash
# Start the stack
podman compose up --build

# Wait for services to be ready (check logs)
podman logs -f cndp-gateway

# In another terminal, run tests
../verify.sh
```

## Example queries

```bash
# Health check
curl http://localhost:8080/healthz

# GraphQL without stock (no inventory call)
curl -X POST http://localhost:8080/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ orders(limit: 3) { id sku quantity status } }"}'

# GraphQL with stock (triggers batched gRPC call)
curl -X POST http://localhost:8080/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ orders(limit: 3) { id sku quantity status stock } }"}'

# Single order by ID
curl -X POST http://localhost:8080/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ order(id: \"ord-001\") { id sku quantity status stock } }"}'
```

## GraphiQL UI

Open http://localhost:8080/q/graphql-ui in your browser for interactive queries.

## Observability

- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- View traces across all three services in Tempo

## Cleanup

```bash
podman compose down -v
```
