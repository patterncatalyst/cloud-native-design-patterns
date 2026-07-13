# Example 16 — WebSockets (Python)

WebSocket scale-out with Redis pub/sub backplane — two server pods sharing state for cross-pod message delivery.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: websockets, redis[hiredis] (Redis pub/sub), OTel
- **Container base**: python:3.12-slim

## Run

```bash
podman compose up --build -d
```

Wait for healthy, then verify from the example root:

```bash
cd .. && bash verify.sh
```

## Project structure

| Path | Description |
|------|-------------|
| `ws-server/` | main.py — WebSocket endpoint with Redis backplane for cross-pod broadcast, sequence numbers for resume |

## Implementation notes

Two instances of ws-server run behind the compose network. Redis pub/sub channel used as backplane. Monotonic sequence numbers allow clients to resume after disconnect.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`REDIS_URL`

## Local development (without containers)

Requires pip install -r requirements.txt.

```bash
uvicorn main:app --reload --port 8080
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
