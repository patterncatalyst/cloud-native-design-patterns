# Example 06 — Stream Processing (Python)

Kafka stream processor with tumbling-window aggregation — order count and revenue per merchant.

## Framework & libraries

- **Framework**: FastAPI 0.143 (order-service), faust-streaming 0.15.3 (stream-processor)
- **Libraries**: aiokafka 0.14 (order-service producer; Faust's Kafka client), asyncpg 0.32, OTel 1.45
- **Container base**: `ubi10/python-314-minimal` (Python 3.14, non-root UID 1001)

## Run

```bash
docker compose up -d --build --wait
```

Wait for healthy, then verify from the example root:

```bash
cd .. && bash verify.sh
```

## Project structure

| Path | Description |
|------|-------------|
| `order-service/` | main.py — REST API publishing order.placed events |
| `stream-processor/` | main.py — tumbling-window aggregation, consumes order.placed, produces revenue.by-merchant |

## Implementation notes

The stream processor is a faust-streaming app: one agent re-keys `order.placed` by merchant
(`group_by`, which creates a repartition topic), a tumbling-window `Table` (no grace, positioned
by the record timestamp with `relative_to_stream()`) holds the running count and total for each
merchant and window, and every update is written to `revenue.by-merchant` as
`{window_start, window_end, merchant_id, order_count, revenue}` (epoch seconds, two-decimal
revenue), the same contract as the Kafka Streams and Streamiz versions. Consumers keep the latest
record per `(merchant_id, window_start)`.

- The Faust app id is the consumer group `stream-processor`; Faust also creates a repartition and
  a changelog topic.
- The store is `memory://`: the state is small, a window is dropped one window length after it
  closes, and Faust rebuilds it from the changelog topic on restart, so RocksDB (a native
  dependency with no Python 3.14 wheel) is not needed.
- A record that is not valid JSON, or whose `total` is not a number, is logged and skipped.
- Faust only declares its own internal topics, so the processor creates `order.placed` and
  `revenue.by-merchant` at startup.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`KAFKA_BOOTSTRAP, DATABASE_URL, WINDOW_SECONDS (stream-processor), OTEL_EXPORTER_OTLP_ENDPOINT`

## Local development (without containers)

Requires pip install -r requirements.txt.

```bash
uvicorn main:app --reload --port 8080
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
docker compose down -v
```
