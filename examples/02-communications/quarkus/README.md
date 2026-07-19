# Example 02 — Communications (Quarkus)

Quarkus 3.33.2 LTS implementation demonstrating REST, GraphQL, gRPC, and Kafka.

## Services

**inventory-service** (gRPC server on port 9000)
- Implements `Inventory.ReserveStock` RPC
- In-memory stock tracking with ConcurrentHashMap
- Quarkus gRPC extension with Mutiny reactive streams

**order-service** (HTTP on port 8080)
- REST endpoints: `POST /orders`, `GET /orders` with cursor pagination, `GET /healthz`
- GraphQL API at `/graphql` with GraphiQL UI
- gRPC client calling inventory service
- Kafka producer publishing to `order.placed` topic
- PostgreSQL persistence via Agroal connection pool

## Stack

- Quarkus 3.33.2 LTS
- UBI10 + OpenJDK 25
- PostgreSQL (orders table)
- Kafka (order.placed events)
- LGTM observability stack

## Running

```bash
# Start all services
podman compose up --build

# Test health
curl http://localhost:8080/healthz

# Create an order (succeeds - enough stock)
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{"sku":"laptop","quantity":5}'

# Create an order (fails - insufficient stock)
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{"sku":"scarce","quantity":200}'

# List orders with pagination
curl http://localhost:8080/orders?limit=10

# GraphQL query
curl -X POST http://localhost:8080/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ orders(limit: 5) { id sku quantity status } }"}'

# GraphiQL UI
open http://localhost:8080/q/graphql-ui

# Verify Kafka
podman exec -it cndp-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic order.placed \
  --from-beginning

# Check logs
podman logs cndp-order-service
podman logs cndp-inventory

# Cleanup
podman compose down -v
```

## What to observe

1. **gRPC communication**: order-service calls inventory-service synchronously
2. **Stock reservation logic**: orders with quantity <= 100 confirm; > 100 reject
3. **Kafka events**: every order publishes to `order.placed` topic
4. **Cursor pagination**: `next_cursor` in `/orders` response enables efficient paging
5. **GraphQL introspection**: GraphiQL UI at `/q/graphql-ui`
6. **OpenTelemetry traces**: Grafana → Explore → Tempo (distributed trace across gRPC + Kafka)

## Quarkus-specific features

- **Code-first GraphQL**: `@GraphQLApi` + `@Query` annotations (no schema.graphqls file)
- **Mutiny reactive**: gRPC server extends Mutiny base, returns `Uni<T>`
- **SmallRye Reactive Messaging**: Kafka producer via `@Channel` + `Emitter<String>`
- **Fast-jar layout**: `target/quarkus-app/` with separated dependencies
- **gRPC + HTTP on separate ports**: inventory uses 9000 (gRPC) + 8081 (HTTP health); order uses 8080
