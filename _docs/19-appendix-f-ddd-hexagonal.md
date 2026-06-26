---
title: "DDD & Hexagonal Architecture"
marker: "F"
label: "Appendix F"
order: 19
part: "Deep-dive appendices"
description: "Where service boundaries and API contracts come from — strategic DDD to place the lines, tactical DDD to model inside them, and hexagonal architecture to keep REST, gRPC, GraphQL and Kafka out of the domain."
duration: 18 minutes
---

The rest of this book assumes the boundaries are already drawn: that each service
owns a coherent slice of the business, and that its API says the right things. This
appendix is where those assumptions come from. Domain-Driven Design supplies the
*strategic* tools to place a boundary and the *tactical* tools to model what lives
inside it; hexagonal architecture is the structural discipline that keeps the four
protocols as replaceable adapters around a clean domain core. Get the boundaries
right and the APIs nearly design themselves; get them wrong and no amount of REST
polish rescues the result.

## Boundaries are an API question

An API is the contract between two **bounded contexts**, which means the hardest API
questions — where to split a system, what a contract should contain, what stays
private — are boundary questions wearing API clothing, and DDD is the discipline for
boundaries. It splits cleanly in two. **Strategic DDD** decides *where the lines go*:
subdomains (core, supporting, generic) and the bounded contexts that realise them,
each with its own model and its own ubiquitous language. **Tactical DDD** models
*what lives inside a line*: aggregates as consistency boundaries, plus entities, value
objects, and domain events — the things that become your API resources and your Kafka
payloads. Hexagonal architecture then keeps the protocols from leaking into the
business logic. The single idea worth carrying out of this appendix: boundaries
dominate outcomes far more than protocol polish does.

## Strategic DDD — placing the boundaries

Classify the business by **value and rate of change**. A *core* subdomain is the
competitive edge — complex, volatile, where the strongest people belong. A
*supporting* subdomain is necessary but not differentiating, so build it simply. A
*generic* subdomain is a solved problem you adopt or buy rather than invent — auth,
notifications. In the running system, order and pricing are core; inventory and
shipping are supporting; auth and notification are generic. The classification is not
academic: it tells you where to spend design effort and, later in this book's coupling
discussion, it predicts which parts change most.

Each subdomain becomes one or more **bounded contexts**, and a bounded context *is*
the natural unit for a service and its API: the scope within which one model and one
ubiquitous language stay consistent. The clarifying example is a single word that
refuses to mean one thing — an "order" in fulfillment (a pick-and-pack job) is not an
"order" in billing (a set of charge lines). Forcing one shared canonical model across
the whole company is how you get a schema nobody can change; instead each context
exposes *its* model through an API and translates at the edge. The context's published
API is its only public surface — schema, storage, and internal types stay private,
which is the "no leaky internal models" rule from the anti-patterns chapter restated
in DDD terms. And by Conway's law, a boundary that does not match a team's ownership
generates constant cross-team coordination, so put the lines where a team can own a
context end to end.

## Context mapping — how contexts integrate

Context mapping catalogues the ways two contexts relate, and three of those patterns
are the ones an API actually implements:

- An **Open-Host Service** is a context that, because many others integrate with it,
  publishes a stable, documented API as its public protocol — that is your REST,
  gRPC, or GraphQL surface.
- A **Published Language** is the shared, versioned schema that API speaks — OpenAPI,
  `.proto`, Avro — which is exactly what lives in the schema registry from the API
  Registry chapter.
- An **Anticorruption Layer** is the translation you build when *consuming* another
  context, so their concepts never leak into your domain.

The ACL has a cheap opposite worth naming: **Conformist**, where you accept the
upstream model wholesale and inherit its every change. That is the right call when the
upstream is clean and stable, and the wrong one when it is messy or volatile — there,
an ACL localises the blast radius of their changes to a single translation layer. The
remaining map entries are trade-offs you choose rarely: a Shared Kernel means two
contexts share a model and therefore change in lockstep (high coupling, use sparingly);
a Partnership means they co-evolve deliberately; Separate Ways means do not integrate
at all. The payoff of this section is recognition: the registry-backed contract you
already have is a Published Language, and the gateway or consumer-edge translation you
already do is an Anticorruption Layer — now they have names and a theory behind them.

## Hexagonal architecture — protocols are adapters

Hexagonal architecture (ports and adapters) is the structural answer to "keep the
protocols out of the domain," and it is the architectural payoff of the whole
protocols discussion. The **domain core** sits in the middle holding entities,
aggregates, and domain logic, and it depends on nothing — no framework, no I/O. It
declares **ports**: inbound ports (what it can be asked to do) and outbound ports
(what it needs from the world). **Driving adapters** — REST, gRPC, GraphQL — translate
an incoming protocol into a call on an inbound port. **Driven adapters** — a Postgres
repository, a Kafka publisher — implement the outbound ports. Every dependency arrow
points inward: adapters depend on the domain, never the reverse.

