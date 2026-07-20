# Example 16: WebSockets (Quarkus)

Two-pod WebSocket service demonstrating cross-pod message delivery via Redis pub/sub backplane.

## Services

- **ws-pod-1** (port 8081) — WebSocket server instance 1
- **ws-pod-2** (port 8082) — WebSocket server instance 2

Both pods run identical code. Clients connect via WebSocket at `/ws/{clientId}`. Messages have sequence numbers for resume support.

## Stack

- **Quarkus 3.33.2 LTS** with `quarkus-websockets-next` (modern WebSocket API)
- **Redis** pub/sub backplane for cross-pod message delivery
- **LGTM** observability stack (Loki, Grafana, Tempo, Mimir)
- **OpenTelemetry** instrumentation with pod-level resource attributes

## Running

```bash
# Start stack
podman compose up -d

# Wait for health
podman compose ps

# Check health
curl http://localhost:8081/healthz
curl http://localhost:8082/healthz

# Run verification
../verify.sh
```

## What to observe

### Cross-pod message delivery

Connect a WebSocket client to pod-1:

```bash
websocat ws://localhost:8081/ws/client-A
```

Send a message from pod-2:

```bash
curl -X POST "http://localhost:8082/send?target=client-A&message=hello"
```

The message arrives at client-A on pod-1 via the Redis backplane.

### Broadcast

Connect clients to both pods:

```bash
websocat ws://localhost:8081/ws/client-A &
websocat ws://localhost:8082/ws/client-B &
```

Broadcast from either pod:

```bash
curl -X POST "http://localhost:8081/send?message=broadcast"
```

Both clients receive the message with monotonically increasing sequence numbers.

### Pod affinity

Send a ping from the WebSocket client:

```json
{"type": "ping"}
```

The pong response includes the pod name:

```json
{"type": "pong", "pod": "ws-pod-1"}
```

## Quarkus-specific features

### quarkus-websockets-next

This example uses `quarkus-websockets-next`, the modern Quarkus WebSocket API introduced in Quarkus 3.x. It replaces the legacy `quarkus-websockets` extension.

Key differences:
- CDI-based endpoint lifecycle (`@WebSocket`, `@OnOpen`, `@OnClose`, `@OnTextMessage`)
- Injected `WebSocketConnection` context
- Path parameters via `connection.pathParam()`
- Synchronous send via `sendTextAndAwait()`

### Redis pub/sub with Vert.x

The Redis backplane uses the Vert.x Redis client wrapped by `quarkus-redis-client`. A dedicated connection is created for subscription (required by Redis pub/sub semantics), while publish operations use the shared connection pool.

### Observability

Each pod exports telemetry to the LGTM stack with pod-level resource attributes. Distributed traces show cross-pod message flow through the Redis backplane.
