# Example 05 — Event-Driven Architecture (Quarkus)

Quarkus 3.33.2 LTS implementation demonstrating event-driven microservices with Kafka.

## Services

**order-service** (HTTP on port 8080)
- REST endpoints: `POST /orders`, `GET /orders`, `GET /healthz`
- Publishes `order.placed` events to Kafka
- PostgreSQL persistence via Agroal connection pool

**shipping-consumer** (headless — no HTTP server)
- Consumes `order.placed` events from Kafka (group: `shipping-group`)
- Inserts shipment records into PostgreSQL
- Idempotent consumer: catches unique-constraint violations on `order_id`

**notification-consumer** (headless — no HTTP server)
- Consumes `order.placed` events from Kafka (group: `notification-group`)
- Inserts notification records into PostgreSQL
- Idempotent consumer: same duplicate-guard pattern

## Stack

- Quarkus 3.33.2 LTS
- UBI10 + OpenJDK 25
- PostgreSQL (orders, shipments, notifications tables)
- Kafka (order.placed topic)
- LGTM observability stack

## Running

```bash
# Start all services
podman compose up --build

# Test health
curl http://localhost:8080/healthz

# Place an order
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{"sku":"widget-a","quantity":3}'

# List orders
curl http://localhost:8080/orders

# Check shipment was created
podman exec cndp-postgres psql -U appuser -d appdb \
  -c "SELECT * FROM shipments"

# Check notification was created
podman exec cndp-postgres psql -U appuser -d appdb \
  -c "SELECT * FROM notifications"

# Verify Kafka consumer groups
podman exec cndp-kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --list

# Cleanup
podman compose down -v
```

## What to observe

1. **Fan-out pattern**: one `order.placed` event consumed by two independent consumer groups
2. **Idempotency**: re-processing the same event does not create duplicate records
3. **Headless consumers**: shipping and notification services run without HTTP servers (`quarkus.http.host-enabled=false`)
4. **Async decoupling**: order-service does not know about downstream consumers
5. **OpenTelemetry traces**: distributed trace propagation across Kafka producer/consumer

## Quarkus-specific features

- **SmallRye Reactive Messaging**: `@Incoming("channel")` for consumers, `@Channel` + `Emitter<String>` for producers
- **Headless mode**: `quarkus.http.host-enabled=false` disables the HTTP server entirely
- **AgroalDataSource**: CDI-injected JDBC connection pool
- **Fast-jar layout**: `target/quarkus-app/` with separated dependencies
