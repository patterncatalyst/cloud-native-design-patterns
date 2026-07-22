# Example 21: Graceful Shutdown — C++

Drogon + libpq implementation demonstrating graceful shutdown with SIGTERM
handling, readiness flip, and in-flight request draining.

## Stack

- **REST framework**: Drogon 1.9.8
- **Database client**: libpq (system package, C client)
- **Logging**: spdlog 1.15.0
- **Base image**: UBI 9 (GCC 14, Conan 2)

## Key implementation details

1. **SIGTERM handler**: Uses `std::signal(SIGTERM, handler)` with `std::atomic<bool>
   g_shutting_down`. The handler sets the flag and logs "SIGTERM received". Drogon
   continues running so readyz can respond with 503.

2. **In-flight tracking**: `std::atomic<int> g_in_flight` incremented at handler entry,
   decremented via RAII guard (`InFlightGuard`).

3. **Readiness probe**: Returns HTTP 503 with `{"ready":false,"reason":"shutting down"}`
   when `g_shutting_down` is true. Otherwise performs DB health check.

4. **Debug state**: `GET /debug/state` returns `{"shutting_down":bool,"in_flight":N,"pid":PID}`.

5. **POST /orders**: Parses JSON body, generates UUID, inserts into DB, returns 201.

6. **Graceful drain**: After `app().run()` returns, waits for `g_in_flight` to reach zero
   before exiting.

## Running

```bash
# Start the stack (builds on first run, ~10-15 min cold Conan cache)
podman compose up -d

# Verify graceful shutdown behavior
../verify.sh

# Tail logs
podman logs -f cndp-order-service

# Shutdown
podman compose down
```

## Verify script tests

The `verify.sh` script (run with `COMPOSE_FILE=cpp/compose.yaml`) checks:

1. Health and readiness endpoints
2. Order creation (POST /orders)
3. SIGTERM → readyz flips to 503, logs show "SIGTERM received"
4. Debug state shows `shutting_down:true`
5. Service restart → recovery (readyz 200, orders persist)

## Container naming

Service container: `cndp-order-service` (matches verify.sh expectation).