{% include excalidraw.html
   file="19-hexagonal-ports"
   alt="A central domain core that depends on nothing, declaring ports. On the left, three driving adapters — REST, gRPC, GraphQL — call inward through an inbound port. On the right, two driven adapters — a Postgres repository and a Kafka publisher — implement outbound ports. All dependency arrows point inward toward the core."
   caption="Figure F.1 — The domain core is isolated; the four protocols are interchangeable adapters around it" %}

The consequence is the one this book cares about: the four protocols are
*interchangeable adapters*. You can add gRPC alongside REST, or a Kafka consumer, or
swap Postgres for another store, without touching a line of domain logic. The code
makes the structure literal — the domain declares plain interfaces for what it needs,
the application service is pure, and the REST handler is a three-line translation from
protocol to a domain call.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

```java
// domain — the core declares the interfaces (ports) it needs; no framework
public interface OrderRepository { void save(Order order); }       // outbound
public interface EventPublisher  { void publish(DomainEvent e); }  // outbound

@Service                                       // pure application logic
public class PlaceOrder {
    private final OrderRepository repo;
    private final EventPublisher  events;
    public PlaceOrder(OrderRepository r, EventPublisher e) {
        this.repo = r; this.events = e;        // constructor injection: no framework leak
    }
    public Order handle(PlaceOrderCmd cmd) {
        Order order = Order.create(cmd);       // aggregate enforces invariants
        repo.save(order);
        events.publish(new OrderPlaced(order.id()));
        return order;
    }
}

// adapter — a driving adapter; gRPC/GraphQL adapters look the same
@RestController
@RequestMapping("/orders")
public class OrderController {
    private final PlaceOrder placeOrder;
    public OrderController(PlaceOrder p) { this.placeOrder = p; }
    @PostMapping public Order place(@RequestBody OrderIn body) {
        return placeOrder.handle(body.toCmd());
    }
}
```

```java
// domain — the core declares the interfaces (ports) it needs; no framework
public interface OrderRepository { void save(Order order); }       // outbound
public interface EventPublisher  { void publish(DomainEvent e); }  // outbound

@ApplicationScoped                            // pure application logic
public class PlaceOrder {
    @Inject OrderRepository repo;
    @Inject EventPublisher events;
    public Order handle(PlaceOrderCmd cmd) {
        Order order = Order.create(cmd);      // aggregate enforces invariants
        repo.save(order);
        events.publish(new OrderPlaced(order.id()));
        return order;
    }
}

// adapter — a driving adapter; gRPC/GraphQL adapters look the same
@Path("/orders")
public class OrderResource {
    @Inject PlaceOrder placeOrder;
    @POST public Order place(OrderIn body) { return placeOrder.handle(body.toCmd()); }
}
```

```csharp
// domain — the core declares the interfaces (ports) it needs; no framework
public interface IOrderRepository { Task SaveAsync(Order order, CancellationToken ct); }
public interface IEventPublisher  { Task PublishAsync(IDomainEvent e, CancellationToken ct); }

// pure application logic; C# 12 primary constructor — no DI annotations needed
public class PlaceOrder(IOrderRepository repo, IEventPublisher events)
{
    public async Task<Order> HandleAsync(PlaceOrderCmd cmd, CancellationToken ct)
    {
        var order = Order.Create(cmd);                // aggregate enforces invariants
        await repo.SaveAsync(order, ct);
        await events.PublishAsync(new OrderPlaced(order.Id), ct);
        return order;
    }
}

// adapter — a driving adapter; gRPC/GraphQL adapters look the same
[ApiController, Route("orders")]
public class OrderController(PlaceOrder placeOrder) : ControllerBase
{
    [HttpPost] public Task<Order> Place(
        [FromBody] OrderIn body, CancellationToken ct) =>
        placeOrder.HandleAsync(body.ToCmd(), ct);
}

// outbound adapters (separate project): EfCoreOrderRepository : IOrderRepository,
//                                       MassTransitEventPublisher : IEventPublisher.
// Wire them in Program.cs: builder.Services.AddScoped<IOrderRepository, …>();
```

```python
# domain/ports.py — the domain declares the interfaces it needs (ports)
class OrderRepository(Protocol):              # outbound port
    async def save(self, order: Order) -> None: ...
class EventPublisher(Protocol):               # outbound port
    async def publish(self, e: DomainEvent) -> None: ...

# domain/service.py — pure application logic: no framework, no I/O
class PlaceOrder:
    def __init__(self, repo: OrderRepository, events: EventPublisher):
        self.repo, self.events = repo, events
    async def __call__(self, cmd: PlaceOrderCmd) -> Order:
        order = Order.create(cmd)             # aggregate enforces invariants
        await self.repo.save(order)
        await self.events.publish(OrderPlaced(order.id))
        return order

# adapters/rest.py — a driving adapter; gRPC/GraphQL look the same
@app.post("/orders")
async def place_order(body: OrderIn, uc: PlaceOrder = Depends(build_uc)):
    return await uc(body.to_cmd())            # protocol -> domain, nothing more
```

