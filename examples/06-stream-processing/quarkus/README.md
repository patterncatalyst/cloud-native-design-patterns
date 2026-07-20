# Example 06 — Stream Processing (Quarkus)

Quarkus 3.33.2 LTS implementation demonstrating windowed stream aggregation with Kafka.

## Services

**order-service** (HTTP on port 8080)
- REST endpoints: `POST /orders`, `GET /orders`, `GET /healthz`
- Accepts orders with `merchant_id`, `sku`, `quantity`, `total`
- Publishes `order.placed` events to Kafka
- PostgreSQL persistence via Agroal connection pool

**stream-processor** (headless — no HTTP server)
- Consumes `order.placed` events from Kafka
- Performs windowed aggregation of revenue by merchant
- Emits aggregated results to `revenue.by-merchant` topic
- Configurable window size via `WINDOW_SECONDS` (default: 10)

## Stack

- Quarkus 3.33.2 LTS
- UBI10 + OpenJDK 25
- PostgreSQL (orders table)
- Kafka (order.placed, revenue.by-merchant topics)
- LGTM observability stack

## Running

```bash
# Start all services
podman compose up --build

# Test health
curl http://localhost:8080/healthz

# Place orders for different merchants
for i in 1 2 3; do
  curl -X POST http://localhost:8080/orders \
    -H "Content-Type: application/json" \
    -d "{\"merchant_id\":\"merchant-a\",\"sku\":\"item-$i\",\"quantity\":1,\"total\":29.99}"
done

# Place orders for another merchant
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{"merchant_id":"merchant-b","sku":"item-x","quantity":2,"total":49.99}'

# Wait for window to flush, then check aggregated output
podman exec cndp-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic revenue.by-merchant \
  --from-beginning

# Cleanup
podman compose down -v
```

## What to observe

1. **Windowed aggregation**: orders are grouped by merchant within time windows
2. **Revenue rollup**: each window emits `order_count` and `total_revenue` per merchant
3. **Configurable window**: `WINDOW_SECONDS` controls the aggregation interval
4. **Automatic flush**: expired windows flush on a 1-second schedule; remaining windows flush on shutdown

## Quarkus-specific features

- **SmallRye Reactive Messaging**: `@Incoming` for consumption, `@Channel` + `Emitter` for emission
- **`@Scheduled` timer**: periodic window flush via `quarkus-scheduler`
- **`@PreDestroy` hook**: flushes remaining windows on graceful shutdown
- **ConcurrentHashMap**: thread-safe windowed accumulation without Kafka Streams
- **Fast-jar layout**: `target/quarkus-app/` with separated dependencies
