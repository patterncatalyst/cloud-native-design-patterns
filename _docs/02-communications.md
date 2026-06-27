---
title: "Communications"
order: 2
part: "Foundations & the system"
description: "Four interaction styles and four defaults — REST at the edge, gRPC for internal calls, GraphQL for composed reads, async events for facts — and pushing resilience onto the mesh instead of into your code."
duration: 20 minutes
---

A service talks to the world and to its peers, and the mistake is using one wire
for everything. There are four interaction styles, and each has a default that
fits it. Real systems use all four; the skill is matching each call to the right
one.

- **REST** for the public, edge surface — reach and caching matter most.
- **gRPC** for internal service-to-service calls — latency and streaming matter.
- **GraphQL** for client-driven reads that compose many sources in one round trip.
- **Async events** for decoupled facts that fan out to whoever cares.

{% include excalidraw.html
   file="02-pick-protocol"
   alt="Four columns of interaction styles, each tagged sync or async: REST/HTTP (public and edge surface, wide reach, cacheable, resource-shaped, FastAPI) — sync; gRPC (internal service-to-service, low latency, streaming, schema-first proto) — sync; GraphQL (client-driven reads, compose many sources, one round-trip, Strawberry/Graphene) — sync; and Async/events (fire-and-forget facts, decoupled in time, fan-out to many, Kafka/Pulsar) — async."
   caption="Figure 2.1 — Four interaction styles, four defaults — three synchronous, one asynchronous" %}

Read it by the sync/async tags along the bottom: REST, gRPC, and GraphQL are all
request/response — the caller waits — while events are fire-and-forget. Three of the
four couple the caller to the callee's availability for the duration of the call; only
the fourth breaks that coupling. Choosing a style is therefore choosing how much
availability you are willing to inherit — the thread the rest of the chapter pulls on.
REST wins where reach and caching matter; gRPC where an internal hop must be fast and
strongly typed; GraphQL where one client read would otherwise be a handful of round
trips; and events wherever immediacy is not strictly required.

## REST at the edge

This is the public surface — in our system, `order-service`. Four things teams
routinely get wrong, and the code gets right: resource-shaped URLs (nouns, not
verbs), request and response contracts validated before bad input reaches your
logic, correct status codes (**201** on create, not 200), and **cursor**
pagination rather than offset (offset breaks under concurrent writes and slows
down at depth).

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
@RestController
@RequestMapping("/orders")
public class OrderController {                // Spring Web MVC
    private final OrderService orders;
    private final EventPublisher events;
    public OrderController(OrderService orders, EventPublisher events) {
        this.orders = orders; this.events = events;
    }

    record OrderIn(@NotBlank String sku, @Positive int quantity) {}  // validated

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)       // correct status, not 200
    public Order place(@Valid @RequestBody OrderIn body) {
        Order o = orders.create(body);
        events.publish("order.placed", o);    // emit the fact (made safe in ch. 04)
        return o;
    }

    @GetMapping                                // cursor pagination, not offset
    public Page<Order> list(@RequestParam(required = false) String after,
                            @RequestParam(defaultValue = "50") int limit) {
        return orders.page(after, limit);
    }
}
```

```java
@Path("/orders")
@Produces(MediaType.APPLICATION_JSON)
public class OrderResource {                  // Quarkus REST

    record OrderIn(@NotBlank String sku, @Positive int quantity) {}  // validated

    @POST
    @Transactional
    public RestResponse<Order> place(@Valid OrderIn body) {
        Order o = orders.create(body);
        events.publish("order.placed", o);    // emit the fact (made safe in ch. 04)
        return RestResponse.status(Response.Status.CREATED, o);   // 201, not 200
    }

    @GET                                       // cursor pagination, not offset
    public Page<Order> list(@RestQuery String after,
                            @RestQuery @DefaultValue("50") int limit) {
        return orders.page(after, limit);
    }
}
```

```csharp
// Program.cs — minimal API style; FluentValidation for input contracts
var orders = app.MapGroup("/orders").WithOpenApi();

