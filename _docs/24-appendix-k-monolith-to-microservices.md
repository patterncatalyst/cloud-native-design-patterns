---
title: "Monolith to Microservices"
marker: "K"
label: "Appendix K"
order: 24
part: "Deep-dive appendices"
description: "Decomposing a monolith with the system still running — the modular monolith as a frequent destination, the strangler-fig family (identify, move, redirect), content-based routing for fine-grained cutover, and the decorating collaborator for legacy you can't touch."
duration: 28 minutes
---

You do not decompose a monolith by stopping it and rewriting; you decompose it
incrementally, one bounded asset at a time, with the system serving users the whole way
through. This appendix walks the patterns that survive a migration without a flag day:
the monolith as a legitimate starting point, the modular monolith as a frequently-correct
*destination*, the strangler-fig family for progressive extraction, content-based routing
for fine-grained cutover, and the decorating collaborator for wrapping legacy code you are
not allowed to change. The single property to design for, named up front and returned to at
the end, is **reversibility**: every step should be a config change you can undo without
coordinating a release.

## A monolith is a unit of deployment

Define the term before fixing it. A monolith is not a code-organisation problem — it is a
*deployment* property. A clean codebase with clear modules, layers, and tests is still a
monolith if it ships as one binary on one heartbeat. That property has real costs: a change
anywhere means redeploying everything, a bug in reporting can take down payments, and one
scaling unit has to serve very different workloads. But the costs do not make monoliths
*wrong*. For a new product, a small team, or anything that fits in one team's head, a
monolith is often the simplest and fastest path to value, and premature decomposition is its
own anti-pattern. The real question is never "monolith or microservices?" in the abstract —
it is "when does *this* monolith start hurting more than it helps?", and that is when these
patterns earn their keep.

{% include excalidraw.html
   file="24-monolith-unit"
   alt="A monolith as a unit of deployment. Web/mobile and other systems call into a single deployable that contains every module — auth, orders, inventory, catalog, payments, shipping, reporting, notifications, admin, pricing, returns, search — all sharing one database that every module reads and writes, giving schema-level coupling everywhere. A change anywhere means redeploying everything, a bug in reporting can take down payments, and one scaling unit serves very different workloads — but it is often the simplest, fastest path to value when the system fits in one team's head."
   caption="Figure K.1 — A monolith is a deployment property: one binary, one heartbeat, one shared database — every module ships and scales together" %}

## The modular monolith — often the destination

The modular monolith is the intermediate pattern that is frequently the right *destination*,
not merely a stepping stone. It is still one deployable, but with strict in-process module
boundaries: each module exposes a clear public API (`PlaceOrder`, `ReserveStock`,
`ChargeCard`) and keeps its internals private. The defining discipline is *enforcement* — not
a gentlemen's agreement but build tooling that fails CI when one module reaches into
another's internals (import-linter or modulegraph rules in Python; module-system or
build-dependency rules on the JVM and .NET). You get most of the benefit of microservices —
clear boundaries, replaceable modules, independent reasoning — at a fraction of the
operational cost: one deployment, one log stream, one debugger session. And if you later need
to split for real, it is a small refactor (rename the public API, move the files, ship) not a
rewrite.

{% include excalidraw.html
   file="24-modular-monolith"
   alt="A modular monolith, still a single deployable, holding an Orders module (public API PlaceOrder and GetOrder, private internals guarded by the build tool), an Inventory module (public API ReserveStock and CheckAvailability, no shared types), and a Payments module (public API ChargeCard and Refund, its own data schema). They share one database but with separate schemas — orders, inventory, payments — and no cross-schema joins, enforced. Modules talk only through their public API, enforced by linters and build rules rather than a gentlemen's agreement."
   caption="Figure K.2 — The modular monolith: one deployable, strict in-process boundaries enforced by build tooling, separate schemas" %}

The genuinely hard part of decomposition is the *database*, and the modular monolith lets you
do it while still one process.

