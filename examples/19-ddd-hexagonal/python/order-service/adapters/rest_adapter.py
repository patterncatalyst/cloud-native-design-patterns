from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from domain.models import Order, PlaceOrderCmd
from domain.ports import OrderRepository
from domain.service import PlaceOrder


class OrderIn(BaseModel):
    sku: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)

    def to_cmd(self) -> PlaceOrderCmd:
        return PlaceOrderCmd(sku=self.sku, quantity=self.quantity)


class OrderOut(BaseModel):
    id: str
    sku: str
    quantity: int
    status: str


def _to_out(o: Order) -> dict:
    return OrderOut(id=o.id, sku=o.sku, quantity=o.quantity, status=o.status).model_dump()


def register_routes(app: FastAPI, place_order: PlaceOrder, repo: OrderRepository):
    @app.post("/orders", status_code=201)
    async def create_order(body: OrderIn):
        order = await place_order(body.to_cmd())
        return _to_out(order)

    @app.get("/orders/{order_id}")
    async def get_order(order_id: str):
        order = await repo.find_by_id(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="not found")
        return _to_out(order)

    @app.get("/orders")
    async def list_orders():
        orders = await repo.list_all()
        return [_to_out(o) for o in orders]

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}
