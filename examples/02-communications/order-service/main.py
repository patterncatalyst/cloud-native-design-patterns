import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
import grpc
import strawberry
from aiokafka import AIOKafkaProducer
from fastapi import FastAPI, Query
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel, Field
from strawberry.fastapi import GraphQLRouter

import inventory_pb2
import inventory_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("order")

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://appuser:apppass@postgres:5432/appdb")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9094")
INVENTORY_ADDR = os.getenv("INVENTORY_ADDR", "inventory:50051")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318")
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "order")

resource = Resource.create({"service.name": SERVICE_NAME})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces"))
)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)


class OrderIn(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(gt=0, le=1000)


class Order(BaseModel):
    id: str
    sku: str
    quantity: int
    status: str


class Page(BaseModel):
    items: list[Order]
    next_cursor: Optional[str] = None


db_pool: Optional[asyncpg.Pool] = None
producer: Optional[AIOKafkaProducer] = None
grpc_channel: Optional[grpc.aio.Channel] = None
inventory_stub: Optional[inventory_pb2_grpc.InventoryStub] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, producer, grpc_channel, inventory_stub

    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    await producer.start()
    grpc_channel = grpc.aio.insecure_channel(INVENTORY_ADDR)
    inventory_stub = inventory_pb2_grpc.InventoryStub(grpc_channel)
    log.info("order-service started")

    yield

    await producer.stop()
    await grpc_channel.close()
    await db_pool.close()


app = FastAPI(title="Order Service", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/orders", response_model=Order, status_code=201)
async def place_order(body: OrderIn):
    with tracer.start_as_current_span("reserve-stock"):
        reply = await inventory_stub.ReserveStock(
            inventory_pb2.ReserveRequest(sku=body.sku, quantity=body.quantity)
        )

    status = "confirmed" if reply.reserved else "rejected"
    order_id = str(uuid.uuid4())

    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4)",
            order_id, body.sku, body.quantity, status,
        )

    order = Order(id=order_id, sku=body.sku, quantity=body.quantity, status=status)

    await producer.send(
        "order.placed",
        value={"id": order.id, "sku": order.sku, "quantity": order.quantity, "status": order.status},
    )
    log.info("order created id=%s status=%s", order.id, order.status)
    return order


@app.get("/orders", response_model=Page)
async def list_orders(after: Optional[str] = Query(None), limit: int = Query(default=50, le=100)):
    async with db_pool.acquire() as conn:
        if after:
            rows = await conn.fetch(
                "SELECT id, sku, quantity, status FROM orders WHERE id > $1 ORDER BY id LIMIT $2",
                after, limit,
            )
        else:
            rows = await conn.fetch(
                "SELECT id, sku, quantity, status FROM orders ORDER BY id LIMIT $1",
                limit,
            )

    items = [Order(id=r["id"], sku=r["sku"], quantity=r["quantity"], status=r["status"]) for r in rows]
    next_cursor = items[-1].id if len(items) == limit else None
    return Page(items=items, next_cursor=next_cursor)


@strawberry.type
class OrderType:
    id: str
    sku: str
    quantity: int
    status: str


@strawberry.type
class Query:
    @strawberry.field
    async def orders(self, limit: int = 50) -> list[OrderType]:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, sku, quantity, status FROM orders ORDER BY id LIMIT $1", limit
            )
        return [OrderType(id=r["id"], sku=r["sku"], quantity=r["quantity"], status=r["status"]) for r in rows]

    @strawberry.field
    async def order(self, id: str) -> Optional[OrderType]:
        async with db_pool.acquire() as conn:
            r = await conn.fetchrow("SELECT id, sku, quantity, status FROM orders WHERE id = $1", id)
        if r is None:
            return None
        return OrderType(id=r["id"], sku=r["sku"], quantity=r["quantity"], status=r["status"])


schema = strawberry.Schema(query=Query)
graphql_router = GraphQLRouter(schema)
app.include_router(graphql_router, prefix="/graphql")