The hardest coupling to see is in the data — schema dependencies, cross-table joins, and
reporting queries that are invisible until you try to move them. So split the data *before*
you split the process: give each module its own store, its own connection pool, and its own
migration history, and replace cross-module joins with a service call or an event
subscription. That is exactly the discipline microservices demand, but with one operational
target instead of many. Start with the highest-coupling module, and tackle the database the
reporting layer joins across early, because it is the second-hardest. Once the data is
decomposed, promoting a module to a separate service is a change of deployment topology, not a
data-migration project — and many teams discover at this point that the modular monolith with
decomposed data is already enough.

{% include excalidraw.html
   file="24-decomposed-databases"
   alt="A modular monolith that is still one process, but with decomposed databases. The Orders, Inventory, and Payments modules each own a separate database: Orders DB on its own Postgres with its own schema and connection pool, Inventory DB on its own Postgres or Mongo, and Payments DB on its own Postgres, encrypted at rest behind a PII boundary. Cross-module data is now async and event-driven — the same discipline as microservices without the operational cost — so promoting one module to a process is a deployment change, not a data-migration project."
   caption="Figure K.3 — Decompose the data while still one process: each module gets its own store, so promotion later is a deployment change, not a migration" %}

## Identify → move → redirect

When you do extract a service, the unit of work is Martin Fowler's strangler-fig pattern,
named for the vine that grows around its host tree until the host is gone and the vine stands
on its own. Three steps, repeated per asset. **Identify** a bounded asset — not "the orders
subsystem" but "order creation" or "order status query" specifically; the smaller and more
bounded, the safer the move. **Move** by building the new service alongside the monolith,
replicating the behaviour, and testing it in parallel without production traffic. **Redirect**
callers to the new service. Each cycle is independently reversible — if the new service is
wrong, redirect back and try again.

{% include excalidraw.html
   file="23-strangler-fig"
   alt="Clients hit one URL at a proxy. The proxy routes a widening slice of traffic (1% to 100%) to a new service holding the extracted asset, and everything else to a shrinking monolith. A note says the proxy is step zero, added first, and that redirect is a proxy config change — widen to roll forward, narrow to roll back — so every step is reversible."
   caption="Figure K.4 — The strangler-fig cutover: a proxy redirects a widening slice to the new service while the monolith shrinks; every step is reversible" %}

## The proxy is step zero

The precondition for incremental migration is a routing layer, introduced *before* you extract
anything. On day zero, clients hit the proxy and the proxy forwards everything to the monolith;
behaviour is unchanged. But now you hold the lever: the proxy is where you later route 1% of
`/orders/*` to the extracted service, then 5%, then 100%. Without this step, every cutover
needs a coordinated client release; with it, every cutover is a proxy config change — and the
proxy is also the right place for the TLS, auth, rate-limiting, and observability you wanted
anyway. The strangler-fig literature calls this *event interception*: you intercept the request
before it reaches the legacy system, giving yourself a place to redirect later.

{% include excalidraw.html
   file="24-proxy-step-zero"
   alt="Step zero of every migration: introduce a routing layer before extracting anything. Clients hit a proxy or reverse proxy (nginx, Envoy, HAProxy, or YARP) through which all traffic now flows, and the proxy forwards everything to the monolith, which still owns everything and doesn't know about the proxy. New services like an extracted Orders.svc and a future Inventory.svc are soon to come behind the proxy's future routes. There is zero behaviour change for clients on day one, but the lever to route traffic to extracted services is now in place, and the proxy is also where TLS, auth, rate-limiting, and observability consolidate."
   caption="Figure K.5 — The proxy is step zero: add the routing layer first, forwarding everything to the monolith, so later cutovers are a config change not a client release" %}

Once the proxy is in place it earns its keep by *redirecting* a slice — by path
(`/orders/*` → new service), by header (`X-Tenant: acme` → new service), by percentage, or by
feature flag. The new service handles its slice and the monolith handles the rest, while clients
still see one URL, one auth boundary, one TLS cert. Roll forward by widening the new-service
route; roll back by narrowing it — and if the new service fails completely, the monolith picks
up, which is the entire point. Instrument both paths so you can verify the new service produces
the same outcomes as the monolith before you widen. This is the same routing machinery as the L7
Routing appendix — `nginx` server blocks, Envoy route configs, or an Istio `VirtualService` —
used for migration instead of canary release.

