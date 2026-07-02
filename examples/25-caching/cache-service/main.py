import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

log = logging.getLogger("cache-service")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

DATABASE_URL = os.getenv("DATABASE_URL", "postgres://appuser:apppass@postgres:5432/appdb")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
TTL = 60

pool: asyncpg.Pool
cache: aioredis.Redis


class ProductIn(BaseModel):
    name: str
    price_cents: int


class EventIn(BaseModel):
    id: str
    type: str
    payload: dict = {}


class MetricIn(BaseModel):
    value: float
    tags: dict = {}


# ---------------------------------------------------------------------------
# Read-through wrapper
# ---------------------------------------------------------------------------
class ReadThrough:
    def __init__(self, redis_client, loader, ttl=60, prefix=""):
        self.redis = redis_client
        self.loader = loader
        self.ttl = ttl
        self.prefix = prefix

    async def get(self, id: str) -> Optional[dict]:
        key = f"{self.prefix}{id}"
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        value = await self.loader(id)
        if value is not None:
            await self.redis.setex(key, self.ttl, json.dumps(value))
        return value


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------
FLUSH_BATCH = 100
FLUSH_PERIOD = 1.0
REFRESH_BEFORE_S = 10


async def flusher():
    """Write-back flusher: drain dirty set to Postgres in batches."""
    while True:
        await asyncio.sleep(FLUSH_PERIOD)
        try:
            ids = await cache.spop("metric:dirty", FLUSH_BATCH)
            if not ids:
                continue
            async with pool.acquire() as conn:
                for mid_b in ids:
                    mid = mid_b if isinstance(mid_b, str) else mid_b.decode()
                    data = await cache.hgetall(f"metric:{mid}")
                    if data:
                        payload = {
                            (k if isinstance(k, str) else k.decode()): (
                                v if isinstance(v, str) else v.decode()
                            )
                            for k, v in data.items()
                        }
                        await conn.execute(
                            "INSERT INTO metrics (id, payload) VALUES ($1, $2) "
                            "ON CONFLICT (id) DO UPDATE SET payload = $2, ts = NOW()",
                            mid,
                            json.dumps(payload),
                        )
                log.info("flusher: persisted %d metrics", len(ids))
        except Exception:
            log.exception("flusher error")


async def refresher():
    """Refresh-ahead: re-warm hot keys before their TTL fires."""
    while True:
        await asyncio.sleep(5)
        try:
            cutoff = time.time() - 300
            await cache.zremrangebyscore("product:hot", 0, cutoff)
            hot_ids = await cache.zrange("product:hot", 0, -1)
            for pid_b in hot_ids:
                pid = pid_b if isinstance(pid_b, str) else pid_b.decode()
                ttl_val = await cache.ttl(f"ra:product:{pid}")
                if 0 < ttl_val < REFRESH_BEFORE_S:
                    async with pool.acquire() as conn:
                        row = await conn.fetchrow(
                            "SELECT id, name, price_cents FROM products WHERE id=$1", pid
                        )
                        if row:
                            await cache.setex(
                                f"ra:product:{pid}",
                                TTL,
                                json.dumps(dict(row)),
                            )
                            log.info("refresher: pre-warmed %s", pid)
        except Exception:
            log.exception("refresher error")


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool, cache
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    cache = aioredis.from_url(REDIS_URL, decode_responses=False)

    flush_task = asyncio.create_task(flusher())
    refresh_task = asyncio.create_task(refresher())

    yield

    flush_task.cancel()
    refresh_task.cancel()
    await cache.aclose()
    await pool.close()


app = FastAPI(lifespan=lifespan)


# ---------------------------------------------------------------------------
# Helper: try cache, fall back to DB on Redis failure
# ---------------------------------------------------------------------------
async def safe_cache_get(key: str) -> Optional[bytes]:
    try:
        return await cache.get(key)
    except Exception:
        return None


async def safe_cache_set(key: str, value: str, ttl: int = TTL):
    try:
        await cache.setex(key, ttl, value)
    except Exception:
        pass


async def safe_cache_delete(key: str):
    try:
        await cache.delete(key)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 1. Cache-aside
# ---------------------------------------------------------------------------
@app.get("/cache-aside/products/{pid}")
async def cache_aside_get(pid: str):
    key = f"ca:product:{pid}"
    cached = await safe_cache_get(key)
    if cached:
        return {"source": "cache", **json.loads(cached)}

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, price_cents FROM products WHERE id=$1", pid
        )
    if not row:
        raise HTTPException(404, "not found")
    data = dict(row)
    await safe_cache_set(key, json.dumps(data))
    return {"source": "db", **data}


@app.put("/cache-aside/products/{pid}")
async def cache_aside_update(pid: str, body: ProductIn):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE products SET name=$1, price_cents=$2 WHERE id=$3",
            body.name,
            body.price_cents,
            pid,
        )
    await safe_cache_delete(f"ca:product:{pid}")
    return {"ok": True, "pattern": "cache-aside", "action": "invalidated"}


