import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import grpc
import httpx
import strawberry
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from strawberry.dataloader import DataLoader
from strawberry.fastapi import GraphQLRouter

import inventory_pb2
import inventory_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gateway")

ORDER_API_URL = os.getenv("ORDER_API_URL", "http://order-api:8081")
INVENTORY_ADDR = os.getenv("INVENTORY_ADDR", "inventory:50051")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318")

resource = Resource.create({"service.name": "gateway"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces"))
)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

http_client: Optional[httpx.AsyncClient] = None
grpc_channel: Optional[grpc.aio.Channel] = None
inventory_stub: Optional[inventory_pb2_grpc.InventoryStub] = None


async def batch_load_stock(skus: list[str]) -> list[Optional[int]]:
    with tracer.start_as_current_span("batch_load_stock", attributes={"skus": str(skus)}):
        reply = await inventory_stub.GetStockBatch(
            inventory_pb2.GetStockBatchRequest(skus=skus)
        )
        stock_map = {item.sku: item.available for item in reply.items}
        log.info("DataLoader batched %d skus in one gRPC call", len(skus))
        return [stock_map.get(sku) for sku in skus]


@strawberry.type
class OrderType:
    id: str
    sku: str
    quantity: int
    status: str

    @strawberry.field
    async def stock(self, info: strawberry.types.Info) -> Optional[int]:
        return await info.context["stock_loader"].load(self.sku)


@strawberry.type
class Query:
    @strawberry.field
    async def orders(self, info: strawberry.types.Info, limit: int = 50) -> list[OrderType]:
        with tracer.start_as_current_span("fetch_orders_rest"):
            resp = await http_client.get(f"{ORDER_API_URL}/orders", params={"limit": limit})
            resp.raise_for_status()
            data = resp.json()
        return [OrderType(**o) for o in data]

    @strawberry.field
    async def order(self, info: strawberry.types.Info, id: str) -> Optional[OrderType]:
        with tracer.start_as_current_span("fetch_order_rest"):
            resp = await http_client.get(f"{ORDER_API_URL}/orders/{id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
        return OrderType(**data)


schema = strawberry.Schema(query=Query)


async def get_context():
    return {"stock_loader": DataLoader(load_fn=batch_load_stock)}


graphql_router = GraphQLRouter(schema, context_getter=get_context)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client, grpc_channel, inventory_stub
    http_client = httpx.AsyncClient(timeout=10.0)
    grpc_channel = grpc.aio.insecure_channel(INVENTORY_ADDR)
    inventory_stub = inventory_pb2_grpc.InventoryStub(grpc_channel)
    log.info("gateway started")
    yield
    await http_client.aclose()
    await grpc_channel.close()


app = FastAPI(title="GraphQL Gateway", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)
app.include_router(graphql_router, prefix="/graphql")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