## The shared database — a deliberate intermediate state

Sometimes the data split is too risky to do at the same time as the process split. Then you let
the new service and the monolith share the database for a while: both read and write the same
tables, and the new service owns the *API* but not the *data*. This is genuinely useful for
extracting reads first (the new service is a nicer API over a read replica) and as a stepping
stone when the data migration is its own project. But it is a transition state, never a
destination — every schema change now needs both apps to agree, and that coordination tax grows
with every team that owns part of the same database. Plan its dissolution from the start: the
next step is to give the new service its own store, via CDC out of the monolith's database,
dual-writing during a brief sync window, or event-sourcing the data across. A shared-database
strangler with no exit plan simply becomes the new monolith.

{% include excalidraw.html
   file="24-shared-database"
   alt="The strangler fig with a shared database as a deliberate intermediate state: process boundary first, data boundary later. Clients hit a proxy that routes to a new Orders service, which reads and writes the same DB and owns the API but not the data, and to the monolith, which still reads and writes the same DB. Both point at a Shared DB whose tables both apps know, with no schema-change isolation. Two apps writing the same tables is a coordination tax — schema changes need both sides to agree — so the next step is to give the new service its own store."
   caption="Figure K.6 — The shared-database strangler: split the process first and the data later; a deliberate intermediate state, never a destination" %}

## Content-based routing during migration

Path-based proxying cuts over a whole endpoint at once. Content-based routing is finer: it reads
the request *body* and decides by payload — tenant, region, feature flag, user segment — so you
can cut over one tenant at a time, watch it under real traffic, then widen. The URL is identical
across both backends; only the content differs.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

```java
// Spring Web + RestClient — a content-aware proxy that reads the request
// body and forwards to the new service or the monolith.
@RestController
@RequestMapping("/orders")
public class OrderRouter {
    private final RestClient monolith;
    private final RestClient newSvc;
    private final RestClient euSvc;

    public OrderRouter(RestClient.Builder builder) {
        this.monolith = builder.baseUrl("http://monolith.svc:8080").build();
        this.newSvc   = builder.baseUrl("http://orders.svc:8080").build();
        this.euSvc    = builder.baseUrl("http://orders-eu.svc:8080").build();
    }

    @PostMapping
    public ResponseEntity<Order> route(@RequestBody Map<String,Object> body,
                                       @RequestHeader Map<String,String> headers) {
        String tenant = (String) body.getOrDefault("tenant", "");
        String region = (String) body.getOrDefault("region", "");
        RestClient upstream =                        // decide by content, not URL
            "acme".equals(tenant) ? newSvc :         // cut Acme over
            "EU".equals(region)   ? euSvc  :         // regional service
                                    monolith;        // default: legacy
        return upstream.post()
            .headers(h -> h.setAll(headers))
            .body(body)
            .retrieve()
            .toEntity(Order.class);
    }
}
```

```java
// Quarkus REST + MicroProfile REST Client — a content-aware proxy that reads
// the body and forwards to the new service or the monolith. In production this
// typically lives in a sidecar; the resource shows the shape cleanly.
@Path("/orders")
public class OrderRouter {
    @Inject @RestClient MonolithClient monolith;       // legacy
    @Inject @RestClient OrdersClient   newSvc;          // extracted
    @Inject @RestClient OrdersEuClient euSvc;           // regional

    @POST
    @Consumes("application/json")
    @Produces("application/json")
    public JsonObject route(JsonObject body) {
        String tenant = body.getString("tenant", "");   // decide by content, not URL
        String region = body.getString("region", "");
        if ("acme".equals(tenant)) return newSvc.placeOrder(body);    // cut Acme over
        if ("EU".equals(region))   return euSvc.placeOrder(body);     // regional
        return monolith.placeOrder(body);                             // default: legacy
    }
}

@RegisterRestClient(configKey = "orders-new")
public interface OrdersClient {
    @POST JsonObject placeOrder(JsonObject body);
}
```

