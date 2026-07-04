import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

VERSION = os.environ.get("APP_VERSION", "v1")

app = FastAPI()


class OrderIn(BaseModel):
    sku: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "version": VERSION}


@app.post("/orders", status_code=201)
async def create_order(body: OrderIn):
    return {"id": "1", "sku": body.sku, "quantity": body.quantity, "version": VERSION}


@app.get("/orders")
async def list_orders():
    return {"orders": [], "version": VERSION}
