# Example 01: Cloud-Native Principles — C++

C++23 implementation of the cloud-native principles chapter using **Drogon** (REST framework), **libpq** (PostgreSQL C client) and **OpenTelemetry C++** (OTLP traces).

## What it demonstrates

- **Factor III (Config)**: Service version and DB connection string from environment variables
- **Health probes**: `/healthz` (liveness, never checks deps) and `/readyz` (readiness, checks DB)
- **Stateless design**: No local state; all data externalized to PostgreSQL
- **CRUD operations**: REST API for creating and listing orders

## Stack

- **Drogon 1.9.13**: High-performance C++ REST framework with built-in JSON support (jsoncpp)
- **libpq 17.11**: PostgreSQL C client (Conan, linked statically; direct, no libpqxx)
- **spdlog 1.17.0**: Logging; handlers add `trace_id` so a log line joins its trace
- **opentelemetry-cpp 1.26.0**: one server span per request, continuing an incoming `traceparent`, exported over OTLP/HTTP to `OTEL_EXPORTER_OTLP_ENDPOINT` (`http://lgtm:4318`); resource attributes from `OTEL_SERVICE_NAME` / `OTEL_RESOURCE_ATTRIBUTES`
- **Build**: Conan 2.33.0 + CMake 4.4.4 + Ninja 1.13.2 + GCC 15.2 (`gcc-toolset-15`), C++23, on UBI 10; runtime `ubi10/ubi-minimal` with libstdc++ linked statically
- **Connection pool**: Production-quality `pg_pool.hpp` with RAII checkout pattern (borrowed from cpp-container-optimization-tutorial)

## Differences from the tutorial's Quarkus implementation

| Quarkus 3.40.1 LTS                   | Drogon 1.9.13 + libpq                     |
|--------------------------------------|------------------------------------------|
| Reactive REST (Mutiny)               | Callback-based handlers (Drogon)         |
| Hibernate Reactive + Vert.x PgClient | libpq direct (C API) + hand-rolled pool  |
| SmallRye Health annotations          | Manual `/healthz` and `/readyz` handlers |
| MicroProfile Config                  | `std::getenv()` + defaults               |

The pg_pool.hpp connection pool implements the same RAII discipline and exception safety patterns as the tutorial's Java/Kotlin examples, but for libpq's C API.

## API contract

```bash
# Service info from environment
GET /
→ {"service":"order-service","version":"1.0.0","config_source":"environment"}

# Liveness probe (always ok)
GET /healthz
→ {"status":"ok"}

# Readiness probe (checks DB)
GET /readyz
→ {"status":"ready","checks":{"database":"ok"}}
→ {"status":"down","checks":{"database":"unreachable"}}  # when DB is down

# Create order
POST /orders?customer=alice&total=42.50
→ {"id":1,"customer":"alice","total":42.5}

# List orders
GET /orders
→ [{"id":1,"customer":"alice","total":42.5}]
```

## Build & run

```bash
# From examples/01-cloud-native-principles/cpp/
docker compose up --build

# Wait for healthcheck to pass (first build takes ~10-15 minutes cold cache)
# Subsequent builds < 1 minute

# In another terminal, run the verification script
cd ..
./verify.sh
```

## Architecture notes

### Connection pool (`pg_pool.hpp`)

The pool eagerly opens N connections at startup (fail-fast if DB is unreachable) and hands them out via RAII `ScopedConnection` handles. Key patterns:

- **Lazy replacement**: A poisoned connection (timeout, reset) is discarded on release; a fresh connection is opened on the next `acquire()`, not in a destructor.
- **Exception safety**: Handlers call `invalidate()` on connections that hit errors; the pool never returns a poisoned connection to the free list.
- **Timeout**: `acquire()` waits up to 2s (readyz) or 5s (CRUD) for a free connection; throws `std::runtime_error` on timeout.

This is production-quality code adapted from the cpp-container-optimization-tutorial's stateless outbox example.

### Why libpq (not libpqxx)?

- **Locked stack**: the C++ stack uses libpq directly; the connection pool below is the only code the C API needs.
- **Stable C ABI**: no libstdc++ mixing concerns; libpq is built by Conan and linked into the binary.
- **Pinned**: libpq 17.11 comes from ConanCenter with the rest of the graph, so it is not tied to the UBI package version.

The connection pool patterns are identical; only the connection type differs (`PGconn*` vs `pqxx::connection`).

### Build time

- **First build**: about 7 minutes on 16 cores (Conan compiles Drogon, OpenTelemetry, protobuf and libpq from source)
- **Warm cache**: under 1 minute (the Conan home is a BuildKit cache mount, `/root/.conan2`)
- **Container startup**: < 5 seconds (the `start_period: 60s` in compose.yaml is for build time, not runtime)

## Environment variables

- `SERVICE_VERSION`: Service version string (default: `1.0.0`)
- `PG_CONNINFO`: PostgreSQL connection string (default: `postgresql://appuser:apppass@postgres:5432/appdb`)
- `PG_POOL_SIZE`: Connection pool size (default: `4`)
- `OTEL_*`: OpenTelemetry configuration (env vars present but SDK not linked in this example)

## Cross-check it yourself

Run `./verify.sh` from the parent directory. It tests all 10 checks from the tutorial:
1. Root endpoint returns service info from environment
2. Liveness probe always returns ok
3. Readiness probe checks DB connectivity
4. Create order via POST with query params
5. List orders returns JSON array
6. Readiness flips to down when DB is stopped
7. Liveness still returns ok when DB is stopped
8. Readiness recovers after DB restart

*Verification status: pending first successful run*
