# Example 06: Stream Processing, C++

Two services built with C++23 (GCC 15 from `gcc-toolset-15`), CMake 4.4.4, Ninja 1.13.2 and Conan 2.33.0
on UBI 10, running on `ubi10/ubi-minimal` as UID 1001 (group 0). Same contract as the other languages:
`order-service` writes orders to Postgres and publishes `order.placed`; `stream-processor` turns that
stream into `revenue.by-merchant`.

| Service | Libraries |
|---------|-----------|
| `order-service` | Drogon 1.9.13 (REST), libpq 17.11 (direct), librdkafka 2.14.2 C++ API (`RdKafka::Producer` with a delivery-report callback, flushed on shutdown) |
| `stream-processor` | librdkafka 2.14.2 C++ API (`RdKafka::KafkaConsumer`, producer, admin API), nlohmann_json 3.12.0, spdlog 1.17.0 |

Kafka goes through librdkafka's C++ API (`rdkafka++`) because modern-cpp-kafka is archived upstream.

## The C++ approach to stream processing

The C++ stack has no Kafka Streams equivalent, so `stream-processor` writes the topology out on
`rdkafka++`. It mirrors the Go (goka) and Kafka Streams versions:

1. **rekey**: `order.placed` -> parse -> `stream-processor-by-merchant` (key = `merchant_id`, Kafka record time
   carried in the value, so event time survives the hop).
2. **aggregate**: `stream-processor-by-merchant` -> per-merchant tumbling windows (`WINDOW_SECONDS`, default 10,
   no grace period: a record whose window already ended relative to the merchant's stream time is dropped)
   -> `revenue.by-merchant`, one record per update.

One consumer in group `stream-processor` reads both input topics, so the repartition topic gives each merchant
exactly one owner. The three topics are created up front (3 partitions for the source when nobody created it,
the same count for the others) through the librdkafka admin API.

Commit order: each batch of input records is processed, the producer is flushed so every output record is
delivery-reported, and only then are the input offsets committed with `commitSync`. A failed delivery stops the
process without committing, and the batch replays on restart (at-least-once). Consumers of `revenue.by-merchant`
keep the latest record per `(merchant_id, window_start)`, so a replayed update is harmless. Window state is in
memory (the Go version mirrors it to a table topic): a window that spans a restart restarts from the committed
offset.

Output record:

```json
{"window_start":1760000000,"window_end":1760000010,"merchant_id":"merchant-a","order_count":3,"revenue":60.00}
```

`window_start` / `window_end` are epoch seconds. Revenue is an exact decimal sum (128-bit fixed point, never a
double) printed with two decimals, HALF_UP. An order whose total is not a plain decimal is skipped with a WARN;
log line per update: `emitted revenue window=<start> merchant=<id> count=<n> revenue=<amount>`.

## Tests

`stream-processor/tests/aggregation_test.cpp` covers window math, money rounding, event parsing and the
tumbling windows; `ctest` runs it in the image build stage, so a failing test fails `docker build`.

## Build and run

```bash
docker compose up --build        # from this directory
../verify.sh                     # from the example root
```

The first image build compiles librdkafka, Drogon and friends from ConanCenter sources (BuildKit cache mount on
the Conan home); later builds reuse them.
