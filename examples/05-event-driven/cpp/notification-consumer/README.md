# Notification consumer (C++)

Consumes `order.placed` in consumer group `notification-group` and writes `notifications` rows.

## Stack

- **C++23** (GCC 15 from `gcc-toolset-15`), CMake 4.4.4, Ninja 1.13.2, Conan 2.33.0, on `ubi10/ubi:10.2`;
  runtime `ubi10/ubi-minimal:10.2`, non-root (UID 1001, group 0), libstdc++ linked statically.
- **librdkafka 2.14.2** through its C++ API (`rdkafka++`). modern-cpp-kafka is archived upstream, so the
  examples use the librdkafka C++ classes directly. ConanCenter has 2.14.2 as the newest librdkafka recipe;
  upstream is ahead (2.16.0).
- **Consumer**: `RdKafka::KafkaConsumer`, `enable.auto.commit=false`; the offset is committed (`commitSync`) only after
  the Postgres row is written (libpq, `ON CONFLICT DO NOTHING`), so a crash redelivers instead of losing the event.
- **libpq 17.11** (direct, no libpqxx), **jsoncpp 1.9.8**.
- **Tracing**: OpenTelemetry C++ 1.26.0 (OTLP/HTTP to `OTEL_EXPORTER_OTLP_ENDPOINT`, service name `notification-consumer`). One consumer span per
  record, parented on the `traceparent` header the order service sets.

## Build

```bash
# from this directory (or the context shown in compose.yaml)
docker build -f Containerfile -t cndp-05-cpp .
```

The first build compiles the dependencies (BuildKit cache mount on `/root/.conan2`); later builds reuse them.
`conan.lock` pins the full dependency graph.
