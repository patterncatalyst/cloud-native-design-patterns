import asyncio
import hashlib
import hmac
import os
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

VALET_SECRET = os.environ.get("VALET_SECRET", "demo-secret-do-not-use-in-prod")

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# -------------------------------------------------------------------
# 1. Sidecar trust middleware — deny without validated identity
# -------------------------------------------------------------------
OPEN_PATHS = {"/healthz", "/docs", "/openapi.json"}


@app.middleware("http")
async def trust_sidecar(request: Request, call_next):
    if request.url.path in OPEN_PATHS:
        return await call_next(request)
    spiffe = request.headers.get("x-forwarded-client-cert")
    if spiffe is None:
        return JSONResponse(
            status_code=403, content={"detail": "no validated identity"}
        )
    request.state.identity = spiffe
    request.state.subject = request.headers.get("x-jwt-claim-sub", "anonymous")
    return await call_next(request)


# -------------------------------------------------------------------
# 2. Per-tenant bulkhead — bounded concurrency per tenant
# -------------------------------------------------------------------
BULKHEAD_LIMIT = 5
_sems: dict[str, asyncio.Semaphore] = {}


def _tenant_sem(tenant: str) -> asyncio.Semaphore:
    return _sems.setdefault(tenant, asyncio.Semaphore(BULKHEAD_LIMIT))


# -------------------------------------------------------------------
# 3. Valet key — mint signed, time-bound, operation-restricted tokens
# -------------------------------------------------------------------
def _mint_valet(resource: str, operation: str, ttl: int = 300) -> dict:
    expires = int(time.time()) + ttl
    payload = f"{resource}:{operation}:{expires}"
    sig = hmac.new(VALET_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return {"resource": resource, "operation": operation, "expires": expires, "token": sig}


def _verify_valet(resource: str, operation: str, expires: int, token: str) -> bool:
    if time.time() > expires:
        return False
    payload = f"{resource}:{operation}:{expires}"
    expected = hmac.new(
        VALET_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(token, expected)


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
orders: dict[str, dict] = {}
_counter = 0


class OrderIn(BaseModel):
    sku: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    tenant: str = Field(..., min_length=1)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/orders", status_code=201)
async def create_order(body: OrderIn, request: Request):
    global _counter
    async with _tenant_sem(body.tenant):
        await asyncio.sleep(0.01)
        _counter += 1
        oid = str(_counter)
        orders[oid] = {
            "id": oid,
            "sku": body.sku,
            "quantity": body.quantity,
            "tenant": body.tenant,
            "identity": request.state.identity,
            "subject": request.state.subject,
        }
        return orders[oid]


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="not found")
    return orders[order_id]


@app.post("/valet-key")
async def mint_key(resource: str, operation: str = "GET"):
    return _mint_valet(resource, operation)


@app.get("/verify-valet")
async def verify_key(resource: str, operation: str, expires: int, token: str):
    if _verify_valet(resource, operation, expires, token):
        return {"valid": True, "resource": resource, "operation": operation}
    raise HTTPException(status_code=403, detail="invalid or expired valet key")


@app.get("/bulkhead-state")
async def bulkhead_state():
    return {
        t: {"available": sem._value, "capacity": BULKHEAD_LIMIT}
        for t, sem in _sems.items()
    }
