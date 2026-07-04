import asyncio
import logging
import random
import time

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

log = logging.getLogger("backend")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

app = FastAPI()

mode = "healthy"
call_count = 0


class ModeIn(BaseModel):
    mode: str


@app.post("/mode")
async def set_mode(body: ModeIn):
    global mode, call_count
    if body.mode not in ("healthy", "slow", "failing", "flaky"):
        raise HTTPException(400, "mode must be healthy|slow|failing|flaky")
    mode = body.mode
    call_count = 0
    return {"mode": mode}


@app.get("/mode")
async def get_mode():
    return {"mode": mode, "call_count": call_count}


@app.get("/process")
async def process(
    request: Request,
    x_deadline_ms: str = Header(default=None),
):
    global call_count
    call_count += 1

    if x_deadline_ms is not None:
        remaining = int(x_deadline_ms)
        if remaining < 100:
            log.info("deadline too small (%dms), refusing", remaining)
            return {
                "status": "rejected",
                "reason": "deadline_too_small",
                "remaining_ms": remaining,
            }

    if mode == "slow":
        await asyncio.sleep(5)
        return {"status": "ok", "mode": mode, "delay": 5}

    if mode == "failing":
        raise HTTPException(500, "backend error")

    if mode == "flaky":
        if random.random() < 0.5:
            raise HTTPException(500, "backend error (flaky)")
        return {"status": "ok", "mode": mode}

    return {"status": "ok", "mode": mode}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
