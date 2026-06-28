---
title: "WebSockets at Scale"
marker: "C"
label: "Appendix C"
order: 16
part: "Deep-dive appendices"
description: "The protocol we left out of the main interaction styles, because it behaves so differently on Kubernetes — why long-lived sockets fight stateless scaling, and the pub/sub backplane plus resume-don't-restart posture that fix it."
duration: 28 minutes
---

WebSockets were deliberately left out of the main interaction-styles discussion
because they behave so differently on Kubernetes. A WebSocket is long-lived,
stateful, and **pinned to a pod** — the opposite of the disposable, stateless
request the platform is built around.

## A WebSocket endpoint — and the problem hiding in it

Each of these is a perfectly ordinary WebSocket endpoint. Look at the connection
registry in every one: it's **per-pod, not shared.** That single fact is the entire
scaling problem.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
@Configuration                                  // spring-boot-starter-websocket
@EnableWebSocket
public class WsConfig implements WebSocketConfigurer {
    @Override public void registerWebSocketHandlers(WebSocketHandlerRegistry r) {
        r.addHandler(new OrderSocket(), "/ws/{userId}").setAllowedOriginPatterns("*");
    }
}

@Component
public class OrderSocket extends TextWebSocketHandler {
    // per-POD registry — NOT shared. This single fact is the scaling problem.
    private final Map<String, WebSocketSession> clients = new ConcurrentHashMap<>();

    @Override public void afterConnectionEstablished(WebSocketSession s) {
        clients.put(userId(s), s);              // this pod now owns this connection
    }
}
```

```java
@WebSocket(path = "/ws/{userId}")            // quarkus-websockets-next
public class OrderSocket {
    @Inject WebSocketConnection connection;   // this pod owns this connection
    @Inject OpenConnections connections;      // per-POD registry — NOT shared!

    @OnOpen
    public void onOpen(@PathParam String userId) {
        connection.userData().put(KEY_USER, userId);
    }

    @OnTextMessage                            // full-duplex, long-lived
    public String onMessage(String msg) { return handle(msg); }
}
```

```csharp
// SignalR ships in the box with ASP.NET Core. The Hub abstraction handles
// framing, heartbeats, and reconnect; a Redis backplane handles scale-out.
public class OrdersHub : Hub                  // one Hub per logical channel
{
    private readonly IOrderService _orders;
    public OrdersHub(IOrderService orders) => _orders = orders;

    public override async Task OnConnectedAsync()
    {
        var userId = Context.UserIdentifier!;          // server-side auth
        await Groups.AddToGroupAsync(Context.ConnectionId, userId);
        await base.OnConnectedAsync();
    }
    // builder.AddSignalR().AddStackExchangeRedis("redis:6379");  // the backplane
}
```

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()
clients: dict[str, WebSocket] = {}           # per-POD state — NOT shared!

@app.websocket("/ws/{user_id}")
async def ws(sock: WebSocket, user_id: str):
    await sock.accept()
    clients[user_id] = sock                   # this pod now owns this connection
    try:
        while True:
            msg = await sock.receive_json()   # full-duplex, long-lived
            await handle(user_id, msg)
    except WebSocketDisconnect:
        clients.pop(user_id, None)
```

```cpp
// Drogon WebSocket endpoint — per-pod state; the scaling problem starts here.
class OrderWs : public drogon::WebSocketController<OrderWs> {
 public:
  WS_PATH_LIST_BEGIN
    WS_PATH_ADD("/ws/{user_id}");
  WS_PATH_LIST_END
  void handleNewConnection(const HttpRequestPtr& req,
                           const WebSocketConnectionPtr& conn) override {
    std::lock_guard lk{mu_};
    clients_[req->getParameter("user_id")] = conn;  // THIS pod owns it — not shared!
  }
 private:
  std::mutex mu_;
  std::unordered_map<std::string, WebSocketConnectionPtr> clients_;
};
```

