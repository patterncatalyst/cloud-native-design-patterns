import logging
import os
from concurrent import futures

import grpc
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

import inventory_pb2
import inventory_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("inventory")

OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318")
INITIAL_STOCK = int(os.getenv("INITIAL_STOCK", "100"))

resource = Resource.create({"service.name": "inventory-service"})

tp = TracerProvider(resource=resource)
tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces")))
trace.set_tracer_provider(tp)

reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=f"{OTEL_ENDPOINT}/v1/metrics"), export_interval_millis=5000)
mp = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(mp)
meter = metrics.get_meter("inventory-service")
reservations_counter = meter.create_counter("stock.reservations", description="Stock reservation attempts")

GrpcInstrumentorServer().instrument()

stock = {}


class InventoryServicer(inventory_pb2_grpc.InventoryServiceServicer):
    def ReserveStock(self, request, context):
        if request.sku not in stock:
            stock[request.sku] = INITIAL_STOCK

        confirmed = stock[request.sku] >= request.quantity
        if confirmed:
            stock[request.sku] -= request.quantity

        reservations_counter.add(1, {"sku": request.sku, "confirmed": str(confirmed)})
        log.info("ReserveStock sku=%s qty=%d confirmed=%s remaining=%d",
                 request.sku, request.quantity, confirmed, stock[request.sku])

        return inventory_pb2.ReserveResponse(
            confirmed=confirmed,
            remaining=stock[request.sku],
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(InventoryServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    log.info("inventory-service started on :50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
