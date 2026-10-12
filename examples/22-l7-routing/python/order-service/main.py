from fastapi import FastAPI
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_version: str = "v1"


settings = Settings()

app = FastAPI()


class OrderIn(BaseModel):
    sku: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "version": settings.app_version}


@app.post("/orders", status_code=201)
async def create_order(body: OrderIn):
    return {"id": "1", "sku": body.sku, "quantity": body.quantity, "version": settings.app_version}


@app.get("/orders")
async def list_orders():
    return {"orders": [], "version": settings.app_version}
