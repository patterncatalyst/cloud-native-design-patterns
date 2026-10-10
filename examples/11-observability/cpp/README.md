# Example 11: Observability, C++

C++23 (GCC 15, CMake 4.4.4, Conan 2.33.0) on UBI 10. `order-service` (Drogon 1.9.13, grpc++ 1.84.0, libpq 17.11,
librdkafka 2.14.2 C++ API) calls `inventory-service` over gRPC, stores the order in Postgres and publishes
`order.placed` with a W3C `traceparent` header. `notification-consumer` (rdkafka++ `KafkaConsumer`, manual commit
after the INSERT) continues the trace from that header.

Telemetry is OpenTelemetry C++ 1.26.0 (traces and the `orders.placed` counter over OTLP/HTTP to
`OTEL_EXPORTER_OTLP_ENDPOINT`) and spdlog; the `order placed ... trace_id=<32 hex>` log line carries the same
trace id as the Tempo trace. `src/telemetry.hpp` in each service holds the SDK setup.