```go
// ws.go — coder/websocket; per-pod state, the scaling problem starts here
var clients sync.Map // map[string]*websocket.Conn — THIS pod's connections, not shared

func wsHandler(w http.ResponseWriter, r *http.Request) {
	userID := r.PathValue("user_id") // 1.22+ path wildcard
	c, err := websocket.Accept(w, r, nil)
	if err != nil {
		return
	}
	defer c.CloseNow()
	clients.Store(userID, c) // this pod now owns this connection
	defer clients.Delete(userID)

	for { // full-duplex, long-lived
		var msg Message
		if err := wsjson.Read(r.Context(), c, &msg); err != nil {
			return // disconnect
		}
		handle(r.Context(), userID, msg)
	}
}
```

## Why WebSockets fight Kubernetes scaling

Once a connection is established through the load balancer, it is pinned to one pod
for its whole lifetime. Two problems follow:

- **Scale-up** — the HPA or KEDA adds `ws-pod-3`, but it gets *zero* existing
  connections. New pods only receive *new* connections, so load stays lopsided and
  the new capacity barely helps the pods already saturated.
- **Scale-down** — killing a pod drops *every* connection it held at once. The
  clients must all reconnect simultaneously — a thundering herd you caused
  yourself.

And because the registry is per-pod, a message for user X is undeliverable from any
pod that doesn't happen to hold X's socket.

{% include excalidraw.html
   file="16-ws-scaling-problem"
   alt="Clients hold long-lived ws connections through a Service or load balancer that is sticky per connection. ws-pod-1 holds 120 connections and ws-pod-2 holds 118, but a newly added ws-pod-3 holds 0 — the scale-up problem, since a new pod gets no existing connections, only new ones. Killing a pod is the scale-down or rollout problem: it drops every connection it was holding at once."
   caption="Figure C.1 — A WebSocket pins to a pod, so scale-up leaves new pods idle and scale-down drops every connection at once" %}

## Scaling out: a pub/sub backplane

The fix keeps the part that's fine — each pod still owns only its own sockets — and
adds a shared **backplane** that every pod subscribes and publishes to: **Redis
pub/sub** for low latency, or a **Kafka topic** when you want durability and replay.
To send to user X, any pod publishes to the backplane; the pod that actually holds
X's socket is subscribed, receives it, and writes it down the wire. No pod needs to
know where any client lives.

{% include excalidraw.html
   file="16-ws-backplane"
   alt="Three WebSocket pods each own only their own sockets; all subscribe and publish to a shared Redis or Kafka backplane. A message for client X arrives at ws-pod-1, which publishes to the backplane; the backplane delivers it to ws-pod-2, which holds X's socket"
   caption="Figure C.2 — Externalised fan-out: the backplane routes each message to whichever pod holds the client" %}

For the payload itself, frame messages as **binary protobuf** rather than JSON
text: smaller and faster on a hot socket, and versioned by the same field-number
rules as gRPC (see **Appendix B**).

## Failure handling: resume, don't restart

The cloud-native posture is to treat every connection as disposable and design for
its loss:

- **Heartbeats** (ping/pong) detect a dead link in seconds — raw TCP can hang for
  minutes before noticing.
- On a drop, the client **reconnects with exponential backoff plus jitter**, so a
  mass disconnect doesn't become a synchronised reconnect storm.
- The client **resumes from the last acknowledged sequence number** — a monotonic
  per-connection counter — so the server replays only what was missed instead of
  restarting the stream. Resume, don't restart.

{% include excalidraw.html
   file="16-ws-resume"
   alt="A sequence between a client and a ws-pod. A ping/pong heartbeat detects a dead link; the connection is lost; the client reconnects with backoff and jitter; it resumes by sending its last acknowledged sequence number (1042); the pod replays only the missed events (1043 to 1050), which are idempotent; the stream is live again, at-least-once and deduplicated by sequence."
   caption="Figure C.3 — Resume, don't restart: detect the drop, reconnect with backoff, and replay only what was missed from the last acked sequence" %}

## Binary framing with protobuf over WebSockets

