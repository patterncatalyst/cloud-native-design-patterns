import json
import logging
import signal
import asyncio
from typing import Optional

import asyncpg
from aiokafka import AIOKafkaConsumer
from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import Field
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("shipping")


class Settings(BaseSettings):
    database_url: str = "postgres://appuser:apppass@postgres:5432/appdb"
    kafka_bootstrap: str = "kafka:9094"
    otel_endpoint: str = Field("http://lgtm:4318", validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    service_name: str = Field("shipping-consumer", validation_alias="OTEL_SERVICE_NAME")


settings = Settings()

resource = Resource.create({"service.name": settings.service_name})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{settings.otel_endpoint}/v1/traces"))
)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("shipping")

shutdown = asyncio.Event()


def _signal_handler(*_):
    shutdown.set()


async def main():
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
    consumer = AIOKafkaConsumer(
        "order.placed",
        bootstrap_servers=settings.kafka_bootstrap,
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
                    # Continue the producer's trace from the Kafka headers.
                    parent = propagate.extract({k: v.decode() for k, v in (msg.headers or ())})
                    with tracer.start_as_current_span(
                        "process_shipment", context=parent, kind=trace.SpanKind.CONSUMER
                    ) as span:
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
