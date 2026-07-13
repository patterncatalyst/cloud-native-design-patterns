# Example 24 — Monolith to Microservices (Python)

Strangler fig pattern — router proxies to the monolith, decorator intercepts and enriches, new services peel off incrementally.

## Framework & libraries

- **Framework**: FastAPI + Uvicorn
- **Libraries**: aiokafka (Kafka), redis, httpx (HTTP proxy)
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
| `router-service/` | main.py — reverse proxy routing to monolith or new services based on path rules |
| `decorator-service/` | main.py — intercepts responses, enriches with cached data from Redis, publishes events to Kafka |
| `stub-service/` | main.py — placeholder for a peeled-off microservice |

## Implementation notes

Router is the strangler fig entry point — it starts routing 100% to the monolith and incrementally shifts paths to new services. Decorator sits between router and monolith.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`KAFKA_BOOTSTRAP, REDIS_URL, MONOLITH_URL`

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