The backplane section said to frame messages as binary protobuf; here is what that
means on the wire. Every message is one versioned **Envelope** — a thin protobuf
wrapper carrying a `version`, the per-connection `seq` that resume already relies on,
a `type` discriminator, and the actual event as nested `payload` bytes. It is sent
as a WebSocket *binary* frame, not a text frame.

```proto
// envelope.proto — one versioned wrapper for every WebSocket message
message Envelope {
  uint32 version = 1;   // bump for an incompatible payload change
  uint64 seq     = 2;   // per-connection monotonic counter — drives resume
  string type    = 3;   // payload discriminator, e.g. "OrderPlaced"
  bytes  payload = 4;   // a nested protobuf message, already serialised
}
```

{% include excalidraw.html
   file="16-ws-protobuf-envelope"
   alt="A producer encodes to bytes; the bytes travel inside a WebSocket binary frame (opcode 0x2) made of four fields — version (uint32 = 2), seq (uint64 = 1043), type (the string OrderPlaced), and payload (protobuf bytes, highlighted); a consumer decodes and dispatches. The envelope is versioned by field number like gRPC: add fields, never renumber."
   caption="Figure C.4 — A versioned protobuf Envelope carried in one binary WebSocket frame" %}

The wins are the same three gRPC gets from protobuf: the frame is **smaller** (no
field names on the wire), **cheaper to parse** than re-parsing JSON on every hot
message, and **versioned by field number** — add a field, never renumber, exactly as
in **Appendix B**. Encoding and sending the envelope looks like this in each stack;
the receive side is the mirror image — read the binary frame, parse the `Envelope`,
and dispatch on `type`.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// BinaryWebSocketHandler — protobuf frames, not text
public class OrderSocket extends BinaryWebSocketHandler {
  void push(WebSocketSession s, long seq, OrderPlaced event) throws IOException {
    Envelope env = Envelope.newBuilder()
        .setVersion(2).setSeq(seq).setType("OrderPlaced")
        .setPayload(event.toByteString())             // nested protobuf
        .build();
    s.sendMessage(new BinaryMessage(env.toByteArray()));   // one binary frame
  }
}
```

```java
@WebSocket(path = "/ws/{userId}")                     // quarkus-websockets-next
public class OrderSocket {
  @Inject WebSocketConnection connection;
  void push(long seq, OrderPlaced event) {
    Envelope env = Envelope.newBuilder()
        .setVersion(2).setSeq(seq).setType("OrderPlaced")
        .setPayload(event.toByteString()).build();
    connection.sendBinaryAndAwait(Buffer.buffer(env.toByteArray()));
  }
}
```

```csharp
// raw System.Net.WebSockets — a protobuf binary frame, not SignalR text
async Task Push(WebSocket socket, ulong seq, OrderPlaced ev)
{
    var env = new Envelope {
        Version = 2, Seq = seq, Type = "OrderPlaced",
        Payload = ev.ToByteString() };                // nested protobuf
    await socket.SendAsync(env.ToByteArray(),
        WebSocketMessageType.Binary, endOfMessage: true, ct);
}
```

```python
async def push(sock: WebSocket, seq: int, event: OrderPlaced):
    env = Envelope(
        version=2, seq=seq, type="OrderPlaced",
        payload=event.SerializeToString())            # nested protobuf
    await sock.send_bytes(env.SerializeToString())     # one binary frame
