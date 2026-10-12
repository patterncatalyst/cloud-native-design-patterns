import asyncio
import json
import logging
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import Field
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ws-server")


class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379"
    otel_endpoint: str = Field("http://lgtm:4318", validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    pod_name: str = Field(default_factory=lambda: f"ws-pod-{uuid.uuid4().hex[:6]}")


settings = Settings()

resource = Resource.create({"service.name": "ws-server", "pod.name": settings.pod_name})
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{settings.otel_endpoint}/v1/traces")))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("ws-server")

CHANNEL = "ws:broadcast"
clients: dict[str, WebSocket] = {}
seq_counters: dict[str, int] = defaultdict(int)
message_buffers: dict[str, list] = defaultdict(list)
BUFFER_SIZE = 100

redis_pool = None
pubsub_task = None


async def backplane_listener():
    sub = redis_pool.pubsub()
    await sub.subscribe(CHANNEL)
    async for msg in sub.listen():
        if msg["type"] != "message":
            continue
        payload = json.loads(msg["data"])
        target = payload.get("target")
        sender_pod = payload.get("pod")
        if sender_pod == settings.pod_name:
            continue
        if target and target in clients:
            ws = clients[target]
            seq_counters[target] += 1
            seq = seq_counters[target]
            frame = {"seq": seq, "data": payload["data"]}
            message_buffers[target].append(frame)
            if len(message_buffers[target]) > BUFFER_SIZE:
                message_buffers[target] = message_buffers[target][-BUFFER_SIZE:]
            try:
                await ws.send_json(frame)
            except Exception:
                pass
        elif not target:
            for cid, ws in list(clients.items()):
                seq_counters[cid] += 1
                seq = seq_counters[cid]
                frame = {"seq": seq, "data": payload["data"]}
                message_buffers[cid].append(frame)
                if len(message_buffers[cid]) > BUFFER_SIZE:
                    message_buffers[cid] = message_buffers[cid][-BUFFER_SIZE:]
                try:
                    await ws.send_json(frame)
                except Exception:
                    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_pool, pubsub_task
    redis_pool = redis.from_url(settings.redis_url)
    pubsub_task = asyncio.create_task(backplane_listener())
    log.info("ws-server started pod=%s", settings.pod_name)
    yield
    pubsub_task.cancel()
    await redis_pool.aclose()


app = FastAPI(title="WebSocket Server", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "pod": settings.pod_name}


@app.get("/info")
async def info():
    return {"pod": settings.pod_name, "clients": list(clients.keys())}


@app.post("/send")
async def send_via_backplane(target: str = None, message: str = "hello"):
    payload = {"pod": settings.pod_name, "target": target, "data": message}
    await redis_pool.publish(CHANNEL, json.dumps(payload))

    if target and target in clients:
        ws = clients[target]
        seq_counters[target] += 1
        seq = seq_counters[target]
        frame = {"seq": seq, "data": message}
        message_buffers[target].append(frame)
        if len(message_buffers[target]) > BUFFER_SIZE:
            message_buffers[target] = message_buffers[target][-BUFFER_SIZE:]
        await ws.send_json(frame)
    elif not target:
        for cid, ws in list(clients.items()):
            seq_counters[cid] += 1
            seq = seq_counters[cid]
            frame = {"seq": seq, "data": message}
            message_buffers[cid].append(frame)
            if len(message_buffers[cid]) > BUFFER_SIZE:
                message_buffers[cid] = message_buffers[cid][-BUFFER_SIZE:]
            try:
                await ws.send_json(frame)
            except Exception:
                pass

    return {"sent": True, "pod": settings.pod_name}


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    resume_seq = websocket.query_params.get("resume_seq")

    clients[client_id] = websocket
    log.info("client connected id=%s pod=%s", client_id, settings.pod_name)

    if resume_seq:
        resume_seq = int(resume_seq)
        missed = [m for m in message_buffers.get(client_id, []) if m["seq"] > resume_seq]
        for frame in missed:
            await websocket.send_json(frame)
        log.info("replayed %d missed messages for client=%s from seq=%d", len(missed), client_id, resume_seq)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data) if data.startswith("{") else {"type": "ping"}
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong", "pod": settings.pod_name})
    except WebSocketDisconnect:
        log.info("client disconnected id=%s pod=%s", client_id, settings.pod_name)
    finally:
        clients.pop(client_id, None)
