---
title: "Protocols in Depth"
marker: "A"
label: "Appendix A"
order: 14
part: "Deep-dive appendices"
description: "The deep dive behind 'pick the protocol' — REST, gRPC, and GraphQL compared on three axes: the mental model each imposes, how each handles fetching and round trips, and what actually travels on the wire."
duration: 26 minutes
---

This is the deep dive behind the protocol choice in **Communications**. The same
`place_order` intent takes three shapes, and the way to choose between them is to
compare the three on three axes: the **mental model** each imposes, how each
handles **fetching and round trips**, and what actually **travels on the wire**.

## Three paradigms, three mental models

Start with the mental model, because it drives everything else:

- **REST is resource-oriented** — nouns and HTTP verbs; you transfer
  representations of state.
- **gRPC is procedure-oriented** — you call typed methods; it's behaviour, not
  state, and the `.proto` is the contract.
- **GraphQL is graph-oriented** — one typed schema the client traverses, picking
  exactly the fields it wants.

{% include excalidraw.html
   file="14-three-paradigms"
   alt="Three columns for the same place_order intent. REST as resources: nouns plus HTTP verbs, POST to orders, GET an order by id, state transfer, server defines payload — resource-oriented. gRPC as procedures: typed method calls like Order.Place and Inventory.Reserve, behaviour not state, contract is the proto — RPC-oriented. GraphQL as a graph: one typed schema, the client picks fields and traverses relationships, contract is the SDL — query-oriented."
   caption="Figure A.1 — One intent, three mental models: resources, procedures, and a typed graph" %}

## The three axes, side by side

| Axis | REST | gRPC | GraphQL |
|---|---|---|---|
| **Mental model** | Resources: nouns + HTTP verbs, transfer state | Procedures: call typed methods, `.proto` is the contract | Typed graph: client traverses one schema, picks fields |
| **Fetching** | Several round trips, or a bespoke aggregate; fixed payloads over/under-fetch | One typed binary call | One tailored query; client names fields — no over/under-fetch |
| **Wire** | HTTP/1.1 or /2, JSON text, request/response, HTTP-cacheable, browser-native — *max reach* | HTTP/2 only, protobuf binary, uni- and bidirectional streaming, no HTTP cache, needs grpc-web in a browser | HTTP POST to one URL, JSON, request/response + subscriptions, caching is app-level |

The fetching axis is the one clients *feel*. With REST you often need several round
trips — order, then its items, then stock, then shipping — or you build a bespoke
aggregate endpoint and still get a fixed shape that over- or under-fetches. GraphQL
collapses that into one query whose fields the client chooses; gRPC is a single
typed binary call.

{% include excalidraw.html
   file="14-protocol-roundtrips"
   alt="REST requires the client to make several round trips to order, items, and stock or shipping, with fixed payloads; GraphQL collapses the same data need into a single query to the gateway where the client names the fields"
   caption="Figure A.2 — Many REST round trips versus one client-shaped GraphQL query" %}

The third axis is what literally travels between processes, and it is the one that
decides reach and caching. REST rides ordinary HTTP, so browsers and shared caches
handle it for free; gRPC trades that reach for HTTP/2 streaming and a compact binary
encoding; GraphQL keeps HTTP reach but moves caching up into the application.

{% include excalidraw.html
   file="14-the-wire"
   alt="Three columns comparing what travels on the wire. REST: transport HTTP/1.1 or 2, JSON text encoding, request and response interaction, cacheable via HTTP, browser-native reach. gRPC: HTTP/2 only, protobuf binary, unidirectional and bidirectional streaming, no HTTP caching, needs grpc-web in a browser. GraphQL: HTTP POST to one URL, JSON text, request and response plus subscriptions, app-level caching, browser-native reach."
   caption="Figure A.3 — What travels on the wire, per protocol: transport, encoding, streaming, caching, and reach" %}

## How an RPC travels: stub to stub

REST and GraphQL are things you can hand-write with a terminal and `curl`; gRPC is
not, and that is the point. The `.proto` contract is compiled into a **client stub**
and a **server skeleton**, and your code only ever calls a typed method. Everything
between the two stubs — serialising the request to protobuf bytes, framing them onto
an HTTP/2 stream, and reversing all of that on the far side — is generated.

{% include excalidraw.html
   file="14-rpc-stub-to-stub"
   alt="A client process and a server process. In the client, application code calls inventory.ReserveStock(req); a generated client stub marshals the request to protobuf. An amber arrow labelled HTTP/2 frame, protobuf crosses to the server, where a generated server skeleton unmarshals the bytes back into a request and invokes the handler reserve(sku, qty). A dashed return arrow carries the ReserveReply protobuf bytes back. One typed contract generates both stubs."
   caption="Figure A.4 — How an RPC travels: a typed call in, protobuf on the wire, a typed call out" %}

