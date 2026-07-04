import asyncio
import json
import logging
import os

import httpx
import redis.asyncio as aioredis
from aiokafka import AIOKafkaProducer
from fastapi import FastAPI

app = FastAPI()
logger = logging.getLogger("decorator")
logging.basicConfig(level=logging.INFO)

LEGACY_URL = os.environ.get("LEGACY_URL", "http://legacy:8080")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379")
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "kafka:9094")
CACHE_TTL = 60

client = httpx.AsyncClient(timeout=5.0)
redis_client: aioredis.Redis | None = None
producer: AIOKafkaProducer | None = None
published_events: list[dict] = []


@app.on_event("startup")
async def startup():
    global redis_client, producer
    redis_client = aioredis.from_url(REDIS_URL)
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
    for attempt in range(30):
        try:
            await producer.start()
            logger.info("Kafka producer connected")
            break
        except Exception:
            logger.warning("Kafka not ready, retry %d/30", attempt + 1)
            await asyncio.sleep(2)
    else:
        logger.error("Failed to connect to Kafka after 30 attempts")


@app.on_event("shutdown")
async def shutdown():
    if producer:
        await producer.stop()
    if redis_client:
        await redis_client.close()


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    cache_key = f"order:{order_id}"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            logger.info("CACHE_HIT order_id=%s", order_id)
            return json.loads(cached)
    except Exception:
        pass

    r = await client.get(f"{LEGACY_URL}/orders/{order_id}")
    data = r.json()
    logger.info("CACHE_MISS order_id=%s", order_id)
    try:
        await redis_client.setex(cache_key, CACHE_TTL, json.dumps(data))
    except Exception:
        pass
    return data


@app.post("/orders", status_code=201)
async def create_order(body: dict):
    r = await client.post(f"{LEGACY_URL}/orders", json=body)
    data = r.json()

    event = {"event": "order.placed", "order_id": data.get("id"), **body}
    published_events.append(event)
    if producer:
        try:
            await producer.send_and_wait("order.placed", json.dumps(event).encode())
            logger.info("EVENT order.placed → Kafka order_id=%s", data.get("id"))
        except Exception as e:
            logger.warning("Kafka publish failed: %s", e)
    return data


@app.get("/events")
async def list_events():
    return published_events


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
