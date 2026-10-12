import logging
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from fastapi import FastAPI, Query
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("order-api")


class Settings(BaseSettings):
    database_url: str = "postgres://appuser:apppass@postgres:5432/appdb"
    otel_endpoint: str = Field("http://lgtm:4318", validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT")


settings = Settings()

resource = Resource.create({"service.name": "order-api"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{settings.otel_endpoint}/v1/traces"))
)
trace.set_tracer_provider(provider)
AsyncPGInstrumentor().instrument()   # one span per SQL statement

db_pool: Optional[asyncpg.Pool] = None


class Order(BaseModel):
    id: str
    sku: str
    quantity: int
    status: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    db_pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
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
