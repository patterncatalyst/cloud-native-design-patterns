# Example 06 — Stream Processing (Quarkus)

Quarkus 3.40.1 LTS implementation demonstrating windowed stream aggregation with Kafka.

## Services

**order-service** (HTTP on port 8080)
- REST endpoints: `POST /orders`, `GET /orders`, `GET /healthz`
- Accepts orders with `merchant_id`, `sku`, `quantity`, `total`
- Publishes `order.placed` events to Kafka
- PostgreSQL persistence via Agroal connection pool

**stream-processor** (headless — no HTTP server)
- Kafka Streams topology (`quarkus-kafka-streams`) over `order.placed`
- Tumbling-window aggregation of revenue by merchant (`TimeWindows`, record timestamps)
- Emits aggregated results to `revenue.by-merchant` topic
- Configurable window size via `WINDOW_SECONDS` (default: 10)

## Stack

- Quarkus 3.40.1 LTS
- UBI10 + OpenJDK 25
- PostgreSQL (orders table)
- Kafka (order.placed, revenue.by-merchant topics)
- LGTM observability stack

## Running

```bash
# Start all services
docker compose up --build

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
docker exec cndp-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic revenue.by-merchant \
  --from-beginning

# Cleanup
docker compose down -v
```

## What to observe

1. **Windowed aggregation**: orders are grouped by merchant within time windows
2. **Revenue rollup**: each window emits `order_count` and `total_revenue` per merchant
3. **Configurable window**: `WINDOW_SECONDS` controls the aggregation interval
4. **Updating results**: each update to a (merchant, window) row is emitted (commit interval 1 s), so a window produces a running total that settles when it closes; consumers keep the latest record per `merchant_id` and `window_start`

## Quarkus-specific features

- **`quarkus-kafka-streams`**: the `Topology` is a CDI-produced bean (`RevenueTopology`); `application.id` is `stream-processor`, which is also the consumer group
- **Windowed KTable**: `groupByKey().windowedBy(TimeWindows.ofSizeWithNoGrace(...)).aggregate(...)` with a Jackson-based `ObjectMapperSerde` for the accumulator
- **Topic bootstrap**: the producer method creates `order.placed` and `revenue.by-merchant` with an `Admin` client, because Kafka Streams refuses to start when a source topic is missing
- **Fast-jar layout**: `target/quarkus-app/` with separated dependencies
