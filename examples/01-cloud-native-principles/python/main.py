import asyncio
import logging
import os

import asyncpg
from fastapi import FastAPI
from pydantic_settings import BaseSettings
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


class Settings(BaseSettings):
    database_url: str
    kafka_bootstrap: str = ""
    service_version: str = "0.0.0"


settings = Settings()
app = FastAPI(title="order-service", version=settings.service_version)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("order-service")

pool: asyncpg.Pool | None = None


@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
    log.info(
        "started version=%s db=%s kafka=%s",
        settings.service_version,
        settings.database_url.split("@")[-1],
        settings.kafka_bootstrap or "(not configured)",
    )


@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()
    log.info("shutdown complete")


@app.get("/healthz")
def healthz():
    """Liveness — is the process up? Never checks dependencies."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    """Readiness — are dependencies reachable? Fails when DB is down."""
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        return {"status": "down", "checks": {"database": "unreachable"}}
    return {"status": "ready", "checks": {"database": "ok"}}


@app.get("/")
async def root():
    return {
        "service": "order-service",
        "version": settings.service_version,
        "config_source": "environment",
    }


@app.get("/orders")
async def list_orders():
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, customer, total FROM orders ORDER BY id")
    return [dict(r) for r in rows]


@app.post("/orders")
async def create_order(customer: str, total: float):
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO orders (customer, total) VALUES ($1, $2) RETURNING id, customer, total",
            customer,
            total,
        )
    log.info("order_created id=%s customer=%s total=%.2f", row["id"], customer, total)
    return dict(row)


FastAPIInstrumentor.instrument_app(app)
