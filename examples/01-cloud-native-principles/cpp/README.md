# Example 01: Cloud-Native Principles — C++

C++ implementation of the cloud-native principles chapter using **Drogon** (REST framework) and **libpq** (PostgreSQL C client).

## What it demonstrates

- **Factor III (Config)**: Service version and DB connection string from environment variables
- **Health probes**: `/healthz` (liveness, never checks deps) and `/readyz` (readiness, checks DB)
- **Stateless design**: No local state; all data externalized to PostgreSQL
- **CRUD operations**: REST API for creating and listing orders

## Stack

- **Drogon 1.9.8**: High-performance C++ REST framework with built-in JSON support (jsoncpp)
- **libpq**: PostgreSQL C client (system package from UBI AppStream, not from Conan)
- **spdlog 1.15**: Structured logging
- **Build**: Conan 2 + CMake 3.25 + Ninja + GCC 14 on UBI 9
- **Connection pool**: Production-quality `pg_pool.hpp` with RAII checkout pattern (borrowed from cpp-container-optimization-tutorial)

## Differences from the tutorial's Quarkus implementation

| Quarkus 3.33 LTS                     | Drogon 1.9.x + libpq                           |
|--------------------------------------|------------------------------------------------|
| Reactive REST (Mutiny)               | Callback-based handlers (Drogon)               |
| Hibernate Reactive + Vert.x PgClient | libpq direct (C API) + hand-rolled pool        |
| SmallRye Health annotations          | Manual `/healthz` and `/readyz` handlers       |
| MicroProfile Config                  | `std::getenv()` + defaults                     |

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
podman compose up --build

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

- **Simpler build**: libpq is in UBI's AppStream; no source build needed.
- **Stable C ABI**: No libstdc++ mixing concerns; the runtime image only needs `libpq.so`.
- **Conan recipe issues**: The libpqxx Conan recipe's CMake build fails under this toolchain (see cpp-container-optimization-tutorial gotcha G-67).

The connection pool patterns are identical; only the connection type differs (`PGconn*` vs `pqxx::connection`).

### Build time

- **First build**: ~10-15 minutes (Conan cold cache resolving Drogon + deps)
- **Warm cache**: < 1 minute (binary-only build)
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
