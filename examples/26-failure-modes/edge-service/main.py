import asyncio
import logging
import os
import random
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Query

log = logging.getLogger("edge")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

BACKEND = os.getenv("BACKEND_URL", "http://backend:8081")


# ---------------------------------------------------------------------------
# Circuit breaker — hand-rolled for transparent state observation
# ---------------------------------------------------------------------------
class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"

    def __init__(self, name, threshold=5, reset_timeout=10):
        self.name = name
        self.state = self.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self.opened_at = 0.0
        self.total_calls = 0
        self.total_rejected = 0

    def allow(self):
        if self.state == self.CLOSED:
            return True
        if self.state == self.OPEN:
            if time.monotonic() - self.opened_at >= self.reset_timeout:
                self.state = self.HALF_OPEN
                self.success_count = 0
                log.info("breaker [%s] → half-open", self.name)
                return True
            return False
        return True

    def record_success(self):
        self.total_calls += 1
        if self.state == self.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 2:
                self.state = self.CLOSED
                self.failure_count = 0
                log.info("breaker [%s] → closed (recovered)", self.name)
        else:
            self.failure_count = 0

    def record_failure(self):
        self.total_calls += 1
        self.failure_count += 1
        if self.state == self.HALF_OPEN:
            self.state = self.OPEN
            self.opened_at = time.monotonic()
            log.info("breaker [%s] → open (half-open trial failed)", self.name)
        elif self.failure_count >= self.threshold:
            self.state = self.OPEN
            self.opened_at = time.monotonic()
            log.info("breaker [%s] → open (threshold reached)", self.name)

    def info(self):
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "threshold": self.threshold,
            "total_calls": self.total_calls,
            "total_rejected": self.total_rejected,
        }


breaker = CircuitBreaker("backend", threshold=5, reset_timeout=10)

# ---------------------------------------------------------------------------
# Bulkhead — bounded concurrency via semaphore
# ---------------------------------------------------------------------------
bulkhead = asyncio.Semaphore(5)
bulkhead_rejected = 0
bulkhead_active = 0


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)


# ---------------------------------------------------------------------------
# 1. No timeout — shows what goes wrong
# ---------------------------------------------------------------------------
@app.get("/no-timeout")
async def no_timeout():
    start = time.monotonic()
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BACKEND}/process", timeout=None)
            elapsed = time.monotonic() - start
            return {"status": r.status_code, "elapsed_s": round(elapsed, 2), "body": r.json()}
    except Exception as e:
        elapsed = time.monotonic() - start
        return {"error": str(e), "elapsed_s": round(elapsed, 2)}


# ---------------------------------------------------------------------------
# 2. With timeout — fails fast on slow downstream
# ---------------------------------------------------------------------------
@app.get("/with-timeout")
async def with_timeout():
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=0.5)) as client:
            r = await client.get(f"{BACKEND}/process")
            elapsed = time.monotonic() - start
            return {"status": r.status_code, "elapsed_s": round(elapsed, 2), "body": r.json()}
    except httpx.TimeoutException:
        elapsed = time.monotonic() - start
        return {"error": "timeout", "elapsed_s": round(elapsed, 2), "pattern": "timeout"}


# ---------------------------------------------------------------------------
# 3. With retry + exponential backoff + jitter
# ---------------------------------------------------------------------------
@app.get("/with-retry")
async def with_retry():
    start = time.monotonic()
    attempts = 0
    last_error = None
    wait = 0.1

    async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=0.5)) as client:
        for attempt in range(1, 4):
            attempts = attempt
            try:
                r = await client.get(f"{BACKEND}/process")
                if r.status_code < 500:
                    elapsed = time.monotonic() - start
                    return {
                        "status": r.status_code,
                        "attempts": attempts,
                        "elapsed_s": round(elapsed, 2),
                        "body": r.json(),
                    }
                last_error = f"HTTP {r.status_code}"
            except httpx.TimeoutException:
                last_error = "timeout"

            if attempt < 3:
                jitter = random.uniform(0, wait * 0.5)
                await asyncio.sleep(wait + jitter)
                wait = min(wait * 2, 2.0)

    elapsed = time.monotonic() - start
    return {
        "error": last_error,
        "attempts": attempts,
        "elapsed_s": round(elapsed, 2),
        "pattern": "retry-exhausted",
    }