```csharp
// ASP.NET Core minimal API + IHttpClientFactory — content-aware proxy that
// reads the body and forwards to the new service or the monolith. In production
// this usually lives in a sidecar / YARP; the minimal API shows the pattern.

// Program.cs
builder.Services.AddHttpClient("monolith", c => c.BaseAddress = new("http://monolith.svc:8080"));
builder.Services.AddHttpClient("orders",   c => c.BaseAddress = new("http://orders.svc:8080"));
builder.Services.AddHttpClient("ordersEu", c => c.BaseAddress = new("http://orders-eu.svc:8080"));

app.MapPost("/orders", async (HttpContext ctx, IHttpClientFactory factory) =>
{
    var body = await ctx.Request.ReadFromJsonAsync<JsonObject>()
                  ?? throw new BadHttpRequestException("empty body");

    var tenant = body["tenant"]?.GetValue<string>() ?? "";   // decide by content
    var region = body["region"]?.GetValue<string>() ?? "";
    var upstream = (tenant, region) switch
    {
        ("acme", _) => factory.CreateClient("orders"),    // new service
        (_, "EU")   => factory.CreateClient("ordersEu"),  // regional
        _           => factory.CreateClient("monolith")   // default: legacy
    };

    using var response = await upstream.PostAsJsonAsync("/orders", body);
    return Results.Stream(
        async stream => await response.Content.CopyToAsync(stream),
        response.Content.Headers.ContentType?.ToString());
});
```

```python
# FastAPI middleware that routes by request content during cutover.
# In production this would typically live in a sidecar / proxy.
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import httpx

app = FastAPI()
MONOLITH = "http://monolith.svc.cluster.local:8080"
NEW_SVC  = "http://orders.svc.cluster.local:8080"
EU_SVC   = "http://orders-eu.svc.cluster.local:8080"
client = httpx.AsyncClient(timeout=5.0)              # reused: warm connection pool

@app.middleware("http")
async def content_router(request: Request, call_next):
    if request.url.path.startswith("/orders"):
        body = await request.body()
        payload = json_or_empty(body)                # decide by content, not URL
        if payload.get("tenant") == "acme":
            upstream = NEW_SVC                        # cut Acme over
        elif payload.get("region") == "EU":
            upstream = EU_SVC                         # regional service
        else:
            upstream = MONOLITH                       # default: legacy
        return await forward(upstream, request, body)
    return await call_next(request)

async def forward(upstream, request, body):
    r = await client.request(
        request.method, f"{upstream}{request.url.path}",
        headers={k: v for k, v in request.headers.items() if k != "host"},
        content=body,                                 # hand the consumed bytes through
    )
    return StreamingResponse(r.aiter_bytes(), status_code=r.status_code,
                             headers=dict(r.headers))
```

```cpp
// Content-based routing during cutover — Drogon middleware.
// (In production this typically lives in a sidecar; middleware shows the shape.)
constexpr auto MONOLITH = "http://monolith.svc.cluster.local:8080";
constexpr auto NEW_SVC  = "http://orders.svc.cluster.local:8080";
constexpr auto EU_SVC   = "http://orders-eu.svc.cluster.local:8080";

Task<> content_router(HttpRequestPtr req, auto next) {
  if (!req->path().starts_with("/orders")) {
    co_await next(req); co_return;             // other routes pass through
  }
  auto body = req->bodyJson();                  // nlohmann::json
  std::string upstream;
  if (body.value("tenant", "") == "acme") {
    upstream = NEW_SVC;                         // cut Acme over
  } else if (body.value("region", "") == "EU") {
    upstream = EU_SVC;                          // regional service
  } else {
    upstream = MONOLITH;                        // default: legacy
  }
  cpp_httplib::Client client{upstream};
  auto r = client.Post(req->path(), req->headers(), req->body(),
                       "application/json");
  auto resp = HttpResponse::newHttpResponse();
  resp->setStatusCode(static_cast<HttpStatusCode>(r->status));
  resp->setBody(r->body);
  co_yield resp;
}
```

