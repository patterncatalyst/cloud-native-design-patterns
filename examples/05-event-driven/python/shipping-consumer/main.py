import json
import logging
import os
import signal
import asyncio
from typing import Optional

import asyncpg
from aiokafka import AIOKafkaConsumer
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("shipping")

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://appuser:apppass@postgres:5432/appdb")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9094")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318")

resource = Resource.create({"service.name": "shipping"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces"))
)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("shipping")

shutdown = asyncio.Event()


def _signal_handler(*_):
    shutdown.set()


async def main():
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    consumer = AIOKafkaConsumer(
        "order.placed",
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="shipping-group",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda v: json.loads(v),
    )
    await consumer.start()
    log.info("shipping-consumer started")

    try:
        while not shutdown.is_set():
            batch = await consumer.getmany(timeout_ms=1000, max_records=50)
            for tp, messages in batch.items():
                for msg in messages:
                    order = msg.value
                    order_id = order["id"]
                    with tracer.start_as_current_span("process_shipment") as span:
                        span.set_attribute("order.id", order_id)
                        async with pool.acquire() as conn:
                            try:
                                await conn.execute(
                                    "INSERT INTO shipments (order_id, status) VALUES ($1, 'scheduled')",
                                    order_id,
                                )
                                log.info("shipment scheduled order_id=%s", order_id)
                            except asyncpg.UniqueViolationError:
                                log.info("duplicate skipped order_id=%s", order_id)
                    await consumer.commit()
    finally:
        await consumer.stop()
        await pool.close()
        log.info("shipping-consumer stopped")


if __name__ == "__main__":
    asyncio.run(main())
