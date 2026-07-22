# Example 19: DDD & Hexagonal Architecture (C++)

Demonstrates **ports-and-adapters architecture** with strict domain isolation.
The domain layer has ZERO framework imports — it depends only on pure C++
interfaces (ports). Two driving adapters (REST and CLI) prove the architecture
is replaceable.

## Architecture

```
src/
  domain/                   # CORE — pure C++, zero framework imports
    models.hpp              # Order, OrderPlaced (entities & events)
    ports.hpp               # OrderRepository, EventPublisher (interfaces)
    service.hpp             # PlaceOrderUseCase (orchestrates domain logic)
  
  adapters/                 # PERIPHERY — implements ports, drives use cases
    pg_repository.hpp       # PostgreSQL implementation of OrderRepository
    log_publisher.hpp       # Logging implementation of EventPublisher
    rest_adapter.cpp        # Drogon HTTP handlers (driving adapter)
  
  main.cpp                  # REST composition root — wires adapters to ports
  cli_main.cpp              # CLI composition root — same use case, different driver
  pg_pool.hpp               # Infrastructure (connection pool)
```

## Key cross-check: domain isolation

The verify.sh script ensures the domain layer has **zero framework imports**:
- No `#include <drogon/...>`
- No `#include <libpq-fe.h>`
- No `#include <spdlog/...>`

The domain layer depends ONLY on its own types and standard C++. Adapters
implement the ports (interfaces) defined by the domain.

## Running

```bash
# From examples/19-ddd-hexagonal/cpp/
podman compose up --build

# Test the REST adapter
curl http://localhost:8080/orders -X POST -H 'Content-Type: application/json' \
    -d '{"sku":"widget-a","quantity":3}'

# Test the CLI adapter (same use case, different entry point)
podman exec cndp-order-service python cli_place_order.py bolt-x 5
```

## Verification

```bash
cd ..
./verify.sh
```

Expected: all checks pass, proving:
1. Domain layer has zero framework imports
2. REST adapter works (POST, GET)
3. CLI adapter works (proving replaceability)
4. Domain events are published
