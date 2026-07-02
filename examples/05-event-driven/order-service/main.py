import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from aiokafka import AIOKafkaProducer
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("order")

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://appuser:apppass@postgres:5432/appdb")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9094")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318")

resource = Resource.create({"service.name": "order"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces"))
)
trace.set_tracer_provider(provider)

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
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
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
    await producer.send("order.placed", value=event)
    log.info("published order.placed id=%s", order_id)

    return Order(id=order_id, sku=body.sku, quantity=body.quantity, status="confirmed")


@app.get("/orders", response_model=list[Order])
async def list_orders():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT 50")
    return [Order(**dict(r)) for r in rows]