From the caller's side it is a single typed method — no URL, no JSON, no status-code
mapping. This stub call is the same `ReserveStock` invocation in all six stacks;
each language gets a generated client from the one `.proto`.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// grpc-spring-boot-starter injects a generated blocking stub
@GrpcClient("inventory")
private InventoryGrpc.InventoryBlockingStub inventory;

int reserve(String sku, int qty) {
  ReserveReply reply = inventory.reserveStock(          // one typed, blocking call
      ReserveRequest.newBuilder().setSku(sku).setQuantity(qty).build());
  return reply.getRemaining();                          // generated getter
}
```

```java
@GrpcClient("inventory")                                // Quarkus gRPC client
Inventory inventory;                                    // generated interface

int reserve(String sku, int qty) {
  return inventory.reserveStock(                        // returns Uni<ReserveReply>
      ReserveRequest.newBuilder().setSku(sku).setQuantity(qty).build())
    .map(ReserveReply::getRemaining)
    .await().indefinitely();                            // block at the edge
}
```

```csharp
// Grpc.Net.Client — one channel, a generated typed client
var client = new Inventory.InventoryClient(channel);

async Task<int> Reserve(string sku, int qty)
{
    var reply = await client.ReserveStockAsync(         // one typed async call
        new ReserveRequest { Sku = sku, Quantity = qty });
    return reply.Remaining;
}
```

```python
# generated stub from protoc / buf
stub = inventory_pb2_grpc.InventoryStub(channel)

def reserve(sku: str, qty: int) -> int:
    reply = stub.ReserveStock(                          # one typed call
        inventory_pb2.ReserveRequest(sku=sku, quantity=qty))
    return reply.remaining
```

```cpp
// grpc++ sync API — generated typed stub
auto stub = Inventory::NewStub(channel);

int reserve(const std::string& sku, int qty) {
  ReserveRequest req; req.set_sku(sku); req.set_quantity(qty);
  ReserveReply reply; grpc::ClientContext ctx;
  grpc::Status st = stub->ReserveStock(&ctx, req, &reply);   // one typed call
  return st.ok() ? reply.remaining() : -1;
}
```

```go
// generated typed client over a shared connection
func reserve(ctx context.Context, client pb.InventoryClient,
	sku string, qty int32) (int32, error) {
	reply, err := client.ReserveStock(ctx,              // one typed call
		&pb.ReserveRequest{Sku: sku, Quantity: qty})    // generated typed stub
	if err != nil {
		return 0, err
	}
	return reply.GetRemaining(), nil
}
```

## Streaming and bidirectional communication

That single typed call is *unary* — one request, one response. gRPC's real
distinction from request/response REST is that the same `.proto` can declare three
more shapes, just by marking a side `stream`:

- **Server-streaming** — one request, a stream of responses. Live order feeds,
  progress updates, tailing a changelog.
- **Client-streaming** — a stream of requests, one response. Bulk ingest, file
  upload, telemetry batches folded into a single ack.
- **Bidirectional** — both sides stream independently over one connection. Chat,
  collaborative editing, long-lived sync.

{% include excalidraw.html
   file="14-streaming-modes"
   alt="Four panels comparing RPC modes between a client and a server. Unary: one request, one response. Server-streaming: one request, then N responses (amber). Client-streaming: N requests (amber), then one response. Bidirectional: both directions stream N to N over one connection (amber, double-headed)."
   caption="Figure A.5 — The four RPC modes: unary, server-streaming, client-streaming, and bidirectional" %}

The impact is architectural, not cosmetic. A stream is one long-lived HTTP/2 stream,
so ordering is preserved and there is no per-message connection cost — but the
connection is now stateful and pinned to one server instance, which the load
balancer must respect (the WebSockets appendix makes the same point). Backpressure
matters: a slow consumer must be allowed to slow the producer rather than buffer
without bound. Here is the server side of a server-streaming RPC in each stack —
note how every one expresses "push many, then finish."

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
@GrpcService                                    // server-streaming RPC
public class OrderEvents extends OrderEventsGrpc.OrderEventsImplBase {
  @Override
  public void streamOrderEvents(StreamRequest req,
                                StreamObserver<OrderEvent> obs) {
    for (Event e : events.since(req.getCursor()))
      obs.onNext(OrderEvent.newBuilder()        // push each event
          .setId(e.id()).setType(e.type()).build());
    obs.onCompleted();                          // close the stream
  }
}
```

