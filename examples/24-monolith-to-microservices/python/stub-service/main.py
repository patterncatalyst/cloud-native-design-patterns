from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "unknown"


settings = Settings()

app = FastAPI()

orders: dict[str, dict] = {}
_counter = 0
_access_counts: dict[str, int] = {}


class OrderIn(BaseModel):
    sku: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    tenant: str = ""


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "source": settings.service_name}


@app.post("/orders", status_code=201)
async def create_order(body: OrderIn):
    global _counter
    _counter += 1
    oid = str(_counter)
    orders[oid] = {
        "id": oid,
        "sku": body.sku,
        "quantity": body.quantity,
        "tenant": body.tenant,
        "source": settings.service_name,
    }
    return orders[oid]


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    _access_counts[order_id] = _access_counts.get(order_id, 0) + 1
    if order_id not in orders:
        return {"id": order_id, "source": settings.service_name, "status": "stub"}
    return orders[order_id]


@app.get("/access-count/{order_id}")
async def access_count(order_id: str):
    return {"order_id": order_id, "count": _access_counts.get(order_id, 0)}