The shape is identical everywhere: read the payload, pick an upstream by content rather than
URL, and forward. Two implementation notes matter. The body is consumed when you read it, so you
must hand the same bytes through to the upstream — the Python `forward` and the C++ `req->body()`
both do this deliberately. And the HTTP client is reused across requests so its connection pool
stays warm. The only real cost is the per-request body parse; over a migration measured in days
it is irrelevant next to the risk it controls, but over months it adds up — which is why, in
production, the same logic often moves into a sidecar's Lua/WASM filter or an `EnvoyFilter`.

## The decorating collaborator

The proxy patterns own *routing*; the decorating collaborator owns *behaviour*. The new service
sits in front of a legacy API and adds cross-cutting capability — caching, audit, validation,
enrichment, fan-out to Kafka — while the legacy service stays unaware it has been wrapped.
Clients talk to the decorator, which delegates the underlying work to the legacy service but
contributes everything else. It is a real microservice (its own data, deploy, and scaling), and
over time it can absorb more behaviour until the legacy service can be retired without clients
noticing. This is the pattern for legacy you *cannot* modify — a vendor product, a fragile system
touching which is forbidden — and for adding capabilities the original never had.

{% include excalidraw.html
   file="24-decorating-collaborator"
   alt="The decorating collaborator: the new service wraps the old, adds capability, then becomes the API. Clients talk to a decorating service that sits in front of the legacy API and adds caching, audit, validation, rate-limiting, fan-out to Kafka, and metrics, while the legacy service stays unaware it has been wrapped and remains the source of truth. The decorator also emits events to Kafka as a new capability. Clients now talk to the decorator; the legacy service keeps running and is eventually replaced behind the decorator's API — unlike a plain proxy, the decorator owns behaviour, not just routing."
   caption="Figure K.7 — The decorating collaborator: a real service wraps the legacy API, adds behaviour, and absorbs it over time — for legacy you cannot modify" %}

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

```java
// Spring REST that wraps a legacy /orders API and adds a Redis cache and
// Kafka event emission. The legacy service is unchanged.
@RestController
@RequestMapping("/orders")
public class OrdersDecorator {
    private final RestClient legacy;
    private final RedisTemplate<String, Order> cache;
    private final KafkaTemplate<String, Order> kafka;
    private static final Duration TTL = Duration.ofSeconds(60);

    public OrdersDecorator(RestClient.Builder b,
                           RedisTemplate<String, Order> cache,
                           KafkaTemplate<String, Order> kafka) {
        this.legacy = b.baseUrl("http://legacy.svc:8080").build();
        this.cache = cache;
        this.kafka = kafka;
    }

    @GetMapping("/{id}")
    public Order get(@PathVariable String id) {
        String key = "order:" + id;
        Order cached = cache.opsForValue().get(key);            // 1. cache hit
        if (cached != null) return cached;
        Order order = legacy.get().uri("/orders/{id}", id)      // 2. legacy fallback
            .retrieve().body(Order.class);
        cache.opsForValue().set(key, order, TTL);               // 3. populate
        return order;
    }

    @PostMapping
    public Order place(@RequestBody Order body) {
        Order order = legacy.post().uri("/orders")              // 1. legacy first (source of truth)
            .body(body).retrieve().body(Order.class);
        kafka.send("order.placed", order.id(), order);          // 2. emit event
        cache.delete("order:" + order.id());                    // 3. invalidate
        return order;
    }
}
```

