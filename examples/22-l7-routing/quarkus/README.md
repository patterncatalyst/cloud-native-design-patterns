# Example 22 — L7 Routing & Traffic Management (Quarkus)

Quarkus 3.33.2 LTS implementation demonstrating weighted routing via Envoy and in-app rule-driven routing.

## Services

### order-service
REST API for order management with version identification. Deployed in two instances (v1/v2) behind Envoy for traffic splitting demonstrations.

**Endpoints:**
- `GET /healthz` — Health check with version info
- `POST /orders` — Create order (returns order with version)
- `GET /orders` — List orders (returns empty list with version)

### router-service
Rule-based routing service that classifies orders as VIP or default based on configurable amount thresholds.

**Endpoints:**
- `POST /orders` — Route order to priority or default topic based on amount
- `GET /rules` — View current routing rules
- `PUT /rules` — Update routing rules dynamically
- `GET /healthz` — Health check

### envoy
Envoy proxy providing L7 routing capabilities:
- **Weighted routing**: Distributes traffic between v1 (70%) and v2 (30%) backends
- **Header-based routing**: Routes requests with `x-route-to: v2` header directly to v2

## Stack

- Quarkus 3.33.2 LTS with `quarkus-rest` (Jakarta REST)
- UBI10 base images with OpenJDK 25
- Envoy v1.31 proxy for L7 traffic management
- Multi-stage Docker builds for optimized images

## Running

### Start all services
```bash
podman compose up --build
```

Wait for all healthchecks to pass (Envoy depends on both order service instances being healthy).

### Test weighted routing through Envoy
```bash
# Multiple requests show distribution between v1 and v2
for i in {1..10}; do
  curl -s http://localhost:8080/orders | jq -r .version
done
```

Expected: Mix of "v1" and "v2" responses (approximately 70/30 split over many requests).

### Test header-based routing
```bash
# Force routing to v2
curl -H "x-route-to: v2" http://localhost:8080/orders | jq .version

# Force routing to v1
curl -H "x-route-to: v1" http://localhost:8080/orders | jq .version
```

### Test rule-based routing (router-service)
```bash
# VIP order (amount >= 1000)
curl -X POST http://localhost:8090/orders \
  -H "Content-Type: application/json" \
  -d '{"sku":"laptop","amount":1500}' | jq .

# Expected: {"routed_to":"orders.priority","vip":true,"amount":1500}

# Ordinary order (amount < 1000)
curl -X POST http://localhost:8090/orders \
  -H "Content-Type: application/json" \
  -d '{"sku":"mouse","amount":50}' | jq .

# Expected: {"routed_to":"orders.default","vip":false,"amount":50}
```

### Update routing rules dynamically
```bash
# View current rules
curl http://localhost:8090/rules | jq .

# Lower VIP threshold to 500
curl -X PUT http://localhost:8090/rules \
  -H "Content-Type: application/json" \
  -d '{"vip_threshold":500}' | jq .

# Now amount=750 is VIP
curl -X POST http://localhost:8090/orders \
  -H "Content-Type: application/json" \
  -d '{"sku":"tablet","amount":750}' | jq .

# Expected: {"routed_to":"orders.priority","vip":true,"amount":750}
```

### Create orders through Envoy
```bash
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" \
  -d '{"sku":"keyboard","quantity":2}' | jq .
```

Expected: Response includes `"version":"v1"` or `"version":"v2"` based on weighted distribution.

### Stop services
```bash
podman compose down
```

## What to observe

### Envoy weighted routing
- Traffic is distributed approximately 70% to v1 and 30% to v2 over many requests
- Each response includes the backend version in the `version` field
- Distribution is probabilistic; exact ratios appear over 50+ requests

### Envoy header-based routing
- Requests with `x-route-to: v2` header always go to v2 (100% deterministic)
- Requests with `x-route-to: v1` header always go to v1
- Header routing overrides weighted routing configuration

### Dynamic rule updates
- Router service logs each routing decision with SKU, amount, and destination topic
- Rules can be updated at runtime via PUT /rules without service restart
- Updated thresholds take effect immediately for subsequent requests
- VIP classification changes based on current threshold value

### Service versioning
- Both order service instances return identical API contracts
- Version field in responses allows tracking which backend served the request
- Useful for canary deployments, A/B testing, and gradual rollouts

## Quarkus-specific features

### Jakarta REST (quarkus-rest)
- Uses Quarkus REST (built on Vert.x) for high-performance non-blocking HTTP
- `@Path`, `@GET`, `@POST`, `@PUT` annotations for endpoint mapping
- `@Produces` and `@Consumes` for content negotiation
- `Response.status()` builder for HTTP status codes

### Configuration injection
- `@ConfigProperty` injects `app.version` from application.properties
- Environment variable `APP_VERSION` overrides default at runtime
- Allows same image to run as v1 or v2 based on environment

### Dependency injection
- `@ApplicationScoped` beans (implicit via REST resource)
- Constructor initialization for thread-safe `ConcurrentHashMap` rules
- No need for explicit bean declarations for JAX-RS resources

### Logging
- `org.jboss.logging.Logger` for structured logging
- Log statements automatically include timestamp, level, and class
- Router logs routing decisions for observability

### JSON handling
- `quarkus-rest-jackson` provides automatic JSON serialization/deserialization
- `LinkedHashMap` ensures stable key ordering in JSON responses
- Map-to-JSON conversion handled transparently by framework

### Build optimization
- Multi-stage Dockerfile reduces final image size
- Build stage includes Maven, runtime stage uses minimal JRE image
- `quarkus-maven-plugin` with `generate-code` and `build` goals
- Fast startup time (< 2 seconds) due to Quarkus build-time optimizations
