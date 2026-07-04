import json
import logging
import os
import signal
import asyncio

import asyncpg
from aiokafka import AIOKafkaConsumer
from opentelemetry import trace, context as otel_context
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import extract
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("notification")

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://appuser:apppass@postgres:5432/appdb")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9094")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318")

resource = Resource.create({"service.name": "notification-consumer"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces"))
)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("notification-consumer")

shutdown = asyncio.Event()


def _signal_handler(*_):
    shutdown.set()


class _KafkaHeaderGetter:
    def get(self, carrier, key):
        for k, v in carrier:
            if k == key:
                return [v.decode("utf-8") if isinstance(v, bytes) else v]
        return []

    def keys(self, carrier):
        return [k for k, v in carrier]

_kafka_header_getter = _KafkaHeaderGetter()


async def main():
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    consumer = AIOKafkaConsumer(
        "order.placed",
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="notification-group",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda v: json.loads(v),
    )
    await consumer.start()
    log.info("notification-consumer started")

    try:
        while not shutdown.is_set():
            batch = await consumer.getmany(timeout_ms=1000, max_records=50)
            for tp_, messages in batch.items():
                for msg in messages:
                    headers = msg.headers or []
                    ctx = extract(headers, getter=_kafka_header_getter)
                    token = otel_context.attach(ctx)
                    try:
                        order = msg.value
                        order_id = order["id"]
                        with tracer.start_as_current_span("process_notification") as span:
                            span.set_attribute("order.id", order_id)
                            async with pool.acquire() as conn:
                                try:
                                    await conn.execute(
                                        "INSERT INTO notifications (order_id, channel) VALUES ($1, 'email')",
                                        order_id,
                                    )
                                    log.info("notification sent order_id=%s", order_id)
                                except asyncpg.UniqueViolationError:
                                    log.info("duplicate skipped order_id=%s", order_id)
                    finally:
                        otel_context.detach(token)
                    await consumer.commit()
    finally:
        await consumer.stop()
        await pool.close()
        log.info("notification-consumer stopped")


if __name__ == "__main__":
    asyncio.run(main())
