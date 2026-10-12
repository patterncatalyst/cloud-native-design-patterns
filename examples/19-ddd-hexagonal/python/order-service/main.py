import logging
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic_settings import BaseSettings
from starlette.responses import JSONResponse

from adapters.log_publisher import LogEventPublisher
from adapters.postgres_repo import PostgresOrderRepository
from adapters.rest_adapter import register_routes
from domain.service import PlaceOrder

logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    database_url: str = "postgres://appuser:apppass@localhost:5432/appdb"


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    dsn = settings.database_url
    app.state.pool = await asyncpg.create_pool(dsn)
    repo = PostgresOrderRepository(app.state.pool)
    publisher = LogEventPublisher()
    place_order = PlaceOrder(repo=repo, events=publisher)
    register_routes(app, place_order, repo)
    yield
    await app.state.pool.close()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})
