import json
import logging
import os
import time
from collections import defaultdict

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("stream-processor")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9094")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318")
WINDOW_SECONDS = int(os.getenv("WINDOW_SECONDS", "300"))

resource = Resource.create({"service.name": "stream-processor"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces"))
)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("stream-processor")


def floor_to_window(ts: float) -> int:
    return int(ts // WINDOW_SECONDS) * WINDOW_SECONDS


import asyncio
import signal

shutdown = asyncio.Event()


def _signal_handler(*_):
    shutdown.set()


async def main():
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    consumer = AIOKafkaConsumer(
        "order.placed",
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="stream-processor",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda v: json.loads(v),
    )
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    await consumer.start()
    await producer.start()
    log.info("stream-processor started (window=%ds)", WINDOW_SECONDS)

    windows: dict[int, dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {"count": 0, "total": 0.0}))
    current_window = floor_to_window(time.time())

    try:
        while not shutdown.is_set():
            batch = await consumer.getmany(timeout_ms=1000, max_records=100)
            now_window = floor_to_window(time.time())

            for tp, messages in batch.items():
                for msg in messages:
                    order = msg.value
                    merchant = order.get("merchant_id", "unknown")
                    total = float(order.get("total", 0))
                    event_window = floor_to_window(msg.timestamp / 1000)

                    with tracer.start_as_current_span("aggregate") as span:
                        span.set_attribute("merchant.id", merchant)
                        span.set_attribute("window.start", event_window)
                        windows[event_window][merchant]["count"] += 1
                        windows[event_window][merchant]["total"] += total

            expired = [w for w in windows if w < now_window]
            for win_start in expired:
                for merchant, agg in windows[win_start].items():
                    result = {
                        "window_start": win_start,
                        "window_end": win_start + WINDOW_SECONDS,
                        "merchant_id": merchant,
                        "order_count": agg["count"],
                        "revenue": round(agg["total"], 2),
                    }
                    await producer.send("revenue.by-merchant", value=result)
                    log.info(
                        "emitted revenue window=%d merchant=%s count=%d revenue=%.2f",
                        win_start, merchant, agg["count"], agg["total"],
                    )
                del windows[win_start]

            if batch:
                await consumer.commit()

    finally:
        for win_start in list(windows):
            for merchant, agg in windows[win_start].items():
                result = {
                    "window_start": win_start,
                    "window_end": win_start + WINDOW_SECONDS,
                    "merchant_id": merchant,
                    "order_count": agg["count"],
                    "revenue": round(agg["total"], 2),
                }
                await producer.send("revenue.by-merchant", value=result)
                log.info("flushed final window=%d merchant=%s", win_start, merchant)

        await producer.stop()
        await consumer.stop()
        log.info("stream-processor stopped")


if __name__ == "__main__":
    asyncio.run(main())