public record OrderIn(                             // immutable, validated
    [Required, StringLength(64)] string Sku,
    [Range(1, 1_000)]            int    Quantity);

orders.MapPost("/", async (
        [FromBody] OrderIn body,
        IValidator<OrderIn> validator,            // FluentValidation
        IOrderService svc,
        IEventPublisher events) =>
{
    var result = await validator.ValidateAsync(body);
    if (!result.IsValid) return Results.ValidationProblem(result.ToDictionary());

    var order = await svc.CreateAsync(body);
    await events.PublishAsync("order.placed", order);   // emit (made safe in ch. 04)
    return Results.Created($"/orders/{order.Id}", order);   // 201, not 200
});

orders.MapGet("/", (string? after, int limit, IOrderService svc) =>
    svc.Page(after, limit));                       // cursor pagination, not offset
```

```python
from fastapi import FastAPI, Query
from pydantic import BaseModel

class OrderIn(BaseModel):            # request contract, validated by Pydantic
    sku: str
    quantity: int

class Order(BaseModel):
    id: str; sku: str; quantity: int; status: str

@app.post("/orders", response_model=Order, status_code=201)   # 201, not 200
async def place_order(body: OrderIn) -> Order:
    order = await orders.create(body)
    await events.publish("order.placed", order)   # emit the fact (made safe in ch. 04)
    return order

@app.get("/orders")                  # cursor pagination, not offset
async def list_orders(after: str | None = Query(None), limit: int = 50):
    return await orders.page(after=after, limit=limit)
```

```cpp
// orders_controller.h — Drogon controller; the OpenAPI YAML is the contract
struct OrderIn { std::string sku; int quantity; };
struct Order   { std::string id, sku, status; int quantity; };

class Orders : public drogon::HttpController<Orders> {
 public:
  METHOD_LIST_BEGIN
    ADD_METHOD_TO(Orders::place, "/orders", Post);
    ADD_METHOD_TO(Orders::list,  "/orders?after={1}&limit={2}", Get);
  METHOD_LIST_END
};

// orders_controller.cc — body validated against the YAML, 201 on create
Task<> Orders::place(HttpRequestPtr req, auto cb) {
  auto in = co_await parse_validated<OrderIn>(req);    // throws → 400
  Order o = co_await orders.create(in);
  co_await events.publish("order.placed", o);          // emit (made safe in ch. 04)
  auto r  = HttpResponse::newHttpJsonResponse(to_json(o));
  r->setStatusCode(k201Created);                       // 201, not 200
  cb(r);
}
```

```go
// orders.go — net/http (Go 1.22+ ServeMux); validated input, 201 on create
type OrderIn struct {
	SKU      string `json:"sku"`
	Quantity int    `json:"quantity"`
}
type Order struct {
	ID       string `json:"id"`
	SKU      string `json:"sku"`
	Quantity int    `json:"quantity"`
	Status   string `json:"status"`
}

func (s *Server) place(w http.ResponseWriter, r *http.Request) {
	var in OrderIn // request contract, validated before logic
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil ||
		in.SKU == "" || in.Quantity < 1 {
		http.Error(w, "invalid order", http.StatusBadRequest)
		return
	}
	o, err := s.orders.Create(r.Context(), in)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	s.events.Publish(r.Context(), "order.placed", o) // emit (made safe in ch. 04)
	w.Header().Set("Location", "/orders/"+o.ID)
	writeJSON(w, http.StatusCreated, o) // 201, not 200
}

func (s *Server) list(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query() // cursor pagination, not offset
	page := s.orders.Page(r.Context(), q.Get("after"), atoiOr(q.Get("limit"), 50))
	writeJSON(w, http.StatusOK, page)
}