```java
@GrpcService                                    // Quarkus gRPC — a reactive stream
public class OrderEvents implements OrderEventsService {
  @Override
  public Multi<OrderEvent> streamOrderEvents(StreamRequest req) {
    return Multi.createFrom().iterable(events.since(req.getCursor()))
      .map(e -> OrderEvent.newBuilder()         // one item per event
          .setId(e.id()).setType(e.type()).build());
  }
}
```

```csharp
public override async Task StreamOrderEvents(
    StreamRequest req, IServerStreamWriter<OrderEvent> stream,
    ServerCallContext ctx)
{
    foreach (var e in _events.Since(req.Cursor))
        await stream.WriteAsync(new OrderEvent {    // push each event
            Id = e.Id, Type = e.Type });
}
```

```python
class OrderEventsServicer(order_pb2_grpc.OrderEventsServicer):
    def StreamOrderEvents(self, request, context):
        for e in events.since(request.cursor):
            yield order_pb2.OrderEvent(             # yield streams each event
                id=e.id, type=e.type)
```

```cpp
grpc::Status StreamOrderEvents(grpc::ServerContext* ctx,
                               const StreamRequest* req,
                               grpc::ServerWriter<OrderEvent>* writer) override {
  for (const auto& e : events_.since(req->cursor())) {
    OrderEvent ev; ev.set_id(e.id); ev.set_type(e.type);
    writer->Write(ev);                          // push each event down the stream
  }
  return grpc::Status::OK;
}
```

```go
func (s *orderEventsServer) StreamOrderEvents(
	req *pb.StreamRequest, stream pb.OrderEvents_StreamOrderEventsServer) error {
	for _, e := range s.events.Since(req.GetCursor()) {
		if err := stream.Send(&pb.OrderEvent{Id: e.ID, Type: e.Type}); err != nil {
			return err                          // client gone — stop streaming
		}
	}
	return nil
}
```

## Why gRPC is fast

When the choosing guidance says "internal, low latency, high call volume → gRPC,"
this is why. None of these levers is exotic; together they make a typed binary call
markedly cheaper than JSON over HTTP/1.1.

| Lever | What it is | Why it beats JSON over HTTP/1.1 |
|---|---|---|
| **HTTP/2 multiplexing** | many calls share one connection | no connection-per-call and no app-layer head-of-line blocking |
| **Binary protobuf** | compact tag-number encoding, no field names on the wire | smaller payloads, far cheaper to parse than JSON text |
| **HPACK header compression** | repeated headers sent once, then referenced | per-call header overhead collapses |
| **Persistent channels** | one long-lived (TLS) connection, reused | no per-call handshake cost |
| **Generated stubs** | (de)serialisation is compiled, not reflective | less CPU per call than runtime JSON mapping |

Two honest caveats. The win is largest exactly where you'd expect it — chatty,
internal, east-west paths — and shrinks for occasional, large-payload calls where
the body dominates. And none of it reaches a browser directly: a browser needs
`grpc-web` and a proxy, which is why the public edge usually stays REST or GraphQL.

## Choosing between them in practice

Said plainly:

- **Public, partner-facing, browser or third-party clients, caching matters →
  REST.**
- **Internal service-to-service, low latency, high call volume, streaming → gRPC.**
- **Aggregating many back-ends for varied clients that each want different fields →
  GraphQL at the gateway.**
- **A fact that many consumers react to → don't make it a call at all; emit an
  event.**

The closing point ties back to the whole book: forcing one protocol everywhere —
"we're a gRPC shop," "everything is GraphQL" — is *itself* an anti-pattern. Each
protocol earns its place on a specific axis; a healthy system uses all of them
where they fit.

## Common mistakes with each

Drawn from real review comments:

- **REST** — verbs in URLs (`/createOrder`), returning `200` with an error body,
  offset pagination that breaks under concurrent writes, and throwing away free
  HTTP caching.
- **gRPC** — calling it straight from a browser without grpc-web, or treating it as
  "REST with protobuf" and never touching its streaming superpower.
- **GraphQL** — the N+1 resolver explosion (fix with DataLoader batching, as in
  **Composition**), no query depth or complexity limits, and using it for simple
  single-resource fetches where REST would be plainer.

The throughline: each protocol is a tool with a shape. Match the shape to the
interaction, and most of these mistakes never arise.

---
*Verification status: the gRPC stub call and server-streaming handler are shown in
all six languages and mirror the patterns compiled and run in the Communications
chapter; the comparison axes, streaming modes, and performance levers are conceptual.
The protocol choices this appendix argues are exercised in Communications and
Composition.*
