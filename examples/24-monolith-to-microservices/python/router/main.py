import os

import httpx
from fastapi import FastAPI, Request
from starlette.responses import Response

app = FastAPI()

MONOLITH_URL = os.environ.get("MONOLITH_URL", "http://monolith:8080")
NEW_SERVICE_URL = os.environ.get("NEW_SERVICE_URL", "http://new-service:8080")
client = httpx.AsyncClient(timeout=5.0)

routes: dict = {
    "tenant_routes": {"acme": "new-service"},
    "default": "monolith",
}


def _resolve_upstream(tenant: str) -> str:
    target = routes["tenant_routes"].get(tenant, routes["default"])
    if target == "new-service":
        return NEW_SERVICE_URL
    return MONOLITH_URL


@app.api_route("/orders", methods=["POST"])
async def route_post(request: Request):
    body = await request.body()
    import json

    payload = json.loads(body) if body else {}
    tenant = payload.get("tenant", "")
    upstream = _resolve_upstream(tenant)
    r = await client.request(
        request.method,
        f"{upstream}/orders",
        content=body,
        headers={"content-type": "application/json"},
    )
    return Response(content=r.content, status_code=r.status_code)


@app.get("/orders/{order_id}")
async def route_get(order_id: str, tenant: str = ""):
    upstream = _resolve_upstream(tenant)
    r = await client.get(f"{upstream}/orders/{order_id}")
    return Response(content=r.content, status_code=r.status_code)


@app.get("/rules")
async def get_rules():
    return routes


@app.put("/rules")
async def update_rules(new_rules: dict):
    routes.update(new_rules)
    return routes


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
