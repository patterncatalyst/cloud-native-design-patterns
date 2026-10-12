import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from aiokafka import AIOKafkaProducer
from fastapi import FastAPI
from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("order")


class Settings(BaseSettings):
    database_url: str = "postgres://appuser:apppass@postgres:5432/appdb"
    kafka_bootstrap: str = "kafka:9094"
    otel_endpoint: str = Field("http://lgtm:4318", validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    service_name: str = Field("order-service", validation_alias="OTEL_SERVICE_NAME")


settings = Settings()

resource = Resource.create({"service.name": settings.service_name})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{settings.otel_endpoint}/v1/traces"))
)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("order-service")

db_pool: Optional[asyncpg.Pool] = None
producer: Optional[AIOKafkaProducer] = None


class OrderIn(BaseModel):
    sku: str = Field(min_length=1)
    quantity: int = Field(gt=0)


class Order(BaseModel):
    id: str
    sku: str
    quantity: int
    status: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, producer
    db_pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap,
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    await producer.start()
    log.info("order-service started")
    yield
    await producer.stop()
    await db_pool.close()


app = FastAPI(title="Order Service", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/orders", response_model=Order, status_code=201)
async def place_order(body: OrderIn):
    order_id = str(uuid.uuid4())
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, 'confirmed')",
            order_id, body.sku, body.quantity,
        )

    event = {"id": order_id, "sku": body.sku, "quantity": body.quantity, "status": "confirmed"}
    # Carry the trace context in the Kafka headers so the consumer spans join this trace.
    with tracer.start_as_current_span("order.placed publish", kind=trace.SpanKind.PRODUCER) as span:
        span.set_attribute("order.id", order_id)
        carrier: dict[str, str] = {}
        propagate.inject(carrier)
        headers = [(k, v.encode()) for k, v in carrier.items()]
        await producer.send("order.placed", value=event, headers=headers)
    log.info("published order.placed id=%s", order_id)

    return Order(id=order_id, sku=body.sku, quantity=body.quantity, status="confirmed")


@app.get("/orders", response_model=list[Order])
async def list_orders():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT 50")
    return [Order(**dict(r)) for r in rows]