func (s *Server) routes() {
	s.mux.HandleFunc("POST /orders", s.place) // method-aware patterns (1.22+)
	s.mux.HandleFunc("GET /orders", s.list)
}
```

The `events.publish("order.placed", …)` line is shown simply here so the focus
stays on the edge concerns; **04 · Data** makes that emission transactionally safe
with the outbox. FastAPI, Spring, and the others also emit an OpenAPI document
for free, which becomes the registered contract.

## gRPC for internal calls

Between internal services — `order-service` calling `inventory` — reach for gRPC:
binary, multiplexed over HTTP/2, fast, and streaming-capable. The crucial point is
that the **`.proto` is the contract**, and it lives in the registry exactly like
OpenAPI. It is the same file for every language; each side generates typed stubs
from it, so nobody hand-writes JSON parsing.

```proto
// inventory.proto — the contract, registered in the API registry
syntax = "proto3";
service Inventory {
  rpc ReserveStock (ReserveRequest) returns (ReserveReply);
}
message ReserveRequest { string sku = 1; int32 quantity = 2; }
message ReserveReply   { bool reserved = 1; int32 remaining = 2; }
```

The field numbers (`= 1`, `= 2`) are the wire contract, not cosmetic — **Appendix B**
explains exactly why they can never be reused. Generate stubs with `protoc` or `buf`,
and both sides share types.

The server side is generated too: you implement the service interface the `.proto`
produces and fill in the one method, never touching the wire format itself.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
@GrpcService                                    // grpc-spring-boot-starter
public class InventoryService extends InventoryGrpc.InventoryImplBase {
  private final Stock stock;
  public InventoryService(Stock stock) { this.stock = stock; }

  @Override                                      // generated base method
  public void reserveStock(ReserveRequest req, StreamObserver<ReserveReply> obs) {
    int remaining = stock.reserve(req.getSku(), req.getQuantity());   // generated getters
    obs.onNext(ReserveReply.newBuilder()
        .setReserved(remaining >= 0)
        .setRemaining(Math.max(remaining, 0)).build());
    obs.onCompleted();
  }
}
```

```java
@GrpcService                                    // Quarkus gRPC
public class InventoryService implements Inventory {   // generated interface
  @Inject Stock stock;

  @Override @Blocking                            // run the blocking reserve on a worker
  public Uni<ReserveReply> reserveStock(ReserveRequest req) {
    int remaining = stock.reserve(req.getSku(), req.getQuantity());
    return Uni.createFrom().item(ReserveReply.newBuilder()
        .setReserved(remaining >= 0)
        .setRemaining(Math.max(remaining, 0)).build());
  }
}
```

```csharp
public class InventoryService : Inventory.InventoryBase   // generated base
{
    private readonly IStock _stock;
    public InventoryService(IStock stock) => _stock = stock;

    public override Task<ReserveReply> ReserveStock(
        ReserveRequest req, ServerCallContext ctx)
    {
        var remaining = _stock.Reserve(req.Sku, req.Quantity);
        return Task.FromResult(new ReserveReply {
            Reserved = remaining >= 0, Remaining = Math.Max(remaining, 0) });
    }
}
```

```python
# server.py — generated stubs from protoc / buf
class InventoryServicer(inventory_pb2_grpc.InventoryServicer):
    def ReserveStock(self, request, context):
        remaining = stock.reserve(request.sku, request.quantity)
        return inventory_pb2.ReserveReply(
            reserved=remaining >= 0, remaining=max(remaining, 0))
```

```cpp
// inventory_service.cc — grpc++ sync API; generated Inventory::Service base
class InventoryServiceImpl final : public Inventory::Service {
  grpc::Status ReserveStock(grpc::ServerContext* ctx,
                            const ReserveRequest* req,
                            ReserveReply* reply) override {
    int remaining = stock_.reserve(req->sku(), req->quantity());  // generated accessors
    reply->set_reserved(remaining >= 0);
    reply->set_remaining(std::max(remaining, 0));
    return grpc::Status::OK;
  }
  Stock stock_;
};
```