# ---------------------------------------------------------------------------
# 4. With circuit breaker + fallback
# ---------------------------------------------------------------------------
@app.get("/with-breaker")
async def with_breaker():
    if not breaker.allow():
        breaker.total_rejected += 1
        return {
            "source": "fallback",
            "reason": "circuit_open",
            "breaker": breaker.state,
        }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=0.5)) as client:
            r = await client.get(f"{BACKEND}/process")
            if r.status_code >= 500:
                breaker.record_failure()
                return {
                    "source": "fallback",
                    "reason": f"upstream_{r.status_code}",
                    "breaker": breaker.state,
                }
            breaker.record_success()
            return {"source": "live", "body": r.json(), "breaker": breaker.state}
    except (httpx.TimeoutException, httpx.ConnectError):
        breaker.record_failure()
        return {
            "source": "fallback",
            "reason": "upstream_unreachable",
            "breaker": breaker.state,
        }


# ---------------------------------------------------------------------------
# 5. Deadline propagation
# ---------------------------------------------------------------------------
@app.get("/with-deadline")
async def with_deadline(budget_ms: int = Query(default=1000)):
    start = time.monotonic()
    edge_overhead = 50
    remaining = budget_ms - edge_overhead

    if remaining < 50:
        return {
            "error": "deadline_exceeded",
            "reason": "insufficient budget at edge",
            "budget_ms": budget_ms,
            "remaining_ms": remaining,
        }

    try:
        timeout_s = remaining / 1000.0
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s, connect=0.5)) as client:
            r = await client.get(
                f"{BACKEND}/process",
                headers={"X-Deadline-Ms": str(remaining)},
            )
            elapsed = time.monotonic() - start
            return {
                "status": r.status_code,
                "budget_ms": budget_ms,
                "remaining_ms": remaining,
                "elapsed_s": round(elapsed, 2),
                "body": r.json(),
            }
    except httpx.TimeoutException:
        elapsed = time.monotonic() - start
        return {
            "error": "deadline_exceeded",
            "reason": "timed out waiting for backend",
            "budget_ms": budget_ms,
            "elapsed_s": round(elapsed, 2),
        }


# ---------------------------------------------------------------------------
# 6. Bulkhead — bounded concurrency
# ---------------------------------------------------------------------------
@app.get("/with-bulkhead")
async def with_bulkhead():
    global bulkhead_rejected, bulkhead_active

    if bulkhead.locked():
        bulkhead_rejected += 1
        return {"error": "bulkhead_full", "pattern": "bulkhead", "active": bulkhead_active}

    try:
        await asyncio.wait_for(bulkhead.acquire(), timeout=0.01)
    except asyncio.TimeoutError:
        bulkhead_rejected += 1
        return {"error": "bulkhead_full", "pattern": "bulkhead", "active": bulkhead_active}

    bulkhead_active += 1
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=0.5)) as client:
            r = await client.get(f"{BACKEND}/process")
            return {"status": r.status_code, "body": r.json(), "active_slots": bulkhead_active}
    except httpx.TimeoutException:
        return {"error": "timeout", "active_slots": bulkhead_active}
    finally:
        bulkhead_active -= 1
        bulkhead.release()


# ---------------------------------------------------------------------------
# State endpoints
# ---------------------------------------------------------------------------
@app.get("/breaker-state")
async def breaker_state():
    return breaker.info()


@app.get("/bulkhead-state")
async def bulkhead_state():
    return {
        "max_concurrent": 5,
        "active": bulkhead_active,
        "rejected": bulkhead_rejected,
    }


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
