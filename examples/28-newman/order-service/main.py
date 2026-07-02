import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

log = logging.getLogger("order-service")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://appuser:apppass@postgres:5432/appdb")

pool: asyncpg.Pool


class OrderIn(BaseModel):
    sku: str = Field(min_length=1)
    quantity: int = Field(gt=0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    yield
    await pool.close()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "details": str(exc)},
    )


@app.post("/orders", status_code=201)
async def create_order(body: OrderIn):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO orders (sku, quantity) VALUES ($1, $2) RETURNING id, sku, quantity, status, created_at",
            body.sku,
            body.quantity,
        )
    return {
        "id": row["id"],
        "sku": row["sku"],
        "quantity": row["quantity"],
        "status": row["status"],
    }


@app.get("/orders/{order_id}")
async def get_order(order_id: int):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, sku, quantity, status FROM orders WHERE id = $1", order_id
        )
    if not row:
        raise HTTPException(404, "order not found")
    return dict(row)


@app.get("/orders")
async def list_orders():
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, sku, quantity, status FROM orders ORDER BY id")
    return [dict(r) for r in rows]


@app.delete("/orders/{order_id}", status_code=204)
async def cancel_order(order_id: int):
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE orders SET status = 'cancelled' WHERE id = $1 AND status = 'placed'",
            order_id,
        )
    if result == "UPDATE 0":
        raise HTTPException(404, "order not found or already cancelled")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