```java
// Quarkus REST that wraps a legacy /orders API and adds Redis caching and
// Kafka event emission. The legacy service is unchanged.
@Path("/orders")
public class OrdersDecorator {
    @Inject @RestClient LegacyOrdersClient legacy;
    @Inject @Channel("order-placed") Emitter<Order> events;
    final ValueCommands<String, Order> cache;

    public OrdersDecorator(RedisDataSource redis) {
        this.cache = redis.value(Order.class);
    }

    @GET @Path("/{id}")
    public Order getOrder(String id) {
        Order cached = cache.get("order:" + id);                // 1. cache hit
        if (cached != null) return cached;
        Order order = legacy.get(id);                           // 2. legacy on miss
        cache.setex("order:" + id, 60, order);                  // 3. populate
        return order;
    }

    @POST
    public Order placeOrder(Order body) {
        Order order = legacy.create(body);                      // 1. legacy first
        events.send(order);                                     // 2. emit event
        cache.del("order:" + order.id());                       // 3. invalidate
        return order;
    }
}
```

```csharp
// ASP.NET Core controller that wraps a legacy /orders API and adds a Redis
// cache (IDistributedCache) and Kafka events (MassTransit). Legacy is unchanged.
[ApiController, Route("orders")]
public class OrdersDecorator(
    IHttpClientFactory factory,
    IDistributedCache  cache,
    IPublishEndpoint   bus) : ControllerBase            // MassTransit
{
    private static readonly DistributedCacheEntryOptions TTL =
        new() { AbsoluteExpirationRelativeToNow = TimeSpan.FromSeconds(60) };

    [HttpGet("{id}")]
    public async Task<ActionResult<Order>> Get(string id, CancellationToken ct)
    {
        var key    = $"order:{id}";
        var cached = await cache.GetStringAsync(key, ct);                 // 1. cache
        if (cached is not null)
            return Ok(JsonSerializer.Deserialize<Order>(cached));         //    hit

        var legacy = factory.CreateClient("legacy");                      // 2. legacy fallback
        var order  = await legacy.GetFromJsonAsync<Order>($"/orders/{id}", ct)
                     ?? throw new KeyNotFoundException();
        await cache.SetStringAsync(key, JsonSerializer.Serialize(order), TTL, ct); // 3. populate
        return Ok(order);
    }

    [HttpPost]
    public async Task<ActionResult<Order>> Place(Order body, CancellationToken ct)
    {
        var legacy = factory.CreateClient("legacy");
        var resp   = await legacy.PostAsJsonAsync("/orders", body, ct);   // 1. legacy first
        var order  = await resp.Content.ReadFromJsonAsync<Order>(ct)
                     ?? throw new InvalidOperationException("no order");
        await bus.Publish(new OrderPlaced(order.Id, order.Total), ct);    // 2. emit event
        await cache.RemoveAsync($"order:{order.Id}", ct);                 // 3. invalidate
        return Ok(order);
    }
}
```

```python
# FastAPI app that wraps a legacy /orders API and adds Redis caching and
# Kafka event emission. The legacy service is unchanged.
from fastapi import FastAPI
from redis.asyncio import Redis
from aiokafka import AIOKafkaProducer
import httpx, json

app    = FastAPI()
legacy = httpx.AsyncClient(base_url="http://legacy.svc:8080", timeout=5.0)
cache  = Redis.from_url("redis://redis:6379")
audit  = AIOKafkaProducer(bootstrap_servers="kafka:9092")

@app.get("/orders/{oid}")
async def get_order(oid: str):
    if cached := await cache.get(f"order:{oid}"):           # 1. cache hit
        return json.loads(cached)
    r = await legacy.get(f"/orders/{oid}")                  # 2. legacy call
    order = r.json()
    await cache.setex(f"order:{oid}", 60, json.dumps(order))  # 3. populate
    return order

@app.post("/orders")
async def place_order(body: dict):
    r = await legacy.post("/orders", json=body)             # 1. legacy first
    order = r.json()
    await audit.send_and_wait("order.placed",               # 2. emit event
                              json.dumps(order).encode())
    await cache.delete(f"order:{order['id']}")              # 3. invalidate
    return order
```