# ---------------------------------------------------------------------------
# 2. Read-through
# ---------------------------------------------------------------------------
async def _load_product(pid: str) -> Optional[dict]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, price_cents FROM products WHERE id=$1", pid
        )
    return dict(row) if row else None


@app.get("/read-through/products/{pid}")
async def read_through_get(pid: str):
    rt = ReadThrough(cache, _load_product, ttl=TTL, prefix="rt:product:")
    result = await rt.get(pid)
    if result is None:
        raise HTTPException(404, "not found")

    key = f"rt:product:{pid}"
    cached = await safe_cache_get(key)
    source = "cache" if cached else "db"
    return {"source": source, **result}


# ---------------------------------------------------------------------------
# 3. Write-through
# ---------------------------------------------------------------------------
@app.get("/write-through/products/{pid}")
async def write_through_get(pid: str):
    key = f"wt:product:{pid}"
    cached = await safe_cache_get(key)
    if cached:
        return {"source": "cache", **json.loads(cached)}

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, price_cents FROM products WHERE id=$1", pid
        )
    if not row:
        raise HTTPException(404, "not found")
    data = dict(row)
    await safe_cache_set(key, json.dumps(data))
    return {"source": "db", **data}


@app.put("/write-through/products/{pid}")
async def write_through_update(pid: str, body: ProductIn):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE products SET name=$1, price_cents=$2 WHERE id=$3",
            body.name,
            body.price_cents,
            pid,
        )
        row = await conn.fetchrow(
            "SELECT id, name, price_cents FROM products WHERE id=$1", pid
        )
    await safe_cache_set(f"wt:product:{pid}", json.dumps(dict(row)))
    return {"ok": True, "pattern": "write-through", "action": "set"}


# ---------------------------------------------------------------------------
# 4. Write-around
# ---------------------------------------------------------------------------
@app.post("/write-around/events")
async def write_around_create(body: EventIn):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO events (id, type, payload) VALUES ($1, $2, $3)",
            body.id,
            body.type,
            json.dumps(body.payload),
        )
    return {"ok": True, "pattern": "write-around", "action": "db-only"}


@app.get("/write-around/events/{eid}")
async def write_around_get(eid: str):
    key = f"wa:event:{eid}"
    cached = await safe_cache_get(key)
    if cached:
        return {"source": "cache", **json.loads(cached)}

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, type, payload FROM events WHERE id=$1", eid)
    if not row:
        raise HTTPException(404, "not found")
    data = {"id": row["id"], "type": row["type"], "payload": json.loads(row["payload"])}
    await safe_cache_set(key, json.dumps(data))
    return {"source": "db", **data}


# ---------------------------------------------------------------------------
# 5. Write-back (write-behind)
# ---------------------------------------------------------------------------
@app.put("/write-back/metrics/{mid}")
async def write_back_write(mid: str, body: MetricIn):
    mapping = {"value": str(body.value), "tags": json.dumps(body.tags)}
    try:
        await cache.hset(f"metric:{mid}", mapping=mapping)
        await cache.sadd("metric:dirty", mid)
    except Exception:
        raise HTTPException(503, "cache unavailable")
    return {"ok": True, "pattern": "write-back", "action": "cached-for-flush"}


@app.get("/write-back/metrics/{mid}")
async def write_back_get(mid: str):
    try:
        data = await cache.hgetall(f"metric:{mid}")
        if data:
            payload = {
                (k if isinstance(k, str) else k.decode()): (
                    v if isinstance(v, str) else v.decode()
                )
                for k, v in data.items()
            }
            return {"source": "cache", "id": mid, **payload}
    except Exception:
        pass

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, payload FROM metrics WHERE id=$1", mid)
    if not row:
        raise HTTPException(404, "not found")
    return {"source": "db", "id": row["id"], "payload": json.loads(row["payload"])}


@app.get("/write-back/flush-status")
async def write_back_flush_status():
    try:
        dirty_count = await cache.scard("metric:dirty")
    except Exception:
        dirty_count = -1
    async with pool.acquire() as conn:
        db_count = await conn.fetchval("SELECT count(*) FROM metrics")
    return {"dirty_keys": dirty_count, "persisted_rows": db_count}


# ---------------------------------------------------------------------------
# 6. Refresh-ahead
# ---------------------------------------------------------------------------
@app.get("/refresh-ahead/products/{pid}")
async def refresh_ahead_get(pid: str):
    key = f"ra:product:{pid}"
    try:
        await cache.zadd("product:hot", {pid: time.time()})
    except Exception:
        pass

    cached = await safe_cache_get(key)
    if cached:
        return {"source": "cache", **json.loads(cached)}

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, price_cents FROM products WHERE id=$1", pid
        )
    if not row:
        raise HTTPException(404, "not found")
    data = dict(row)
    await safe_cache_set(key, json.dumps(data))
    return {"source": "db", **data}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/cache-keys")
async def cache_keys():
    """Debug endpoint: list all cache keys."""
    try:
        keys = []
        async for key in cache.scan_iter("*"):
            k = key if isinstance(key, str) else key.decode()
            keys.append(k)
        return {"keys": sorted(keys)}
    except Exception:
        return {"keys": [], "error": "cache unavailable"}
