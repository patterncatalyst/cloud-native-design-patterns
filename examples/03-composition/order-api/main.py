import logging
import os
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
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("order-api")

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://appuser:apppass@postgres:5432/appdb")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318")

resource = Resource.create({"service.name": "order-api"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces"))
)
trace.set_tracer_provider(provider)

db_pool: Optional[asyncpg.Pool] = None


class Order(BaseModel):
    id: str
    sku: str
    quantity: int
    status: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    log.info("order-api started")
    yield
    await db_pool.close()


app = FastAPI(title="Order API", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/orders", response_model=list[Order])
async def list_orders(limit: int = Query(default=50, le=100)):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, sku, quantity, status FROM orders ORDER BY id LIMIT $1", limit
        )
    return [Order(id=r["id"], sku=r["sku"], quantity=r["quantity"], status=r["status"]) for r in rows]


@app.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str):
    async with db_pool.acquire() as conn:
        r = await conn.fetchrow("SELECT id, sku, quantity, status FROM orders WHERE id = $1", order_id)
    if r is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="order not found")
    return Order(id=r["id"], sku=r["sku"], quantity=r["quantity"], status=r["status"])
