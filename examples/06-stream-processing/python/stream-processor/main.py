"""order.placed -> tumbling window per merchant -> revenue.by-merchant.

A faust-streaming app: one agent re-keys the order stream by merchant, a windowed Table
holds the running (count, total) for each merchant and window, and every update to a
(merchant, window) row is emitted downstream. A window therefore yields a running total
that settles when the window closes; consumers keep the latest record per
(merchant_id, window_start). The contract matches the Kafka Streams and Streamiz versions.
"""
import asyncio
import json
import logging
import os
from datetime import timedelta
from decimal import Decimal, InvalidOperation

import faust
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import KafkaConnectionError, TopicAlreadyExistsError
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

ORDERS = "order.placed"
REVENUE = "revenue.by-merchant"

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9094")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318")
WINDOW_SECONDS = int(os.getenv("WINDOW_SECONDS", "10"))

log = logging.getLogger("stream-processor")

provider = TracerProvider(resource=Resource.create({"service.name": "stream-processor"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces")))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("stream-processor")

app = faust.App(
    # The app id is also the consumer group (verify.sh looks for "stream-processor").
    "stream-processor",
    broker=f"kafka://{KAFKA_BOOTSTRAP}",
    # The window state is small and bounded (a window expires one window length after it
    # closes) and every write is mirrored to the table's changelog topic, which Faust
    # replays on restart. An in-memory store is therefore enough: no RocksDB, no volume.
    store="memory://",
    web_enabled=False,
    # internal (repartition, changelog) topics get the same partition count as the source
    topic_partitions=3,
    consumer_auto_offset_reset="earliest",
    # Emit updated window aggregates about every second instead of every 2.8 s (default).
    broker_commit_interval=1.0,
)

# Raw bytes in, raw bytes out: a record that is not valid JSON is skipped, not fatal.
orders_topic = app.topic(ORDERS, key_serializer="raw", value_serializer="raw", allow_empty=True)
revenue_topic = app.topic(REVENUE, key_serializer="raw", value_serializer="raw")

# Tumbling windows, no grace (a window is dropped one window length after it ends),
# positioned by the timestamp of the record being processed (stream time), like the
# Kafka Streams TimeWindows.ofSizeWithNoGrace version.
revenue = app.Table(
    "revenue",
    default=lambda: {"count": 0, "total": "0"},
).tumbling(
    WINDOW_SECONDS,
    expires=timedelta(seconds=WINDOW_SECONDS),
).relative_to_stream()


def parse(raw: bytes | None) -> tuple[str, str] | None:
    """Return (merchant_id, total) for a usable order event, otherwise None."""
    try:
        event = json.loads(raw)
        merchant = event["merchant_id"]
        total = event.get("total")
        if not isinstance(merchant, str) or not merchant:
            return None
        return merchant, "0" if total is None else str(total)
    except (TypeError, ValueError, KeyError, AttributeError):
        return None


def merchant_of(raw: bytes) -> bytes:
    """Repartition key. An unusable record keeps an empty key and is dropped by the agent."""
    parsed = parse(raw)
    return parsed[0].encode() if parsed else b""


@app.agent(orders_topic)
async def aggregate(orders):
    async for raw in orders.group_by(merchant_of, name="merchant"):
        parsed = parse(raw)
        if parsed is None:
            log.warning("skipping unreadable order record")
            continue
        merchant, amount = parsed
        # A total that is not a number skips the record instead of killing the agent.
        try:
            value = Decimal(amount)
            if not value.is_finite():
                raise InvalidOperation
        except InvalidOperation:
            log.warning("skipping order with invalid total merchant=%s total=%s", merchant, amount)
            continue

        # Kafka record timestamp (seconds); the window is the one that contains it.
        timestamp = faust.current_event().message.timestamp
        start = int(timestamp // WINDOW_SECONDS) * WINDOW_SECONDS

        with tracer.start_as_current_span("aggregate") as span:
            span.set_attribute("merchant.id", merchant)
            span.set_attribute("window.start", start)
            acc = revenue[merchant].value()
            count = acc["count"] + 1
            total = Decimal(acc["total"]) + value
            revenue[merchant] = {"count": count, "total": str(total)}

        shown = total.quantize(Decimal("0.01"))
        log.info("emitted revenue window=%d merchant=%s count=%d revenue=%s", start, merchant, count, shown)
        # revenue is spliced in as a JSON number with exactly two decimals
        body = '{"window_start": %d, "window_end": %d, "merchant_id": %s, "order_count": %d, "revenue": %s}' % (
            start, start + WINDOW_SECONDS, json.dumps(merchant), count, shown,
        )
        await revenue_topic.send(key=merchant.encode(), value=body.encode())


async def ensure_topics() -> None:
    """Faust only declares its own internal topics. Create the source and the sink up
    front (broker defaults apply), as the Streamiz version does, and wait for Kafka."""
    admin = AIOKafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP)
    for attempt in range(1, 31):
        try:
            await admin.start()
            break
        except KafkaConnectionError as e:
            log.warning("Kafka not ready, retry %d/30: %s", attempt, e)
            await asyncio.sleep(2)
    else:
        raise RuntimeError(f"could not reach Kafka at {KAFKA_BOOTSTRAP}")
    try:
        for name in (ORDERS, REVENUE):
            try:
                await admin.create_topics([NewTopic(name, num_partitions=3, replication_factor=1)])
            except TopicAlreadyExistsError:
                pass
    finally:
        await admin.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(ensure_topics())
    app.main()
