# Example 22: L7 routing, router-service (C++)

In-app, rule-driven routing: Drogon serves `POST /orders`, `GET|PUT /rules` and `GET /healthz`;
the routing policy is a Lua script (`routing.lua`) run with **sol2** on Lua 5.4.8, the same
script contract as the Go service: `route(order, rules)` returns `topic, vip`.

## Sandbox

`src/routing_engine.hpp`:

- Only the base, table, string and math libraries are opened. `dofile`, `loadfile`, `load`,
  `loadstring`, `require`, `print`, `collectgarbage` and `string.dump` are removed; `io`, `os`,
  `debug` and `package` do not exist.
- Every call builds a fresh Lua state, loads the script and discards the state, so nothing is
  shared between concurrent requests and a script cannot leave globals behind for the next one.
- Per call: an instruction budget (5,000,000) and a 100 ms wall-clock deadline, both checked
  from a count hook every 1000 instructions, plus an 8 MiB allocator cap. A runaway script
  ends in an error and the request answers 500; the service keeps running.

`tests/engine_test.cpp` (CTest, run in the image build) covers routing, bad scripts, the
escapes above, the limits, state isolation and concurrent use.

`ROUTING_RULES_FILE` selects another script (default `/usr/share/router-service/routing.lua`,
copied into the image). The script is checked at startup; a syntax error stops the service.

## Build

C++23, GCC 15 (`gcc-toolset-15` on `ubi10/ubi:10.2`), CMake 4.4.4, Ninja 1.13.2, Conan 2.33.0
(Drogon 1.9.13, sol2 3.5.0, Lua 5.4.8). sol2's recipe pins `lua/5.4.6`; the conanfile overrides it
with the newest 5.4 release.
