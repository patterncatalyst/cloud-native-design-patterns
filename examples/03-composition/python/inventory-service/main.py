import logging
import os
from concurrent import futures

import grpc
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

import inventory_pb2
import inventory_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("inventory")

OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318")

resource = Resource.create({"service.name": "inventory"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces"))
)
trace.set_tracer_provider(provider)
GrpcInstrumentorServer().instrument()

STOCK = {
    "widget-a": 42,
    "widget-b": 17,
    "gadget-x": 100,
    "gadget-y": 0,
}
call_count = 0


class InventoryServicer(inventory_pb2_grpc.InventoryServicer):
    def GetStock(self, request, context):
        global call_count
        call_count += 1
        available = STOCK.get(request.sku, 0)
        log.info("GetStock sku=%s available=%d (call #%d)", request.sku, available, call_count)
        return inventory_pb2.GetStockReply(sku=request.sku, available=available)

    def GetStockBatch(self, request, context):
        global call_count
        call_count += 1
        items = []
        for sku in request.skus:
            available = STOCK.get(sku, 0)
            items.append(inventory_pb2.GetStockReply(sku=sku, available=available))
        log.info("GetStockBatch skus=%s (call #%d)", list(request.skus), call_count)
        return inventory_pb2.GetStockBatchReply(items=items)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    inventory_pb2_grpc.add_InventoryServicer_to_server(InventoryServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    log.info("inventory gRPC server listening on :50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
