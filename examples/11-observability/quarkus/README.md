# Example 11 — Observability (Quarkus)

Quarkus 3.33.2 LTS implementation demonstrating distributed tracing, custom metrics, and correlated logging.

## Services

**inventory-service** (gRPC server on port 9000)
- Implements `Inventory.ReserveStock` RPC
- In-memory stock tracking with ConcurrentHashMap
- Custom Micrometer metric: `stock.reservations` counter (by sku, confirmed)
- OTel traces exported via gRPC to the LGTM collector

**order-service** (HTTP on port 8080)
- REST endpoints: `POST /orders`, `GET /healthz`
- gRPC client calling inventory-service for stock reservation
- Kafka producer publishing to `order.placed` topic
- Custom Micrometer metric: `orders.placed` counter (by sku, status)
- Correlated logging: `trace_id` injected into log output via MDC
- OTel traces + Micrometer metrics exported to the LGTM collector

**notification-consumer** (headless — no HTTP server)
- Consumes `order.placed` events from Kafka
- Inserts notification records into PostgreSQL
- OTel traces propagated across Kafka consumer

## Stack

- Quarkus 3.33.2 LTS
- UBI10 + OpenJDK 25
- PostgreSQL (orders, notifications tables)
- Kafka (order.placed topic)
- LGTM observability stack (Grafana, Tempo, Prometheus, Loki)
- Micrometer OTLP registry (Quarkiverse) for metrics push

## Running

```bash
# Start all services
podman compose up --build

# Test health
curl http://localhost:8080/healthz

# Place an order
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{"sku":"widget-a","quantity":2}'

# Check correlated logs (trace_id in output)
podman logs cndp-order-service 2>&1 | grep "order placed"

# Query traces in Tempo
curl -s http://localhost:3200/api/search | jq '.traces[:3]'

# Query metrics in Prometheus
curl -s 'http://localhost:9090/api/v1/query?query=orders_placed_total' | jq '.data.result'
curl -s 'http://localhost:9090/api/v1/query?query=stock_reservations_total' | jq '.data.result'

# Grafana UI
open http://localhost:3000

# Cleanup
podman compose down -v
```

## What to observe

1. **Distributed traces**: order-service → inventory-service (gRPC) spans in Tempo
2. **Trace propagation**: trace context flows across Kafka to notification-consumer
3. **Correlated logging**: `trace_id=<32-hex>` in order-service log lines
4. **Custom metrics**: `orders_placed_total` and `stock_reservations_total` in Prometheus
5. **LGTM integration**: traces in Tempo, metrics in Prometheus, logs in Loki

## Quarkus-specific features

- **OTel traces via Vert.x gRPC sender**: `quarkus-opentelemetry` uses native Vert.x transport (port 4317)
- **Micrometer OTLP push**: Quarkiverse `quarkus-micrometer-registry-otlp` pushes metrics via HTTP (port 4318)
- **MDC trace correlation**: `Span.current().getSpanContext().getTraceId()` + `MDC.put("trace_id", ...)`
- **Mutiny reactive gRPC**: `Uni<ReserveReply>` return type with `.await().atMost(Duration)`
- **Fast-jar layout**: `target/quarkus-app/` with separated dependencies
