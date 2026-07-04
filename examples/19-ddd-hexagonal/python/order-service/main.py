import logging
import os

import asyncpg
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from adapters.log_publisher import LogEventPublisher
from adapters.postgres_repo import PostgresOrderRepository
from adapters.rest_adapter import register_routes
from domain.service import PlaceOrder

logging.basicConfig(level=logging.INFO)

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.on_event("startup")
async def startup():
    dsn = os.environ.get("DATABASE_URL", "postgres://appuser:apppass@localhost:5432/appdb")
    app.state.pool = await asyncpg.create_pool(dsn)
    repo = PostgresOrderRepository(app.state.pool)
    publisher = LogEventPublisher()
    place_order = PlaceOrder(repo=repo, events=publisher)
    register_routes(app, place_order, repo)


@app.on_event("shutdown")
async def shutdown():
    await app.state.pool.close()
