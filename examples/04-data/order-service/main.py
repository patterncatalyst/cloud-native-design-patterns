import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from fastapi import FastAPI, Query
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
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318")

resource = Resource.create({"service.name": "order"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces"))
)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

db_pool: Optional[asyncpg.Pool] = None


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
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    log.info("order-service started")
    yield
    await db_pool.close()


app = FastAPI(title="Order Service (Outbox)", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/orders", response_model=Order, status_code=201)
async def place_order(body: OrderIn):
    order_id = str(uuid.uuid4())

    with tracer.start_as_current_span("outbox-transaction"):
        async with db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, 'confirmed')",
                    order_id, body.sku, body.quantity,
                )
                payload = {
                    "id": order_id,
                    "sku": body.sku,
                    "quantity": body.quantity,
                    "status": "confirmed",
                }
                await conn.execute(
                    "INSERT INTO outbox (aggregate_id, event_type, payload) VALUES ($1, $2, $3)",
                    order_id, "order.placed", json.dumps(payload),
                )

    log.info("order + outbox written in one transaction id=%s", order_id)
    return Order(id=order_id, sku=body.sku, quantity=body.quantity, status="confirmed")


@app.get("/orders", response_model=list[Order])
async def list_orders(limit: int = Query(default=50, le=100)):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT $1",
            limit,
        )
    return [Order(id=r["id"], sku=r["sku"], quantity=r["quantity"], status=r["status"]) for r in rows]


@app.get("/outbox")
async def list_outbox(limit: int = Query(default=50, le=100)):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, aggregate_id, event_type, payload, created_at FROM outbox ORDER BY id DESC LIMIT $1",
            limit,
        )
    return [dict(r) for r in rows]