```go
// inventory_server.go — embed the generated UnimplementedInventoryServer base
type inventoryServer struct {
	pb.UnimplementedInventoryServer // forward-compatible
	stock *Stock
}

func (s *inventoryServer) ReserveStock(
	ctx context.Context, req *pb.ReserveRequest) (*pb.ReserveReply, error) {

	remaining := s.stock.Reserve(req.GetSku(), req.GetQuantity()) // generated getters
	return &pb.ReserveReply{
		Reserved:  remaining >= 0,
		Remaining: max(remaining, 0), // Go 1.21+ builtin
	}, nil
}
```

There is no socket code, no serialisation, no HTTP/2 framing — the generated base class
handles all of it. Your method receives a typed `ReserveRequest` and returns a typed
`ReserveReply`, and every language fills in the same one `ReserveStock` contract.

## Synchronous coupling vs. asynchronous facts

This is the central trade-off of the whole book in one picture. A synchronous
call couples caller to callee in *time* and *availability*: if `payment` is down,
the order request fails too, and availability multiplies downward across a chain.
Emitting `order.placed` as a fact lets the order succeed immediately; consumers
that were down catch up from the log later.

{% include excalidraw.html
   file="02-sync-vs-async"
   alt="Top row: order makes a synchronous call to payment and blocks on it, so if payment is down the order fails. Bottom row: order emits an order.placed fact to Kafka, and consumers catch up from the log independently"
   caption="Figure 2.2 — A blocking call couples availability; a published fact decouples it" %}

The rule: reach for async wherever immediacy isn't strictly required. A call you
*must* wait for is a call whose availability you have inherited.

## Resilience as configuration, not per-call code

Your app speaks plain HTTP or gRPC to localhost; the Istio sidecar (Envoy)
intercepts and adds mTLS, retries, timeouts, and telemetry **on the wire** —
uniformly, for every service, with zero application code. This ties straight back
to the principles chapter: resilience and security become platform defaults, not
per-service reimplementations.

{% include excalidraw.html
   file="02-mesh-handles-wire"
   alt="Two pods, each containing an app (FastAPI or grpc server, speaking plain localhost) beside an istio-proxy Envoy sidecar that handles mTLS, retries, timeouts, and traces. The two sidecars communicate over mutual TLS, encrypted and authenticated. Below, the istiod control plane distributes policy, SPIFFE identity, and telemetry config to both pods."
   caption="Figure 2.3 — The mesh moves cross-cutting concerns off your code: sidecars handle mTLS, retries, timeouts, and telemetry, configured by istiod" %}

Each pod runs your service next to an Envoy sidecar. Your code talks plain HTTP or gRPC
to localhost; the sidecar intercepts every call, adds mutual TLS so traffic between pods
is encrypted and authenticated by SPIFFE identity, and applies the retry and timeout
policy. The istiod control plane distributes that policy and identity to every sidecar,
so the behaviour is uniform and centrally configured rather than coded per service. The
`VirtualService` below is how that policy is expressed:

```yaml
# Istio VirtualService — retries and timeout for inventory, as config not code
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: inventory }
spec:
  hosts: [inventory]
  http:
    - timeout: 2s
      retries:
        attempts: 2                 # bounded — never an unbounded retry storm
        perTryTimeout: 800ms
        retryOn: connect-failure,unavailable
      route:
        - destination: { host: inventory }
```

The critical word is **bounded**: `attempts: 2`, not infinite. Unbounded
client-side retries are how a brief blip becomes a full outage — every caller
piles onto the struggling service in a retry storm. Putting the policy in the mesh
means one bounded, observable rule for every caller, instead of each team
re-inventing (and mis-tuning) retries in code.

### Cross-check it yourself

Use plain tools. `curl` and Postman exercise the REST contract — confirm a create
returns **201** and that a bad body returns **400** before your logic runs.
`ghz` throws gRPC load at `inventory` so you can watch the Istio timeout and
bounded retries behave under pressure rather than trusting they do.

The code is in `examples/02-communications/`. The run script there builds and runs
it; its `README.md` covers what it does and how to drive it.

---
*Verification status: unverified — code transcribed and normalised from the source
decks, not yet run. The `examples/02-communications/` runner moves it to verified.*
