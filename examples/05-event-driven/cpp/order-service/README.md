# Order service (C++)

POST/GET `/orders`: inserts the order with libpq and publishes `order.placed`.

## Stack

- **C++23** (GCC 15 from `gcc-toolset-15`), CMake 4.4.4, Ninja 1.13.2, Conan 2.33.0, on `ubi10/ubi:10.2`;
  runtime `ubi10/ubi-minimal:10.2`, non-root (UID 1001, group 0), libstdc++ linked statically.
- **librdkafka 2.14.2** through its C++ API (`rdkafka++`). modern-cpp-kafka is archived upstream, so the
  examples use the librdkafka C++ classes directly. ConanCenter has 2.14.2 as the newest librdkafka recipe;
  upstream is ahead (2.16.0).
- **Drogon 1.9.13** (REST), **libpq 17.11** (direct, no libpqxx).
- **Producer**: `RdKafka::Producer` with `acks=all` and a `DeliveryReportCb`; a poller thread serves
  delivery reports, and shutdown calls `flush()` so queued events are delivered before exit.

## Build

```bash
# from this directory (or the context shown in compose.yaml)
docker build -f Containerfile -t cndp-05-cpp .
```

The first build compiles the dependencies (BuildKit cache mount on `/root/.conan2`); later builds reuse them.
`conan.lock` pins the full dependency graph.
