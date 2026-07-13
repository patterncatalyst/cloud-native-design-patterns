# Example 16 — WebSockets (Spring Boot)

WebSocket scale-out with Redis pub/sub backplane — two server pods sharing state for cross-pod message delivery.

## Framework & libraries

- **Framework**: Spring Boot (Web, WebSocket, Data Redis)
- **Libraries**: spring-boot-starter-websocket, spring-boot-starter-data-redis, OTel
- **Container base**: eclipse-temurin:21-jre

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
| `ws-server/` | WsHandler.java — WebSocket handler; RedisBackplane.java — pub/sub bridge; ClientRegistry.java — connection tracking |

## Implementation notes

Most decomposed implementation: 8 source files. `WebSocketConfig` registers the handler; `RedisBackplane` subscribes to a Redis channel and broadcasts to local connections.

## Environment variables

Key variables (set by compose.yaml, override for local dev):

`spring.data.redis.host`

## Local development (without containers)

Requires JDK 21+, Maven (wrapper included).

```bash
./mvnw spring-boot:run
```

Requires a running Postgres (and Kafka/Redis if the example uses them) —
see the compose.yaml `depends_on` for which infrastructure services are needed.

## Tear down

```bash
podman compose down -v
```