```cpp
// Drogon decorator wrapping a legacy /orders API: Redis caching of GET
// responses and Kafka event emission on writes. The legacy service is unchanged.
class OrdersDecorator : public drogon::HttpController<OrdersDecorator> {
 public:
  METHOD_LIST_BEGIN
    METHOD_ADD(OrdersDecorator::getOrder,   "/orders/{oid}", Get);
    METHOD_ADD(OrdersDecorator::placeOrder, "/orders",       Post);
  METHOD_LIST_END

  Task<> getOrder(HttpRequestPtr req, auto cb, std::string oid) {
    auto key = "order:" + oid;
    if (auto hit = co_await cache_.get(key)) {  // 1. cache hit
      cb(json_response(*hit)); co_return;
    }
    auto body = co_await legacy_.get("/orders/" + oid);  // 2. miss → legacy
    co_await cache_.setex(key, 60, body);                // 3. populate
    cb(json_response(body));
  }

  Task<> placeOrder(HttpRequestPtr req, auto cb) {
    auto body  = co_await legacy_.post("/orders", req->body());  // 1. legacy first
    auto order = json::parse(body);
    producer_.send("order.placed", body);                        // 2. emit
    co_await cache_.del("order:" + order["id"].get<std::string>());  // 3. invalidate
    cb(json_response(body));
  }
};
```

The two paths tell the whole story. The `GET` adds a Redis cache with a short TTL — a capability
the legacy service never had — falling back to the legacy call on a miss and populating the cache
on the way out. The `POST` delegates the write to the legacy service (still the source of truth),
*then* emits a Kafka event so downstream systems can subscribe to a new event stream, *then*
invalidates the cache. The legacy service has no idea it has been wrapped, and clients have no
idea they are talking to a decorator. Over time you move more behaviour in — validation,
idempotency keys, dedup, multi-source reads — and when you are ready to retire the legacy service
you implement storage inside the decorator (or a clean service it calls) and stop forwarding,
while the client-facing API never changes.

## Choosing the right migration pattern

The decision rules, in priority order. A **modular monolith is frequently a fine destination** —
microservices have real operational cost, and not every system warrants paying it. **Split the
database early**, while still one process, because that is where projects get stuck for years and
where being wrong is cheapest to redo. **No proxy, no incremental migration** — without the
routing layer every cutover is a coordinated client release. A **shared-database strangler is a
means, never an end** — plan its dissolution or it becomes the new monolith. Reach for
**content-based routing** when you need fine-grained, tenant-at-a-time progress, and the
**decorating collaborator** when you need to add capability to code you cannot change. The
architectural take-home is the property named at the start: design every step to be a reversible
config change, because migrations fail when they reach an irreversible step too early. The
book-length treatment is Sam Newman's *Monolith to Microservices* (O'Reilly).

### Cross-check it yourself

Prove the two properties this appendix actually rests on: reversibility and equivalence. Stand the
content router in front of a stub "monolith" and a stub "new service" that tag their responses,
and drive traffic with `hey`. Send a batch with `tenant: acme` and confirm every one lands on the
new service; send the rest and confirm they land on the monolith; then flip the rule (or widen the
percentage) and watch the split move — and flip it *back* and confirm traffic returns to the
monolith with no client change. That round-trip is reversibility. For the decorator, hit the `GET`
twice and confirm the second response is served from cache (the legacy backend sees one call, not
two — check its access log), then `POST` once and confirm both that the legacy service recorded the
write *and* that an `order.placed` event landed on Kafka. Same client-visible API, new behaviour
underneath, legacy untouched — that is the decorator doing its job.

---
*Verification status: unverified — code transcribed and normalised from the source decks (the
Quarkus router and decorator are shown in blocking style; the .NET decorator's write path was
cleaned to await rather than block on a Task), not yet run. Worth confirming on a real build: the
Spring `RestClient` body/`toEntity` round-trip preserves headers and status, the Quarkus blocking
`RedisDataSource` `ValueCommands` and MicroProfile REST Client signatures, the .NET minimal-API
`Results.Stream` passthrough, the FastAPI middleware re-reading a consumed body, and the C++
forward client choice (a plain HTTP client is used for the proxy hop rather than the main Drogon
stack). The `examples/24-monolith-to-microservices/` runner moves it to verified.*
