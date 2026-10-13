import asyncio
import logging
import time
from contextlib import asynccontextmanager

import httpx
import pybreaker
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic_settings import BaseSettings
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

log = logging.getLogger("edge")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


class Settings(BaseSettings):
    backend_url: str = "http://backend:8081"


settings = Settings()

# Circuit breaker: 5 failed calls open it, it stays open 10 s, then 2 successful trial calls close it.
# throw_new_error_on_trip=False keeps the real cause on the call that trips it.
breaker = pybreaker.CircuitBreaker(
    fail_max=5, reset_timeout=10, success_threshold=2, throw_new_error_on_trip=False, name="backend"
)

# Bulkhead: at most 5 calls in flight; a sixth is turned away at once.
BULKHEAD = 5
bulkhead = asyncio.Semaphore(BULKHEAD)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # One client for the process; every call gives up after 2 s (0.5 s to connect).
    async with httpx.AsyncClient(base_url=settings.backend_url, timeout=httpx.Timeout(2.0, connect=0.5)) as client:
        app.state.client = client
        yield


app = FastAPI(lifespan=lifespan)


def client() -> httpx.AsyncClient:
    return app.state.client


def elapsed_s(start: float) -> float:
    return round(time.monotonic() - start, 2)


# 1. No timeout: shows what goes wrong
@app.get("/no-timeout")
async def no_timeout():
    start = time.monotonic()
    try:
        r = await client().get("/process", timeout=None)
        return {"status": r.status_code, "elapsed_s": elapsed_s(start), "body": r.json()}
    except httpx.HTTPError as e:
        return {"error": str(e), "elapsed_s": elapsed_s(start)}


# 2. Timeout: fails fast on a slow downstream
@app.get("/with-timeout")
async def with_timeout():
    start = time.monotonic()
    try:
        r = await client().get("/process")
        return {"status": r.status_code, "elapsed_s": elapsed_s(start), "body": r.json()}
    except httpx.TimeoutException:
        return {"error": "timeout", "elapsed_s": elapsed_s(start), "pattern": "timeout"}


# 3. Retry with exponential backoff and jitter (tenacity): 3 attempts, 100 ms doubling to 2 s
@app.get("/with-retry")
async def with_retry():
    start = time.monotonic()
    attempts = 0
    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=0.1, max=2.0, jitter=0.05),
            retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
            reraise=True,
        ):
            with attempt:
                attempts = attempt.retry_state.attempt_number
                r = await client().get("/process")
                r.raise_for_status()
        return {"status": r.status_code, "attempts": attempts, "elapsed_s": elapsed_s(start), "body": r.json()}
    except (httpx.HTTPStatusError, httpx.TransportError) as e:
        error = f"HTTP {e.response.status_code}" if isinstance(e, httpx.HTTPStatusError) else "timeout"
        return {"error": error, "attempts": attempts, "elapsed_s": elapsed_s(start), "pattern": "retry-exhausted"}


# 4. Circuit breaker with a fallback (pybreaker)
@app.get("/with-breaker")
async def with_breaker():
    try:
        with breaker.calling():
            r = await client().get("/process")
            r.raise_for_status()
        return {"source": "live", "body": r.json(), "breaker": breaker.current_state}
    except pybreaker.CircuitBreakerError:
        reason = "circuit_open"
    except httpx.HTTPStatusError as e:
        reason = f"upstream_{e.response.status_code}"
    except httpx.TransportError:
        reason = "upstream_unreachable"
    return {"source": "fallback", "reason": reason, "breaker": breaker.current_state}


# 5. Deadline propagation: the backend gets what is left of the caller's budget
@app.get("/with-deadline")
async def with_deadline(budget_ms: int = Query(default=1000)):
    start = time.monotonic()
    remaining = budget_ms - 50  # edge overhead

    if remaining < 50:
        return {
            "error": "deadline_exceeded",
            "reason": "insufficient budget at edge",
            "budget_ms": budget_ms,
            "remaining_ms": remaining,
        }

    try:
        r = await client().get(
            "/process",
            headers={"X-Deadline-Ms": str(remaining)},
            timeout=httpx.Timeout(remaining / 1000.0, connect=0.5),
        )
        return {
            "status": r.status_code,
            "budget_ms": budget_ms,
            "remaining_ms": remaining,
            "elapsed_s": elapsed_s(start),
            "body": r.json(),
        }
    except httpx.TimeoutException:
        return {
            "error": "deadline_exceeded",
            "reason": "timed out waiting for backend",
            "budget_ms": budget_ms,
            "elapsed_s": elapsed_s(start),
        }


# 6. Bulkhead: bounded concurrency, the overflow refused with 429
@app.get("/with-bulkhead")
async def with_bulkhead():
    if bulkhead.locked():
        return JSONResponse({"error": "bulkhead_full", "pattern": "bulkhead"}, status_code=429)
    async with bulkhead:
        try:
            r = await client().get("/process")
            return {"status": r.status_code, "body": r.json()}
        except httpx.TimeoutException:
            return {"error": "timeout"}


# State endpoints
@app.get("/breaker-state")
async def breaker_state():
    return {"name": breaker.name, "state": breaker.current_state, "fail_counter": breaker.fail_counter}


@app.get("/bulkhead-state")
async def bulkhead_state():
    return {"max_concurrent": BULKHEAD, "full": bulkhead.locked()}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
