import logging
import os
from concurrent import futures

import grpc
from grpc_status import rpc_status
from google.protobuf import any_pb2, duration_pb2
from google.rpc import status_pb2, error_details_pb2

import inventory_pb2
import inventory_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("inventory")

INITIAL_STOCK = int(os.getenv("INITIAL_STOCK", "10"))
FAIL_MODE = os.getenv("FAIL_MODE", "none")

stock = {}


class InventoryServicer(inventory_pb2_grpc.InventoryServiceServicer):
    def ReserveStock(self, request, context):
        if FAIL_MODE == "unavailable":
            retry_info = error_details_pb2.RetryInfo(
                retry_delay=duration_pb2.Duration(seconds=2)
            )
            detail = any_pb2.Any()
            detail.Pack(retry_info)
            rich_status = status_pb2.Status(
                code=grpc.StatusCode.UNAVAILABLE.value[0],
                message="inventory service temporarily unavailable",
                details=[detail],
            )
            context.abort_with_status(rpc_status.to_status(rich_status))
            return inventory_pb2.ReserveResponse()

        if request.sku not in stock:
            stock[request.sku] = INITIAL_STOCK

        if stock[request.sku] < request.quantity:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details(f"insufficient stock for {request.sku}: have {stock[request.sku]}, need {request.quantity}")
            return inventory_pb2.ReserveResponse(confirmed=False, remaining=stock[request.sku])

        stock[request.sku] -= request.quantity
        log.info("reserved sku=%s qty=%d remaining=%d", request.sku, request.quantity, stock[request.sku])
        return inventory_pb2.ReserveResponse(confirmed=True, remaining=stock[request.sku])


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(InventoryServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    log.info("inventory-service started on :50051 (stock=%d, fail_mode=%s)", INITIAL_STOCK, FAIL_MODE)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
