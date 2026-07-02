import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
import grpc
from aiokafka import AIOKafkaProducer
from fastapi import FastAPI
from opentelemetry import trace, metrics, context
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient
from opentelemetry.propagate import inject
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from pydantic import BaseModel, Field

import inventory_pb2
import inventory_pb2_grpc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("order")

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://appuser:apppass@postgres:5432/appdb")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9094")
INVENTORY_ADDR = os.getenv("INVENTORY_ADDR", "inventory:50051")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318")

resource = Resource.create({"service.name": "order-service"})

tp = TracerProvider(resource=resource)
tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces")))
trace.set_tracer_provider(tp)
tracer = trace.get_tracer("order-service")

reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=f"{OTEL_ENDPOINT}/v1/metrics"), export_interval_millis=5000)
mp = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(mp)
meter = metrics.get_meter("order-service")
orders_placed_counter = meter.create_counter("orders.placed", description="Number of orders placed")

GrpcInstrumentorClient().instrument()

db_pool: Optional[asyncpg.Pool] = None
producer: Optional[AIOKafkaProducer] = None


class OTelLogFilter(logging.Filter):
    def filter(self, record):
        span = trace.get_current_span()
        ctx = span.get_span_context()
        record.otelTraceID = format(ctx.trace_id, "032x") if ctx.trace_id else "0" * 32
        record.otelSpanID = format(ctx.span_id, "016x") if ctx.span_id else "0" * 16
        return True


for handler in logging.root.handlers:
    handler.addFilter(OTelLogFilter())


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

    with tracer.start_as_current_span("reserve-stock") as span:
        span.set_attribute("sku", body.sku)
        span.set_attribute("quantity", body.quantity)
        async with grpc.aio.insecure_channel(INVENTORY_ADDR) as channel:
            stub = inventory_pb2_grpc.InventoryServiceStub(channel)
            resp = await stub.ReserveStock(
                inventory_pb2.ReserveRequest(sku=body.sku, quantity=body.quantity)
            )
            status = "confirmed" if resp.confirmed else "rejected"
            span.set_attribute("stock.confirmed", resp.confirmed)

    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4)",
            order_id, body.sku, body.quantity, status,
        )

    event = {"id": order_id, "sku": body.sku, "quantity": body.quantity, "status": status}
    headers = []
    inject(carrier=headers, setter=_kafka_header_setter)
    await producer.send("order.placed", value=event, headers=headers)

    orders_placed_counter.add(1, {"sku": body.sku, "status": status})
    log.info("order placed sku=%s id=%s status=%s", body.sku, order_id, status)

    return Order(id=order_id, sku=body.sku, quantity=body.quantity, status=status)


class _KafkaHeaderSetter:
    def set(self, carrier, key, value):
        carrier.append((key, value.encode("utf-8") if isinstance(value, str) else value))

_kafka_header_setter = _KafkaHeaderSetter()


@app.get("/orders", response_model=list[Order])
async def list_orders():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT 50")
    return [Order(**dict(r)) for r in rows]
