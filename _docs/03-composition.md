---
title: "Composition"
order: 3
part: "Foundations & the system"
description: "Composing many back-ends behind one schema without coupling them — a GraphQL gateway that fans out to REST and gRPC, the resolver that makes it concrete, and the three places aggregation belongs."
duration: 18 minutes
---

A client rarely wants what a single service holds. It wants an order *and* its
live stock *and* its shipment status — data spread across services. The wrong fix
is to have `order-service` call `inventory` call `pricing` in a chain. The right
fix is to push the aggregation **outward, to the edge**, and keep the services
unaware of each other.

## One query, many services

A GraphQL gateway presents **one schema** to clients and fans out to REST and gRPC
back-ends, then joins and shapes the result. The client makes a single round trip
and asks for exactly the fields it needs — no more, no less.

```graphql
# the gateway's schema — one contract for every client
type Query {
  order(id: ID!): Order
}
type Order {
  id: ID!
  sku: String!
  status: String!
  stock: Int!        # resolved on demand from inventory-service
}
```

A client asks one question:

```graphql
query {
  order(id: "A-1001") {
    sku
    status
    stock            # the gateway fans this field out to inventory-service
  }
}
```

The crucial property: the services stay unaware of each other. The gateway owns
the composition.

{% include excalidraw.html
   file="03-composition"
   alt="A client sends one GraphQL query to the graphql-gateway; the gateway calls order-service over REST for the order fields and inventory over gRPC for the stock field, then joins and returns one result"
   caption="Figure 3.1 — One query in; the gateway fans out to REST and gRPC and joins" %}

## The resolver makes it concrete

Federation stops being abstract at the resolver. The top-level `order` query
calls `order-service` over REST; the `Order.stock` field resolves *on demand* by
calling `inventory` over gRPC. **Each field resolves against its owning service** —
the gateway is only the composition layer.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

```java
@Controller                                   // spring-boot-starter-graphql
public class OrderGraphQLController {
    private final OrderClient orderClient;
    private final InventoryGrpcClient inventory;
    public OrderGraphQLController(OrderClient o, InventoryGrpcClient i) {
        this.orderClient = o; this.inventory = i;
    }

    @QueryMapping                              // REST call to order-service
    public Order order(@Argument String id) {
        return orderClient.get(id);
    }

    @SchemaMapping(typeName = "Order", field = "stock")   // resolved on demand
    public Integer stock(Order order) {                   // via gRPC
        return inventory.remaining(order.sku());
    }
}
```

```java
@GraphQLApi                                  // the gateway's schema (SmallRye GraphQL)
public class OrderApi {

    @Query                                   // REST call to order-service
    public Order order(String id) {
        return orderClient.get(id);
    }

    // @Source adds a 'stock' field to Order, fetched only when queried
    public Integer stock(@Source Order order) {           // via gRPC
        return inventory.reserveStockView(order.sku()).getRemaining();
    }
}
// SmallRye GraphQL exports the SDL to the registry automatically.
```

```csharp
// HotChocolate (MIT, by ChilliCream) — the dominant open-source GraphQL
// server for .NET, with a built-in DataLoader to batch away N+1.

public class Query                                   // the gateway's schema
{
    public async Task<Order?> GetOrder(string id,    // REST call to order-service
        [Service] IOrderClient orders) =>
        await orders.GetAsync(id);
}

[ExtendObjectType<Order>]                            // adds fields to Order
public class OrderExtensions
{
    // batched per request to kill N+1: one gRPC call for N orders
    public async Task<int> GetStock(
        [Parent] Order order,
        IInventoryStockDataLoader loader) =>
        await loader.LoadAsync(order.Sku);           // via gRPC, batched
}
```

```python
import strawberry                            # modern, code-first GraphQL for Python

@strawberry.type
class Order:
    id: str; sku: str; status: str

    @strawberry.field                        # resolved on demand, from another service
    async def stock(self) -> int:
        reply = await inventory_client.reserve_stock_view(self.sku)  # gRPC
        return reply.remaining

@strawberry.type
class Query:
    @strawberry.field
    async def order(self, id: str) -> Order:
        return await order_client.get(id)    # REST call to order-service

schema = strawberry.Schema(query=Query)      # SDL exported to the registry
```

