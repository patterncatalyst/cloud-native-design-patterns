import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Query
from openfeature import api
from openfeature.evaluation_context import EvaluationContext
from openfeature.contrib.provider.flagd import FlagdProvider
from openfeature.contrib.provider.flagd.config import ResolverType

log = logging.getLogger("flag-service")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

FLAGD_HOST = os.getenv("FLAGD_HOST", "flagd")
FLAGD_PORT = int(os.getenv("FLAGD_PORT", "8013"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        provider = FlagdProvider(
            host=FLAGD_HOST,
            port=FLAGD_PORT,
            resolver_type=ResolverType.RPC,
        )
        api.set_provider(provider)
        log.info("OpenFeature provider set: flagd at %s:%d", FLAGD_HOST, FLAGD_PORT)
    except Exception:
        log.exception("Failed to connect to flagd — will use defaults")

    yield

    try:
        api.shutdown()
    except Exception:
        pass


app = FastAPI(lifespan=lifespan)


def _ctx(user_id: str, plan: str = "free", region: str = "us"):
    return EvaluationContext(
        targeting_key=user_id,
        attributes={"plan": plan, "region": region},
    )


# ---------------------------------------------------------------------------
# 1. Release flag — new-checkout (default off, enterprise always on, 25% rollout)
# ---------------------------------------------------------------------------
@app.post("/checkout")
async def checkout(
    x_user: str = Header(default="anonymous"),
    x_plan: str = Header(default="free"),
    x_region: str = Header(default="us"),
):
    client = api.get_client()
    ctx = _ctx(x_user, x_plan, x_region)
    use_new = client.get_boolean_value("new-checkout", False, ctx)

    if use_new:
        return {"path": "new", "user": x_user, "plan": x_plan}
    return {"path": "legacy", "user": x_user, "plan": x_plan}


# ---------------------------------------------------------------------------
# 2. Kill switch — recommendations-enabled (default on)
# ---------------------------------------------------------------------------
@app.get("/recommendations")
async def recommendations(
    x_user: str = Header(default="anonymous"),
):
    client = api.get_client()
    ctx = _ctx(x_user)
    enabled = client.get_boolean_value("recommendations-enabled", True, ctx)

    if not enabled:
        return {"recommendations": [], "reason": "killed"}
    return {
        "recommendations": ["product-a", "product-b", "product-c"],
        "reason": "live",
    }


# ---------------------------------------------------------------------------
# 3. Simple on/off flag — dark-mode
# ---------------------------------------------------------------------------
@app.get("/ui-config")
async def ui_config(
    x_user: str = Header(default="anonymous"),
):
    client = api.get_client()
    ctx = _ctx(x_user)
    dark = client.get_boolean_value("dark-mode", False, ctx)
    return {"dark_mode": dark, "user": x_user}


# ---------------------------------------------------------------------------
# 4. Evaluate all flags at once (for debug / verify)
# ---------------------------------------------------------------------------
@app.get("/flags")
async def all_flags(
    x_user: str = Header(default="anonymous"),
    x_plan: str = Header(default="free"),
):
    client = api.get_client()
    ctx = _ctx(x_user, x_plan)
    return {
        "new-checkout": client.get_boolean_value("new-checkout", False, ctx),
        "dark-mode": client.get_boolean_value("dark-mode", False, ctx),
        "recommendations-enabled": client.get_boolean_value(
            "recommendations-enabled", True, ctx
        ),
        "user": x_user,
        "plan": x_plan,
    }


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
