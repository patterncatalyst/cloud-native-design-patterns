import logging
import os
import uuid
from contextlib import asynccontextmanager

import grpc
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel, Field

import inventory_pb2
import inventory_pb2_grpc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("order")

INVENTORY_ADDR = os.getenv("INVENTORY_ADDR", "inventory:50051")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318")

resource = Resource.create({"service.name": "order-service"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces")))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("order-service")


def get_trace_id() -> str:
    span = trace.get_current_span()
    ctx = span.get_span_context()
    return format(ctx.trace_id, "032x") if ctx.trace_id else None


def problem_response(status: int, code: str, message: str, retryable: bool = False,
                     retry_after: int = None, details: list = None) -> JSONResponse:
    body = {
        "type": f"urn:error:{code.lower().replace('_', '-')}",
        "title": message,
        "status": status,
        "code": code,
        "traceId": get_trace_id(),
        "retryable": retryable,
    }
    if retry_after is not None:
        body["retryAfter"] = retry_after
    if details:
        body["details"] = details
    headers = {"Content-Type": "application/problem+json"}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(status_code=status, content=body, headers=headers)


class OrderIn(BaseModel):
    sku: str = Field(min_length=1)
    quantity: int = Field(gt=0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("order-service started")
    yield


app = FastAPI(title="Order Service", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors = [{"field": ".".join(str(l) for l in e["loc"]), "message": e["msg"]} for e in exc.errors()]
    return problem_response(
        status=422,
        code="VALIDATION_ERROR",
        message="request validation failed",
        details=errors,
    )


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/orders", status_code=201)
async def place_order(body: OrderIn):
    order_id = str(uuid.uuid4())

    try:
        async with grpc.aio.insecure_channel(INVENTORY_ADDR) as channel:
            stub = inventory_pb2_grpc.InventoryServiceStub(channel)
            resp = await stub.ReserveStock(
                inventory_pb2.ReserveRequest(sku=body.sku, quantity=body.quantity)
            )
    except grpc.aio.AioRpcError as e:
        if e.code() == grpc.StatusCode.UNAVAILABLE:
            return problem_response(
                status=503,
                code="INVENTORY_UNAVAILABLE",
                message="inventory service is temporarily unavailable",
                retryable=True,
                retry_after=2,
            )
        if e.code() == grpc.StatusCode.FAILED_PRECONDITION:
            return problem_response(
                status=409,
                code="STOCK_UNAVAILABLE",
                message=e.details(),
                retryable=False,
            )
        return problem_response(
            status=502,
            code="UPSTREAM_ERROR",
            message="unexpected error from inventory service",
            retryable=True,
            retry_after=5,
        )

    if not resp.confirmed:
        return problem_response(
            status=409,
            code="STOCK_UNAVAILABLE",
            message=f"insufficient stock for {body.sku}",
            retryable=False,
        )

    return {
        "id": order_id,
        "sku": body.sku,
        "quantity": body.quantity,
        "status": "confirmed",
        "remaining_stock": resp.remaining,
    }
