import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("saga")

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://appuser:apppass@postgres:5432/appdb")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://lgtm:4318")
SHIPPING_FAIL = os.getenv("SHIPPING_FAIL", "false").lower() == "true"

resource = Resource.create({"service.name": "saga-orchestrator"})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTEL_ENDPOINT}/v1/traces")))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("saga")

db_pool: Optional[asyncpg.Pool] = None

STEPS = [
    {"name": "charge_payment", "compensate": "refund_payment"},
    {"name": "reserve_stock", "compensate": "release_stock"},
    {"name": "book_shipping", "compensate": "cancel_shipping"},
]


async def execute_step(step_name: str, context: dict) -> dict:
    if step_name == "charge_payment":
        payment_id = f"pay-{uuid.uuid4().hex[:8]}"
        log.info("charged payment %s for order %s", payment_id, context.get("order_id"))
        return {"payment_id": payment_id, "amount": context.get("total", 0)}

    if step_name == "reserve_stock":
        reservation_id = f"rsv-{uuid.uuid4().hex[:8]}"
        log.info("reserved stock %s for sku %s", reservation_id, context.get("sku"))
        return {"reservation_id": reservation_id, "sku": context.get("sku")}

    if step_name == "book_shipping":
        if SHIPPING_FAIL or context.get("fail_shipping"):
            raise RuntimeError("shipping service unavailable")
        shipment_id = f"shp-{uuid.uuid4().hex[:8]}"
        log.info("booked shipping %s", shipment_id)
        return {"shipment_id": shipment_id}

    if step_name == "refund_payment":
        log.info("refunded payment %s", context.get("charge_payment", {}).get("payment_id"))
        return {"refunded": True}

    if step_name == "release_stock":
        log.info("released stock %s", context.get("reserve_stock", {}).get("reservation_id"))
        return {"released": True}

    if step_name == "cancel_shipping":
        log.info("cancelled shipping %s", context.get("book_shipping", {}).get("shipment_id"))
        return {"cancelled": True}

    return {}


async def advance(saga_id: str):
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT id, status, step_index, context FROM sagas WHERE id=$1 FOR UPDATE",
                saga_id,
            )
            if not row or row["status"] != "RUNNING":
                return

            step_index = row["step_index"]
            context = json.loads(row["context"])

            if step_index >= len(STEPS):
                await conn.execute(
                    "UPDATE sagas SET status='COMPLETED', updated_at=now() WHERE id=$1",
                    saga_id,
                )
                return

            step = STEPS[step_index]
            with tracer.start_as_current_span(f"saga.{step['name']}") as span:
                span.set_attribute("saga.id", saga_id)
                span.set_attribute("saga.step", step["name"])
                try:
                    result = await execute_step(step["name"], context)
                    context[step["name"]] = result

                    await conn.execute(
                        "INSERT INTO saga_log (saga_id, step, action, result) VALUES ($1, $2, 'execute', $3)",
                        saga_id, step["name"], json.dumps(result),
                    )
                    await conn.execute(
                        "UPDATE sagas SET step_index=$1, context=$2, updated_at=now() WHERE id=$3",
                        step_index + 1, json.dumps(context), saga_id,
                    )
                except Exception as e:
                    log.error("step %s failed: %s — starting compensation", step["name"], e)
                    span.set_attribute("saga.failed", True)
                    await conn.execute(
                        "INSERT INTO saga_log (saga_id, step, action, result) VALUES ($1, $2, 'failed', $3)",
                        saga_id, step["name"], json.dumps({"error": str(e)}),
                    )
                    await conn.execute(
                        "UPDATE sagas SET status='COMPENSATING', updated_at=now() WHERE id=$1",
                        saga_id,
                    )

    row = await db_pool.fetchrow("SELECT status FROM sagas WHERE id=$1", saga_id)
    if row["status"] == "RUNNING":
        await advance(saga_id)
    elif row["status"] == "COMPENSATING":
        await compensate(saga_id)


async def compensate(saga_id: str):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT step_index, context FROM sagas WHERE id=$1", saga_id)
        step_index = row["step_index"]
        context = json.loads(row["context"])

        for i in range(step_index - 1, -1, -1):
            step = STEPS[i]
            comp_name = step["compensate"]
            with tracer.start_as_current_span(f"saga.{comp_name}") as span:
                span.set_attribute("saga.id", saga_id)
                span.set_attribute("saga.compensate", comp_name)
                result = await execute_step(comp_name, context)
                await conn.execute(
                    "INSERT INTO saga_log (saga_id, step, action, result) VALUES ($1, $2, 'compensate', $3)",
                    saga_id, comp_name, json.dumps(result),
                )

        await conn.execute(
            "UPDATE sagas SET status='COMPENSATED', updated_at=now() WHERE id=$1",
            saga_id,
        )
    log.info("saga %s fully compensated", saga_id)


class SagaIn(BaseModel):
    order_id: str = Field(min_length=1)
    sku: str = Field(min_length=1)
    total: float = Field(gt=0)
    fail_shipping: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    running = await db_pool.fetch("SELECT id FROM sagas WHERE status='RUNNING'")
    for row in running:
        log.info("resuming saga %s", row["id"])
        await advance(row["id"])
    log.info("saga-orchestrator started")
    yield
    await db_pool.close()


app = FastAPI(title="Saga Orchestrator", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/sagas", status_code=201)
async def create_saga(body: SagaIn):
    saga_id = str(uuid.uuid4())
    context = {"order_id": body.order_id, "sku": body.sku, "total": body.total}
    if body.fail_shipping:
        context["fail_shipping"] = True

    await db_pool.execute(
        "INSERT INTO sagas (id, status, step_index, context) VALUES ($1, 'RUNNING', 0, $2)",
        saga_id, json.dumps(context),
    )
    await advance(saga_id)

    row = await db_pool.fetchrow("SELECT id, status, step_index, context FROM sagas WHERE id=$1", saga_id)
    return {
        "id": row["id"],
        "status": row["status"],
        "step_index": row["step_index"],
        "context": json.loads(row["context"]),
    }


@app.get("/sagas/{saga_id}")
async def get_saga(saga_id: str):
    row = await db_pool.fetchrow("SELECT id, status, step_index, context FROM sagas WHERE id=$1", saga_id)
    if not row:
        return {"error": "not found"}, 404
    return {
        "id": row["id"],
        "status": row["status"],
        "step_index": row["step_index"],
        "context": json.loads(row["context"]),
    }


@app.get("/sagas/{saga_id}/log")
async def get_saga_log(saga_id: str):
    rows = await db_pool.fetch(
        "SELECT step, action, result, created_at FROM saga_log WHERE saga_id=$1 ORDER BY id",
        saga_id,
    )
    return [
        {"step": r["step"], "action": r["action"], "result": json.loads(r["result"]) if r["result"] else None}
        for r in rows
    ]
