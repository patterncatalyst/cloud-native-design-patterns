# Example 21: Graceful Shutdown — C++

Drogon + libpq implementation demonstrating graceful shutdown with SIGTERM
handling, readiness flip, and in-flight request draining.

## Stack

- **REST framework**: Drogon 1.9.13
- **Database client**: libpq 17.11 (Conan, direct C client)
- **Logging**: spdlog 1.17.0
- **Base image**: UBI 10 (GCC 15, C++23, CMake 4.4.4, Conan 2.33.0); runtime `ubi10/ubi-minimal`

## Key implementation details

1. **SIGTERM handler**: Uses `std::signal(SIGTERM, handler)` with `std::atomic<bool>
   g_shutting_down`. The handler is async-signal-safe: it only stores to the lock-free
   atomic. A watcher thread observes the flag, logs "SIGTERM received", keeps serving for
   `DRAIN_DELAY_SECONDS` (default 5) so endpoints update and readyz answers 503, waits for
   in-flight requests to reach zero (20 s bound) and calls `app().quit()`. One SIGTERM drives
   the whole sequence.

2. **In-flight tracking**: `std::atomic<int> g_in_flight` incremented at handler entry,
   decremented via RAII guard (`InFlightGuard`).

3. **Readiness probe**: Returns HTTP 503 with `{"ready":false,"reason":"shutting down"}`
   when `g_shutting_down` is true. Otherwise performs DB health check.

4. **Debug state**: `GET /debug/state` returns `{"shutting_down":bool,"in_flight":N,"pid":PID}`.

5. **POST /orders**: Parses JSON body, generates UUID, inserts into DB, returns 201.

6. **Graceful drain**: After `app().run()` returns, closes the connection pool and exits 0.

## Running

```bash
# Start the stack (builds on first run, about 7 min cold Conan cache)
docker compose up -d

# Verify graceful shutdown behavior
../verify.sh

# Tail logs
docker logs -f cndp-order-service

# Shutdown
docker compose down
```

## Verify script tests

The `verify.sh` script checks:

1. Health and readiness endpoints
2. Order creation (POST /orders)
3. One SIGTERM → readyz flips to 503, logs show "SIGTERM received"
4. Debug state shows `shutting_down:true`
5. The container exits by itself with code 0 inside the 30 s grace period
6. Service restart → recovery (readyz 200, orders persist)
7. `docker stop -t 30` → exit code 0 before the timeout

## Container naming

Service container: `cndp-order-service` (matches verify.sh expectation).
