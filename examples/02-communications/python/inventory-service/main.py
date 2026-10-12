import asyncio
import logging
from concurrent import futures

import grpc
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import Field
from pydantic_settings import BaseSettings

import inventory_pb2
import inventory_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("inventory")


class Settings(BaseSettings):
    otel_endpoint: str = Field("http://lgtm:4318", validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    service_name: str = Field("inventory", validation_alias="OTEL_SERVICE_NAME")
    initial_stock: int = 100


settings = Settings()

resource = Resource.create({"service.name": settings.service_name})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{settings.otel_endpoint}/v1/traces"))
)
trace.set_tracer_provider(provider)
GrpcInstrumentorServer().instrument()

STOCK: dict[str, int] = {}


class InventoryServicer(inventory_pb2_grpc.InventoryServicer):
    def ReserveStock(self, request, context):
        sku = request.sku
        qty = request.quantity

        if sku not in STOCK:
            STOCK[sku] = settings.initial_stock

        remaining = STOCK[sku] - qty
        if remaining >= 0:
            STOCK[sku] = remaining
            log.info("reserved sku=%s qty=%d remaining=%d", sku, qty, remaining)
            return inventory_pb2.ReserveReply(reserved=True, remaining=remaining)

        log.warning("insufficient stock sku=%s requested=%d available=%d", sku, qty, STOCK[sku])
        return inventory_pb2.ReserveReply(reserved=False, remaining=STOCK[sku])


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    inventory_pb2_grpc.add_InventoryServicer_to_server(InventoryServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    log.info("inventory gRPC server listening on :50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
