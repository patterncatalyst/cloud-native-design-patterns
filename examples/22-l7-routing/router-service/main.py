import logging

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()
logger = logging.getLogger("router")
logging.basicConfig(level=logging.INFO)

rules = {
    "vip_threshold": 1000,
    "priority_topic": "orders.priority",
    "default_topic": "orders.default",
}


class OrderIn(BaseModel):
    sku: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    amount: float = Field(..., gt=0)


@app.post("/orders", status_code=201)
async def route_order(body: OrderIn):
    if body.amount >= rules["vip_threshold"]:
        topic = rules["priority_topic"]
        logger.info("ROUTED sku=%s amount=%.2f -> %s (VIP)", body.sku, body.amount, topic)
        return {"routed_to": topic, "vip": True, "amount": body.amount}
    topic = rules["default_topic"]
    logger.info("ROUTED sku=%s amount=%.2f -> %s", body.sku, body.amount, topic)
    return {"routed_to": topic, "vip": False, "amount": body.amount}


@app.get("/rules")
async def get_rules():
    return rules


@app.put("/rules")
async def update_rules(new_rules: dict):
    rules.update(new_rules)
    logger.info("RULES_UPDATED %s", rules)
    return rules


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
