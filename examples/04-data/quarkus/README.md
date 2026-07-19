# Example 04: Data Layer & Transactional Outbox (Quarkus)

Demonstrates the **Transactional Outbox** pattern with Quarkus + PostgreSQL + Debezium + Kafka.

## What it does

- **POST /orders** → Creates an order in the `orders` table and writes an event to the `outbox` table **atomically** (single transaction)
- **Debezium CDC connector** watches the `outbox` table and publishes events to Kafka topic `order.placed`
- **GET /orders** → Lists all orders from the database
- **GET /outbox** → Lists all outbox events from the database
- **GET /healthz** → Health check endpoint

## Architecture

```
┌─────────────────┐
│ order-service   │
│  (Quarkus)      │
│                 │
│ POST /orders    │──┐
│                 │  │ (1) Write order + outbox in single TX
└─────────────────┘  │
         │           │
         v           v
    ┌────────────────────┐
    │   PostgreSQL       │
    │  ┌──────┐ ┌──────┐│
    │  │orders│ │outbox││  (2) Debezium CDC watches outbox
    │  └──────┘ └──────┘│
    └────────────────────┘
              │
              │ (3) Publish to Kafka
              v
         ┌─────────┐
         │  Kafka  │
         │ topic:  │
         │order.   │
         │placed   │
         └─────────┘
```

## Run it

```bash
cd examples/04-data/quarkus

# Start all services
podman compose up --build -d

# Wait for services to be ready (30-40 seconds)
sleep 30

# Register Debezium connector
../debezium/register-connector.sh

# Verify
../verify.sh
```

## Test manually

```bash
# Health check
curl http://localhost:8080/healthz

# Create an order
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{"sku":"widget-a","quantity":5}'

# List orders
curl http://localhost:8080/orders

# List outbox events
curl http://localhost:8080/outbox

# Check Kafka topic (via Kafka UI)
open http://localhost:8090
# Navigate to Topics → order.placed → Messages
```

## Observe

- **Kafka UI**: http://localhost:8090 → see `order.placed` topic
- **Grafana**: http://localhost:3000 → traces, logs, metrics
- **Kafka Connect**: http://localhost:8083/connectors → see `outbox-connector` status

## Clean up

```bash
podman compose down -v
```

## Key files

- `order-service/src/main/java/com/cndp/order/OrderResource.java` → REST endpoints, transactional outbox write
- `order-service/src/main/resources/application.properties` → Quarkus config
- `../db/init/01-schema.sql` → Database schema with outbox publication
- `../debezium/register-connector.sh` → Debezium connector registration
