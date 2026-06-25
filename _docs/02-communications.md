---
title: "Communications"
order: 2
part: "Foundations & the system"
description: "Four interaction styles and four defaults — REST at the edge, gRPC for internal calls, GraphQL for composed reads, async events for facts — and pushing resilience onto the mesh instead of into your code."
duration: 18 minutes
---

A service talks to the world and to its peers, and the mistake is using one wire
for everything. There are four interaction styles, and each has a default that
fits it. Real systems use all four; the skill is matching each call to the right
one.

- **REST** for the public, edge surface — reach and caching matter most.
- **gRPC** for internal service-to-service calls — latency and streaming matter.
- **GraphQL** for client-driven reads that compose many sources in one round trip.
- **Async events** for decoupled facts that fan out to whoever cares.

## REST at the edge

This is the public surface — in our system, `order-service`. Four things teams
routinely get wrong, and the code gets right: resource-shaped URLs (nouns, not
verbs), request and response contracts validated before bad input reaches your
logic, correct status codes (**201** on create, not 200), and **cursor**
pagination rather than offset (offset breaks under concurrent writes and slows
down at depth).

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

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

The field numbers (`= 1`, `= 2`) are the wire contract, not cosmetic — **15 ·
Appendix B** explains exactly why they can never be reused. Generate stubs with
`protoc` or `buf`, and both sides share types.

## Synchronous coupling vs. asynchronous facts

This is the central trade-off of the whole book in one picture. A synchronous
call couples caller to callee in *time* and *availability*: if `payment` is down,
the order request fails too, and availability multiplies downward across a chain.
Emitting `order.placed` as a fact lets the order succeed immediately; consumers
that were down catch up from the log later.

{% include excalidraw.html
   file="02-sync-vs-async"
   alt="Top row: order makes a synchronous call to payment and blocks on it, so if payment is down the order fails. Bottom row: order emits an order.placed fact to Kafka, and consumers catch up from the log independently"
   caption="Figure 2.1 — A blocking call couples availability; a published fact decouples it" %}

The rule: reach for async wherever immediacy isn't strictly required. A call you
*must* wait for is a call whose availability you have inherited.

## Resilience as configuration, not per-call code

Your app speaks plain HTTP or gRPC to localhost; the Istio sidecar (Envoy)
intercepts and adds mTLS, retries, timeouts, and telemetry **on the wire** —
uniformly, for every service, with zero application code. This ties straight back
to the principles chapter: resilience and security become platform defaults, not
per-service reimplementations.

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
