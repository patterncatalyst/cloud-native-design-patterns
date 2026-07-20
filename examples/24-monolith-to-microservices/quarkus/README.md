# Example 24 — Monolith to Microservices (Quarkus)

Quarkus 3.33.2 LTS implementation demonstrating Strangler Fig pattern with content-based routing and decorating collaborator.

## Services

**monolith** (HTTP on port 8080, internal only)
- Stub service handling legacy tenant traffic
- Shared stub-service code with SERVICE_NAME=monolith

**new-service** (HTTP on port 8080, internal only)
- Stub service handling migrated tenant traffic
- Shared stub-service code with SERVICE_NAME=new-service

**legacy** (HTTP on port 8080, internal only)
- Stub service being wrapped by decorator
- Shared stub-service code with SERVICE_NAME=legacy

**router** (HTTP on port 8080)
- Content-based router dispatching by tenant
- Dynamic routing rules via PUT /rules
- Initial routing: acme→new-service, others→monolith

**decorator** (HTTP on port 8091)
- Wraps legacy service with Redis cache + Kafka events
- 60-second cache TTL for GET requests
- Publishes order.placed events on POST /orders

## Stack

- Quarkus 3.33.2 LTS
- UBI10 + OpenJDK 25
- Redis (order caching)
- Kafka (order.placed topic)

## Running

```bash
# Start all services
podman compose up --build

# Test router health
curl http://localhost:8080/healthz

# Test tenant routing (acme → new-service)
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{"sku":"widget","quantity":1,"tenant":"acme"}'

# Test default routing (other → monolith)
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{"sku":"widget","quantity":1,"tenant":"other"}'

# Check routing rules
curl http://localhost:8080/rules

# Update routing (flip acme to monolith)
curl -X PUT http://localhost:8080/rules \
  -H "Content-Type: application/json" \
  -d '{"tenant_routes":{"acme":"monolith"},"default":"monolith"}'

# Test decorator (creates order via legacy, caches result)
curl -X POST http://localhost:8091/orders \
  -H "Content-Type: application/json" \
  -d '{"sku":"cached-item","quantity":2}'

# Get cached order (check logs for CACHE_HIT/CACHE_MISS)
curl http://localhost:8091/orders/1

# View published events
curl http://localhost:8091/events

# Cleanup
podman compose down -v
```

## What to observe

1. **Content-based routing**: tenant field determines backend (new-service vs monolith)
2. **Dynamic rules**: PUT /rules flips routing without redeployment
3. **Redis caching**: second GET served from cache (legacy sees 1 request, not 2)
4. **Kafka events**: decorator publishes order.placed on POST, transparent to legacy
5. **Strangler Fig**: legacy service untouched, new behavior layered via decorator
6. **CACHE_HIT/CACHE_MISS** in decorator logs, absent from legacy logs

## Quarkus-specific features

- **java.net.http.HttpClient**: Lightweight HTTP proxy in router/decorator (no RestClient needed)
- **Redis ValueCommands**: `io.quarkus.redis.datasource.value.ValueCommands` with `setex` for TTL
- **SmallRye Emitter**: `@Channel` + `Emitter<String>` for non-blocking Kafka publish
- **Shared stub JAR**: Single stub-service artifact differentiated via SERVICE_NAME env var
- **Fast-jar layout**: `target/quarkus-app/` with separated dependencies