```cpp
// schema.graphql is the contract — schemagen produces these types:
//   type Query { order(id: ID!): Order }
//   type Order { id: ID!  sku: String!  status: String!  stock: Int! }
class OrderResolver : public object::Order {
 public:
  OrderResolver(Order o, InventoryClient& inv) : o_(std::move(o)), inv_(inv) {}
  service::AwaitableScalar<std::string> getId()     const { co_return o_.id; }
  service::AwaitableScalar<std::string> getSku()    const { co_return o_.sku; }
  service::AwaitableScalar<std::string> getStatus() const { co_return o_.status; }
  service::AwaitableScalar<int> getStock() const {     // resolved on demand, via gRPC
    auto reply = co_await inv_.ReserveStock_view(o_.sku);
    co_return reply.remaining();
  }
 private:
  Order o_;
  InventoryClient& inv_;
};
```

### How the code works

The top-level `order` resolver does a REST call; the `stock` field resolver does a
gRPC call, and only runs *when the client asks for `stock`*. That on-demand
property is the point of GraphQL — unrequested fields cost nothing.

The trap to know is **N+1**: resolve `stock` naively for a list of 100 orders and
you fire 100 gRPC calls. Production gateways batch with a **DataLoader** — collect
the keys requested in one tick, make one batched back-end call. HotChocolate ships
one; Strawberry, the JVM servers, and the others have equivalents. When you write
a per-field resolver that calls another service, assume you will need batching.

## Three ways to compose — and where each belongs

The resolver above is one shape of a more general idea. There are three, and all
three push aggregation outward — toward the client as coupling needs loosen.

{% include excalidraw.html
   file="03-three-ways"
   alt="Three columns with tags: API Gateway (routing, auth, rate-limit; no business logic; Istio ingress) tagged thin edge; Backend-for-Frontend (one BFF per client type; client-specific shaping; owns aggregation) tagged client-shaped; and GraphQL federation (schema stitched across domains that own subgraphs; gateway plans query) tagged read-optimised. Aggregation moves toward the client as coupling needs loosen."
   caption="Figure 3.2 — Three places to compose: a thin API gateway, a client-shaped BFF, or a read-optimised GraphQL federation" %}

- **API gateway** — one composed schema for everyone. Simple, central, one contract;
  it routes, authenticates, and rate-limits at the edge (our Istio ingress) but holds
  no business logic.
- **Backend-for-frontend (BFF)** — a tailored aggregate per client type, so the
  web and mobile apps each get a surface shaped for them rather than a
  lowest-common-denominator one. The BFF owns the aggregation for its client.
- **GraphQL federation** — a distributed graph, where each service owns its slice
  of one logical schema and a gateway plans and stitches the query across subgraphs.

Pick by how much each client's needs diverge: a gateway when one shape serves everyone,
a BFF when clients differ enough to deserve their own surface, and federation when many
domains must present as one graph and reads dominate.

The anti-pattern to name explicitly is the opposite of all three:
**service-to-service call chains**, where `order` calls `inventory` calls
`pricing` calls… — synchronous, deeply coupled, and impossible to reason about. It
quietly rebuilds a distributed monolith. Composition belongs at the edge, not
buried in a chain of internal calls.

### Cross-check it yourself

The gateway is just HTTP. Send the query above with `curl` or Postman and request
`stock` in one call, then omit it in another — confirm the gateway only calls
`inventory` when `stock` is actually selected. Then request a *list* of orders with
`stock` and watch the back-end call count: without batching it climbs with the
list size; with a DataLoader it stays flat. That flat line is the N+1 fix working.

The code is in `examples/03-composition/`. The run script there builds and runs it;
its `README.md` covers what it does and how to drive it.

---
*Verification status: unverified — code transcribed and normalised from the source
decks, not yet run. The `examples/03-composition/` runner moves it to verified.*