```

```cpp
// Drogon — send a protobuf Envelope as a binary frame
void push(const WebSocketConnectionPtr& conn, uint64_t seq,
          const OrderPlaced& event) {
  Envelope env;
  env.set_version(2); env.set_seq(seq); env.set_type("OrderPlaced");
  env.set_payload(event.SerializeAsString());         // nested protobuf
  conn->send(env.SerializeAsString(),
             WebSocketMessageType::Binary);            // one binary frame
}
```

```go
// coder/websocket — write a protobuf Envelope as a binary frame
func push(ctx context.Context, c *websocket.Conn, seq uint64, ev *pb.OrderPlaced) error {
	payload, _ := proto.Marshal(ev)                   // nested protobuf
	out, _ := proto.Marshal(&pb.Envelope{
		Version: 2, Seq: seq, Type: "OrderPlaced", Payload: payload})
	return c.Write(ctx, websocket.MessageBinary, out) // one binary frame
}
```

## Failover without interruption

Resume is the client-side mechanic; **failover** is what it buys you when a whole pod
goes away — a rollout, a scale-down, or a crash. The socket drops, the client
reconnects through the Service, and the load balancer lands it on *some other* pod —
never the dead one. That only works because the backplane already decoupled delivery
from placement: any pod can serve any client, so the new pod is as good as the old
one. The client then resumes from its last acked `seq`, and the new pod replays only
the missed range. The user sees a brief reconnect, not a lost stream.

{% include excalidraw.html
   file="16-ws-failover"
   alt="A client that resumes at seq 1043 reconnects with backoff through the LB or Service. The dashed path to ws-pod-2, now terminated, is marked gone; the client lands instead on ws-pod-5, which holds the new socket. ws-pod-5 subscribes to the Redis or Kafka backplane and replays events with seq greater than 1042. The takeaway: backplane plus per-connection seq means a pod dies and the client loses nothing."
   caption="Figure C.5 — Failover without interruption: reconnect lands on a live pod, which replays the gap from the backplane" %}

The one requirement is that the missed range be *reconstructable* from somewhere the
new pod can reach. A Kafka backplane with retention gives this for free — the new pod
seeks to `seq + 1` and replays. With Redis pub/sub, which has no history, pair it with
a short server-side ring buffer (or a Redis stream) keyed by sequence so the gap can
be re-sent. Either way the contract is at-least-once, deduplicated by `seq`.

## Performance

A WebSocket's entire value is amortising one handshake across thousands of messages,
so performance work is mostly about keeping the *per-message* cost low and the
*per-connection* memory bounded.

| Lever | Why it matters |
|---|---|
| **Binary protobuf frames** | fewer bytes and a cheaper parse than JSON text on every hot message |
| **One upgrade, then raw frames** | no per-message HTTP request/response or header overhead — the handshake is paid once |
| **Bounded send buffers (backpressure)** | a slow consumer slows the producer instead of growing memory without limit; drop or disconnect rather than OOM |
| **Coalesce small messages** | batch a burst into one frame to cut syscalls and framing overhead |
| **Tuned heartbeats** | ping often enough to detect a dead link in seconds, rarely enough not to wake every idle connection constantly |
| **Per-pod connection caps** | memory-per-connection × cap sizes the pod; scale and trigger on connection count, not CPU |

The throughline with the rest of this appendix: most of these are the same levers
that make the system *scale* — bounded buffers and connection caps are what let the
HPA reason about a pod, and binary framing is what keeps the backplane cheap.

## A cloud-native WebSocket checklist

- **Externalise fan-out** to a backplane (Redis or Kafka); never assume one pod
  holds the client.
- **Scale and trigger on connection count and memory, not CPU**, and set realistic
  per-pod connection caps.
- **Drain gracefully on shutdown**: stop accepting new connections, signal clients
  to reconnect, and give them time to land on another pod before the pod exits
  (which is exactly the graceful-shutdown discipline of **Appendix H**).
- **Frame binary and versioned**: protobuf `Envelope`s (version + seq + type +
  payload), not JSON text — and bound each connection's send buffer so a slow
  client applies backpressure instead of exhausting the pod.

### Cross-check it yourself

Make the backplane earn its place. Connect a client to `ws-pod-1`, then send it a
message *from* `ws-pod-2`: with the backplane wired up it arrives; rip the backplane
out and it vanishes, because no other pod can reach that socket. Then scale the
Deployment down by one and confirm the dropped clients reconnect with backoff and
resume from their last sequence rather than losing the stream.

---
*Verification status: unverified — endpoints transcribed and normalised from the
source decks, not yet run with a live backplane. The `examples/16-websockets/`
runner moves it to verified.*
