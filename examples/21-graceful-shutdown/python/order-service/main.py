import asyncio
import logging
import os
import signal
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from fastapi import FastAPI
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("order")

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://appuser:apppass@postgres:5432/appdb")

db_pool: Optional[asyncpg.Pool] = None
shutting_down = False
in_flight = 0
in_flight_lock = asyncio.Lock()


class OrderIn(BaseModel):
    sku: str = Field(min_length=1)
    quantity: int = Field(gt=0)


def handle_sigterm(*_):
    global shutting_down
    shutting_down = True
    log.info("SIGTERM received — readiness flipped, draining in-flight requests")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    signal.signal(signal.SIGTERM, handle_sigterm)
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    log.info("order-service started (PID=%d)", os.getpid())
    yield
    log.info("waiting for in-flight requests to drain...")
    for _ in range(100):
        if in_flight == 0:
            break
        await asyncio.sleep(0.1)
    log.info("drained (in_flight=%d), closing DB pool", in_flight)
    await db_pool.close()
    log.info("order-service shutdown complete")


app = FastAPI(title="Order Service", lifespan=lifespan)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    if shutting_down:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"ready": False, "reason": "shutting down"})
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"ready": False, "reason": "db unreachable"})
    return {"ready": True}


@app.post("/orders", status_code=201)
async def place_order(body: OrderIn):
    global in_flight
    async with in_flight_lock:
        in_flight += 1
    try:
        if shutting_down:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=503, content={"error": "shutting down"})

        order_id = str(uuid.uuid4())
        async with db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, 'confirmed')",
                order_id, body.sku, body.quantity,
            )
        return {"id": order_id, "sku": body.sku, "quantity": body.quantity, "status": "confirmed"}
    finally:
        async with in_flight_lock:
            in_flight -= 1


@app.get("/orders")
async def list_orders():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT 50")
    return [dict(r) for r in rows]


@app.get("/debug/state")
async def debug_state():
    return {"shutting_down": shutting_down, "in_flight": in_flight, "pid": os.getpid()}
