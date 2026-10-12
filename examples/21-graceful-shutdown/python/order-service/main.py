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
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("order")


class Settings(BaseSettings):
    database_url: str = "postgres://appuser:apppass@postgres:5432/appdb"
    drain_delay_seconds: float = 5.0


settings = Settings()

db_pool: Optional[asyncpg.Pool] = None
shutting_down = False
in_flight = 0
in_flight_lock = asyncio.Lock()


class OrderIn(BaseModel):
    sku: str = Field(min_length=1)
    quantity: int = Field(gt=0)


# uvicorn's own SIGTERM handler, saved when ours is installed: it starts uvicorn's graceful
# shutdown (stop accepting, finish open requests, then run the lifespan exit below).
uvicorn_sigterm = None
loop: Optional[asyncio.AbstractEventLoop] = None


def stop_server(signum, frame):
    log.info("shutting down HTTP server (in_flight=%d)", in_flight)
    uvicorn_sigterm(signum, frame)


def handle_sigterm(signum, frame):
    """One SIGTERM drives the whole drain: readiness flips now, uvicorn's shutdown starts after the delay."""
    global shutting_down
    if shutting_down:
        return  # already draining
    shutting_down = True
    log.info("SIGTERM received — readiness flipped, draining in-flight requests")
    log.info("waiting %.0fs for endpoints to update", settings.drain_delay_seconds)
    # Keep serving during the delay, then hand over to uvicorn (stop accepting, finish in-flight).
    loop.call_soon_threadsafe(loop.call_later, settings.drain_delay_seconds, stop_server, signum, frame)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, uvicorn_sigterm, loop
    loop = asyncio.get_running_loop()
    # uvicorn installs its handlers before the lifespan starts; keep it and chain to it.
    uvicorn_sigterm = signal.signal(signal.SIGTERM, handle_sigterm)
    db_pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
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
