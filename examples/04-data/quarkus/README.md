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
docker compose up -d --build --wait

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

# Read the topic from inside the broker container
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:9094 --topic order.placed --from-beginning --timeout-ms 5000
# or, from the host with kcat: kcat -b localhost:9092 -t order.placed -C -e
```

## Observe

- **Kafka topic**: `kafka-console-consumer.sh` inside the `kafka` container (or `kcat -b localhost:9092 -t order.placed -C -e`) → see `order.placed` events
- **Grafana**: http://localhost:3000 → traces, logs, metrics
- **Kafka Connect**: http://localhost:8083/connectors → see `outbox-connector` status

## Clean up

```bash
docker compose down -v
```

## Key files

- `order-service/src/main/java/com/cndp/order/OrderResource.java` → REST endpoints, transactional outbox write
- `order-service/src/main/resources/application.properties` → Quarkus config
- `../db/init/01-schema.sql` → Database schema with outbox publication
- `../debezium/register-connector.sh` → Debezium connector registration