```cpp
// domain/ports.hpp — the domain declares the interfaces it needs.
struct OrderRepository {                       // outbound port
  virtual Task<> save(const Order&) = 0;
  virtual ~OrderRepository() = default;
};
struct EventPublisher {                        // outbound port
  virtual Task<> publish(const DomainEvent&) = 0;
  virtual ~EventPublisher() = default;
};

// domain/place_order.hpp — pure logic: no framework, no I/O
class PlaceOrder {
 public:
  PlaceOrder(OrderRepository& repo, EventPublisher& events)
      : repo_(repo), events_(events) {}
  Task<Order> operator()(PlaceOrderCmd cmd) {
    Order o = Order::create(cmd);              // aggregate invariants
    co_await repo_.save(o);
    co_await events_.publish(OrderPlaced{o.id});
    co_return o;
  }
 private:
  OrderRepository& repo_;
  EventPublisher&  events_;
};

// adapters/rest.cpp — driving adapter; gRPC/GraphQL look the same
Task<> Orders::place(HttpRequestPtr req, auto cb) {
  Order o = co_await place_order_(parse<OrderIn>(req).to_cmd());
  cb(HttpResponse::newHttpJsonResponse(to_json(o)));
}
```

Read the three blocks the same way in every language. The **ports** are plain
interfaces the domain declares for what it needs — a repository and an event publisher
— and the domain imports nothing else. The application service `PlaceOrder` is **pure**:
it creates the aggregate (which enforces its own invariants), saves through the
outbound port, publishes a domain event through the outbound port, and never references
the web framework, the database driver, or the Kafka client. The **driving adapter** is
trivial — it turns a request body into a command and calls the use case; a gRPC or
GraphQL adapter would be the same handful of lines against the same inbound call. The
outbound ports are satisfied by **driven adapters** (a Postgres repository, a Kafka
publisher) injected at startup. That injection is dependency inversion in service of
the boundary: the protocols and the infrastructure are replaceable, and the domain is
the stable thing they all depend on.

## Aggregates and domain events

Tactical DDD is where the modelling inside a context ties three earlier parts of the
book together. An **aggregate** is a cluster of objects treated as one consistency
unit — the boundary inside which invariants hold and a single transaction commits — and
it usually maps to one API resource. Because it is the transaction boundary, it is also
the **outbox boundary** from the Data chapter: the state change and the domain event
commit together, atomically. **Domain events** (`OrderPlaced`) are first-class in DDD,
and they are precisely the payloads that become Kafka events other contexts react to —
choreography between bounded contexts, as in the Event-Driven chapter. The rule that
keeps this tractable is to keep aggregates small: one aggregate per transaction,
reference other aggregates by id rather than nesting them, and let events connect them
— which is exactly why consistency *across* aggregates needs a saga, the subject of the
Saga appendix.

## How DDD maps to the stack

Every DDD concept on the left has already appeared, concretely, on the right:

- **Bounded context** → a service and its API boundary.
- **Open-Host Service / Published Language** → the REST/gRPC/GraphQL contract plus the
  schema registry.
- **Anticorruption Layer** → model translation at the gateway or consumer edge.
- **Aggregate** → an API resource, and the transaction/outbox boundary behind it.
- **Domain event** → a Kafka event other contexts consume.

DDD is not a separate methodology bolted onto the architecture; it is the naming and
the reasoning behind the boundaries the whole system already relies on. The full
treatment is Vlad Khononov's *Learning Domain-Driven Design* (O'Reilly, 2021).

### Cross-check it yourself

Test the isolation claim directly, because it is the one that pays the rent. In the
domain package — `domain/` in Python or C++, the application service and its port
interfaces in the JVM and .NET versions — grep for framework imports: there should be
no `fastapi`, no `org.springframework.web`, no `Microsoft.AspNetCore`, no
`drogon`/`grpc`, no database driver. The application service should import only its own
domain types and the ports it declares. Then prove replaceability by construction: add
a second driving adapter (a gRPC endpoint, or a Kafka consumer) that calls the *same*
`PlaceOrder` use case, and confirm the domain files do not change in that diff — only a
new adapter file appears. A clean domain import list plus a no-domain-change diff when
you bolt on a protocol is hexagonal architecture actually holding.

---
*Verification status: unverified — code transcribed and normalised from the source
decks, not yet run. The points most worth confirming on a real build: the Python
`Protocol`-based ports resolve under the project's type checker, the Quarkus and Spring
constructor/field injection wires `PlaceOrder` without a framework import in the domain
type, the .NET primary-constructor service registers cleanly in `Program.cs`, and the
C++ coroutine `Task<>` port signatures compile against Drogon's adapter. The
`examples/19-ddd-hexagonal/` runner moves it to verified.*
