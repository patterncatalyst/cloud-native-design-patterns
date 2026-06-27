---
title: "L7 Routing & Traffic Management"
marker: "I"
label: "Appendix I"
order: 22
part: "Deep-dive appendices"
description: "Layer-7 routing as a four-layer stack of software — edge, gateway, mesh, and in-app — that decides on every HTTP and gRPC envelope, north/south and east/west, including rule-driven routing pushed inside the service."
duration: 32 minutes
---

This is the longest appendix in the book, large enough to be a talk of its own. The
reframe it argues for: L7 routing in 2026 is not an appliance in a rack — it is layered
software running inside Kubernetes that makes a decision on every HTTP and gRPC envelope
crossing the network, both north/south (clients into the system) and east/west (service
to service). The chapter walks what each layer can see and decide, shows real config for
the mesh, covers TLS, sticky sessions, traffic steering, and the latency budget, then
goes *inside* the service for rule-driven routing, and finally circles back to east/west,
where most of the decisions actually happen.

## L4 versus L7 — what each layer can decide on

A Layer-4 load balancer sees *connections*: IPs, ports, and the TCP 5-tuple. It can pick
a backend and hash-balance, but it cannot read URLs, headers, cookies, methods, or gRPC
metadata. A Layer-7 router sees the whole *conversation*: host, path, headers, cookies,
JWT claims, query parameters, the HTTP method, and the gRPC `service.method` pair. That
full envelope is the menu of inputs every routing decision in this appendix draws on. The
one nuance worth holding onto is TLS: an L4 balancer can route by SNI *without* terminating
TLS (cheap, opaque), while an L7 router typically terminates TLS so it can read everything
else (richer, slightly slower).

{% include excalidraw.html
   file="22-l4-vs-l7"
   alt="Two columns. L4 transport sees source and destination IP and port, TCP/UDP protocol, and TLS SNI hostname only; it can pick a backend by IP or port and load-balance by the 5-tuple, but cannot read URLs or headers or route per user or cookie. L7 application sees the host header, URL path, HTTP method, query params, request and response headers, cookies, JWT claims, and the gRPC service.method; it can route by path, header, or cookie, branch by header to a canary, version, or user, and inject or rewrite headers and rate-limit."
   caption="Figure I.1 — L4 sees connections (IPs, ports, the 5-tuple); L7 sees the whole HTTP/gRPC conversation and can route on any of it" %}

## The four-layer stack

L7 routing lives in four layers, and each is the right home for a *different kind* of
decision. A request is really a chain of independent L7 decisions across them.

{% include excalidraw.html
   file="22-l7-layers"
   alt="North/south: a client passes through edge/ingress (TLS, host/path), then the API gateway (auth, rate limit), then a mesh sidecar (mTLS, retries), then the service (in-app rules). East/west: service A and service B talk through mesh sidecars that add mTLS, outlier detection, and locality routing. Each layer makes a different kind of decision and emits a trace span."
   caption="Figure I.2 — L7 routing is a four-layer stack; the mesh applies the same routing to every internal call, not just at the edge" %}

The **edge / ingress** layer (HAProxy, Nginx, Envoy, Traefik) is where TLS terminates and
coarse host/path routing happens. The **API gateway** (Kong, Apigee, an Istio gateway,
Spring Cloud Gateway) handles product-level concerns — authentication, rate limiting,
transformation. The **service mesh** (Istio with Envoy sidecars, or Linkerd) governs
east/west traffic, giving every internal call mTLS, retries, outlier detection, and
locality-aware load balancing. And when a decision depends on business rules the platform
cannot know, routing pushes into the **app** itself. Each box can refuse, transform, or
branch the request, and each emits a trace span — so the journey from the Observability
chapter, viewed through the L7 lens, is observable end to end.

{% include excalidraw.html
   file="22-l7-journey"
   alt="A request's L7 journey across five components: Client (request), Edge LB (TLS, host and path), API Gateway (auth, rate-limit), Mesh sidecar (mTLS, retry, locality), and the Service (in-app routing). Each box can refuse, transform, or branch the request and emits a trace span for the next layer."
   caption="Figure I.3 — A request's journey: Client → Edge LB → API Gateway → Mesh sidecar → Service, each making its own L7 decision" %}

## Content-based routing

HAProxy and Nginx are the workhorses of the edge — mature, fast, predictable. HAProxy
reads the envelope with ACLs (`path_beg` for URL prefixes, `hdr` for headers,
`content-type` for the body kind) and `use_backend` dispatches on them; Nginx uses
`location` blocks and the `map` directive to turn a header value into an upstream pool.
Envoy is the modern sidecar choice because it speaks HTTP/2 and gRPC natively. But the
form most of this book uses is the mesh's: the same content-based primitives expressed as
Kubernetes CRDs that Istio compiles down to Envoy config across every sidecar.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: orders }
spec:
  hosts: [orders]
  http:
  - match:                                    # gRPC by service.method
    - uri: { prefix: /acme.orders.v1.OrderService/ }
    route: [{ destination: { host: orders, subset: v2 } }]
  - match:                                    # by header
    - headers: { x-internal: { exact: "1" } }
    route: [{ destination: { host: orders, subset: v2 } }]
  - match:                                    # by cookie
    - headers: { cookie: { regex: ".*canary=on.*" } }
    route: [{ destination: { host: orders, subset: v2 } }]
  - route: [{ destination: { host: orders, subset: v1 } }]   # default
```

Three match rules — by URI prefix (which is how you route on a gRPC `service.method`, since
gRPC paths look like `/package.Service/Method`), by header, and by cookie — each sending to
a different subset, with a default route at the bottom that is *critical*: without it,
unmatched requests have nowhere to go. The CRD lives in Git, gets reviewed like any other
change, and Istio reconfigures every sidecar within seconds.

## TLS termination

TLS at the edge comes in three modes. **Terminate-and-decrypt** is the common case — it
lets the router do everything L7. **Terminate-and-re-encrypt** is the most secure default
in a mesh, since mTLS inside is automatic. **Passthrough** is for traffic you must not see
(client mTLS for regulated flows): route by SNI only, decrypt nothing. cert-manager is the
standard answer for public certificates; SPIFFE-style identity and Envoy's SDS handle
service-to-service certs automatically inside the mesh. A handshake is milliseconds, so
amortise it with session resumption, TLS 1.3, and HTTP/2 multiplexing.

## Sticky sessions

There are three affinity modes, and the default is the one you want. **No affinity** sends
any request to any pod — even load, and client state lives elsewhere (Redis, the JWT, the
database). **Cookie-based** stickiness is the fallback when something stateful must stay on
one pod: the balancer sets a cookie and routes subsequent requests back to the same pod —
but that ties the session to one pod's lifetime, so a restart loses it. **IP-hash** needs
no cookie but is fragile behind NAT and mobile networks, where many users share an address
and load skews. The real cost is that stickiness fights elastic scaling, fast restarts, and
graceful shutdown — the entire cloud-native delivery model. Treat it as a deliberate choice
for a known constraint, never a default, and prefer to externalise state (Redis for session
data, JWT claims for identity, the backplane from the WebSockets appendix for fan-out) so
the balancer can return to no-affinity.

{% include excalidraw.html
   file="22-sticky-sessions"
   alt="Three affinity modes. No affinity: any pod gets any request, load is even, client state lives elsewhere — the preferred default. Cookie-based: the LB sets a session cookie so the client returns to the same pod, works behind any L7 LB, but ties the session to the pod's life. IP-hash: hash the client IP to a pod, no cookies needed, but NAT and mobile NAT break it and load can skew badly. The cost of stickiness is uneven load, painful pod restarts, broken scale-to-zero, and every restart re-balancing all sessions."
   caption="Figure I.4 — Affinity modes: no-affinity is the default; cookie and IP-hash stickiness both fight elastic scaling" %}

## Intelligent traffic steering

Six familiar release shapes are all the same L7 primitive with different inputs and weights:
canary (a small weighted slice to a new version), blue/green (two environments flipped
atomically), A/B (a stable cohort mapped to a variant by a user id), header-based
dark launches (route opted-in users by a header), geo/latency (EU users to EU pods), and
shadow/mirror (copy a percentage of real traffic to a new version without returning its
responses). The canonical one is the weighted canary: a `VirtualService` splits traffic by
weight, and a `DestinationRule` defines the subsets by pod label.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: orders }
spec:
  hosts: [orders]
  http:
  - route:
    - destination: { host: orders, subset: v1 }
      weight: 90                              # 90% on the stable version
    - destination: { host: orders, subset: v2 }
      weight: 10                              # 10% on the canary
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata: { name: orders }
spec:
  host: orders
  subsets:
  - name: v1
    labels: { version: v1 }
  - name: v2
    labels: { version: v2 }
```

Ramping the canary is changing the weights in Git — typically 10, 25, 50, 100 percent with
metric gates between steps — and a controller like Flagger or Argo Rollouts flips the weights
back in seconds if error rate or latency on `v2` crosses a threshold. Header-based steering
adds surgical precision: an upstream identity proxy sets a header for opted-in users and the
`VirtualService` routes *those* users to `v2`, on real production data with zero blast radius.
Payload modification is the cheap cousin — header inject/strip and URL rewrites are nearly
free because the router is already parsing the line and headers (this is how the W3C
`traceparent` header propagates, and how a gateway validates a JWT once and injects trusted
claims downstream). Body transformation is the expensive one: it forces the router to buffer
the full payload, killing streaming and risking memory under load. The rule of thumb: if you
can do it in the headers, do it in the headers.

{% include excalidraw.html
   file="22-traffic-steering"
   alt="Six release shapes built from the same L7 primitive. Canary: 90% v1, 10% v2, watch metrics and ramp. Blue/Green: all v1 to all v2, flip atomically with fast rollback. A/B test: a cohort maps to a variant, stable per user, measure. Header-based: an x-internal header routes to v2 for dark launches and betas. Geo/latency: EU users to EU pods for lower RTT and data residency. Shadow: copy traffic to v2 to test under load with no user impact."
   caption="Figure I.5 — Six familiar release shapes, all the same weighted/header L7 rule with different deploy-and-rollback discipline" %}

## Routing inside the app by business rules

There is a threshold where routing leaves the network and enters the service. If the decision
fits in a few YAML lines and depends only on the envelope, do it at the mesh. If it depends on
the *payload*, requires a decision table that domain experts edit, or involves many
intersecting conditions — think routing a healthcare message by patient class and encounter
type — push it into a rule engine inside the app, behind the mesh, not in a network CRD. The
discipline is "data, not code": the routing logic lives in an externalised ruleset the domain
experts own, separate from the dispatcher, and changes without redeploying the service.

{% include excalidraw.html
   file="22-business-rule-routing"
   alt="Routing by business rules inside the service. Inputs from REST, WebSocket, or Kafka reach a FastAPI/Starlette router that enriches the order with context, evaluates an externalised durable-rules ruleset (a Rete forward-chaining engine), and dynamically dispatches to a list of destinations. The router fans out to service A on a Kafka topic, service B over HTTP, and a DLQ/audit topic. The durable-rules engine sits beside the router and is consulted per request."
   caption="Figure I.6 — When routing depends on a business rule, a FastAPI front evaluates an externalised durable-rules ruleset and dispatches to services A, B, or a DLQ" %}

Each ecosystem composes this from its own rule engine — a Rete forward-chaining engine in
most cases — feeding a small dispatcher. First the **ruleset**, read as a set of "when … then …"
statements that set a list of destinations:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

```java
// orders.drl  —  edited by domain experts, not developers (Drools)
package com.acme.orders;
import com.acme.orders.OrderFact;

rule "High-value VIP orders go to the priority queue"
    when
        $o : OrderFact( amountCents > 50_000, customer.tier == "VIP" )
    then
        $o.setWhereTo("kafka:orders.priority,http:notify-vip");
end

rule "European orders go to the EU region"
    when
        $o : OrderFact( customer.region == "EU" )
    then
        $o.setWhereTo("kafka:orders.eu");
end

rule "Default route"
    salience -100                                  // last resort
    when   $o : OrderFact( whereTo == null )
    then   $o.setWhereTo("kafka:orders.default");
end
```

```java
// orders.drl  —  edited by domain experts, not developers (Drools)
package com.acme.orders;
import com.acme.orders.OrderFact;

rule "High-value VIP orders go to the priority queue"
    when
        $o : OrderFact( amountCents > 50_000, customer.tier == "VIP" )
    then
        $o.setWhereTo("kafka:orders.priority,http:notify-vip");
end

rule "European orders go to the EU region"
    when
        $o : OrderFact( customer.region == "EU" )
    then
        $o.setWhereTo("kafka:orders.eu");
end

rule "Default route"
    salience -100                                  // last resort
    when   $o : OrderFact( whereTo == null )
    then   $o.setWhereTo("kafka:orders.default");
end
```

```csharp
// NRules — same Rete engine, fluent C# rules (NRules.Fluent).
[Name("High-value VIP orders go to the priority queue")]
public class HighValueVipRule : Rule
{
    public override void Define()
    {
        OrderFact order = default!;            // declare the fact binding
        When()
            .Match<OrderFact>(() => order,
                f => f.AmountCents > 50_000,
                f => f.Customer.Tier == "VIP");
        Then()
            .Do(ctx => order.WhereTo = "kafka:orders.priority,http:notify-vip");
    }
}

[Name("European orders go to the EU region")]
public class EuropeanOrderRule : Rule
{
    public override void Define()
    {
        OrderFact order = default!;
        When().Match<OrderFact>(() => order, f => f.Customer.Region == "EU");
        Then().Do(ctx => order.WhereTo = "kafka:orders.eu");
    }
}

[Name("Default route")] [Priority(-100)]    // salience equivalent — fires last
public class DefaultRouteRule : Rule
{
    public override void Define()
    {
        OrderFact order = default!;
        When().Match<OrderFact>(() => order, f => f.WhereTo == null);
        Then().Do(ctx => order.WhereTo = "kafka:orders.default");
    }
}
```

```python
# orders_rules.py  —  edited by domain experts, not developers (durable-rules)
from durable.lang import ruleset, when_all, m

with ruleset("orders"):

    @when_all((m.amount_cents > 50_000) & (m.tier == "VIP"))
    def vip(c):                              # high-value VIP orders
        c.m.where_to = ["kafka:orders.priority", "http:notify-vip"]

    @when_all(m.region == "EU")
    def eu(c):                               # European orders → EU region
        c.m.where_to = ["kafka:orders.eu"]

    @when_all(+m.order_id)                   # catch-all (lowest priority)
    def default(c):
        if not getattr(c.m, "where_to", None):
            c.m.where_to = ["kafka:orders.default"]
```

```lua
-- orders_rules.lua  —  edited by domain experts, not developers (sol2 + Lua)
-- Each rule appends destinations; the dispatcher fans out.
function route(order, ctx)
  local dests = {}

  -- high-value VIP orders
  if order.amount_cents > 50000 and ctx.tier == "VIP" then
    table.insert(dests, "kafka:orders.priority")
    table.insert(dests, "http:notify-vip")
  end

  -- European orders -> EU region
  if order.region == "EU" then
    table.insert(dests, "kafka:orders.eu")
  end

  -- catch-all
  if #dests == 0 then
    table.insert(dests, "kafka:orders.default")
  end
  return dests
end
```

Then the **dispatcher**: enrich the input with any context the rules need, evaluate the
ruleset, and fan out to each destination over the right transport. The `kafka:` / `http:`
prefix on each destination is a tiny convention that lets one ruleset drive multiple
transports.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

```java
// Camel route in Spring Boot, calling Drools (camel-spring-boot + drools starters)
@Component
public class OrderRoutes extends RouteBuilder {
    private final RulesEvaluator rules;            // wraps a Drools KieSession
    public OrderRoutes(RulesEvaluator rules) { this.rules = rules; }

    @Override public void configure() {
        from("kafka:orders.inbound")
            .enrich("direct:lookupCustomer", aggregateStrategy)  // context
            .process(rules::evaluate)                // sets "whereTo" header
            .log("routing ${header.whereTo}")
            .routingSlip(header("whereTo"))          // dynamic dispatch
            .end();

        from("direct:lookupCustomer")
            .to("http:customer-svc/lookup")          // enrich w/ HTTP call
            .unmarshal().json();
    }
}
```

```java
// Camel route in Quarkus, calling Drools (camel-quarkus + drools-quarkus)
@ApplicationScoped
public class OrderRoutes extends RouteBuilder {
    @Inject RulesEvaluator rules;                    // wraps a Drools KieSession

    @Override public void configure() {
        from("kafka:orders.inbound")
            .enrich("direct:lookupCustomer", aggregateStrategy)  // context
            .process(rules::evaluate)                // sets "whereTo" header
            .log("routing ${header.whereTo}")
            .routingSlip(header("whereTo"))          // dynamic dispatch
            .end();

        from("direct:lookupCustomer")
            .to("http:customer-svc/lookup")          // enrich w/ HTTP call
            .unmarshal().json();
    }
}
```

```csharp
// MassTransit RoutingSlip + NRules — consumer enriches, evaluates, dispatches.
public record OrderFact(string OrderId, long AmountCents, Customer Customer)
{
    public string? WhereTo { get; set; }                   // rules write this
}

public class OrderRouter(
    HttpClient lookup,                                     // customer-svc
    ISession rulesSession) : IConsumer<OrderInbound>       // NRules session
{
    public async Task Consume(ConsumeContext<OrderInbound> ctx)
    {
        // 1) enrich — fetch the customer for the decision
        var customer = await lookup.GetFromJsonAsync<Customer>(
            $"http://customer-svc/lookup/{ctx.Message.OrderId}")
            ?? throw new NotFoundException();
        var fact = new OrderFact(ctx.Message.OrderId,
                                 ctx.Message.AmountCents, customer);

        // 2) evaluate — NRules fires matching rules, sets fact.WhereTo
        rulesSession.Insert(fact);
        rulesSession.Fire();

        // 3) dispatch — build a RoutingSlip from WhereTo and execute
        var builder = new RoutingSlipBuilder(NewId.NextGuid());
        foreach (var dest in (fact.WhereTo ?? "queue:orders.default").Split(','))
            builder.AddActivity("Forward",
                new Uri($"queue:forward-to_{Sanitize(dest)}"),
                new { Destination = dest });
        await ctx.Execute(builder.Build());                 // MassTransit dispatches
    }
}
```

```python
from durable.lang import post
from fastapi import FastAPI, Depends
from aiokafka import AIOKafkaProducer
import httpx, json
import orders_rules                          # registers the ruleset

app = FastAPI()

@app.post("/orders/route")
async def route(order: dict,
                producer: AIOKafkaProducer = Depends(kafka_producer),
                http: httpx.AsyncClient    = Depends(http_client)):
    ctx  = await enrich(order)               # gather context (DB / HTTP)
    fact = post("orders", order | ctx)       # evaluate the ruleset
    for dest in fact["where_to"]:            # dispatch per destination
        proto, target = dest.split(":", 1)
        if proto == "kafka":
            await producer.send(target, json.dumps(order).encode())
        elif proto == "http":
            await http.post(target, json=order)
    return {"routed_to": fact["where_to"]}
```

```cpp
{% raw %}// dispatcher.cpp — Drogon controller + sol2 + modern-cpp-kafka
#include <sol/sol.hpp>
#include <drogon/HttpController.h>
class Router {                                // process-scoped
  sol::state lua_;
 public:
  Router() {
    lua_.open_libraries(sol::lib::base, sol::lib::table);
    lua_.script_file("/etc/orders/rules.lua");  // load DSL
  }
  std::vector<std::string> evaluate(const Order& o, const Ctx& c) {
    return lua_["route"](o, c);              // call route()
  }
} router;

Task<> Orders::route(HttpRequestPtr req, auto cb) {
  auto order = parse<OrderIn>(req);
  auto ctx   = co_await enrich(order);        // DB / HTTP
  auto dests = router.evaluate(order, ctx);   // rules
  for (const auto& dest : dests) {            // fan-out
    auto [proto, target] = split(dest, ':');
    if (proto == "kafka") producer_.send(target, to_json(order));
    else if (proto == "http") co_await http_.post(target, order);
  }
  cb(json_response({{"routed_to", dests}}));
}{% endraw %}
```

The shapes converge: a forward-chaining rule engine (Drools, NRules, durable-rules, or Lua)
evaluates the enriched fact and produces a `where_to` list, and a small dispatcher fans the
input out to each destination. The pattern is the classic content-based router from the
enterprise-integration literature — the value is that the *decision* is data a domain expert
edits, not code a developer redeploys.

## The cost of L7 hops

Every L7 capability costs time, and it is a budget you spend before your service even runs.
TLS termination is sub-2ms, path/header routing sub-1ms, JWT validation a few ms, a WAF a few
more, each mesh sidecar about a millisecond, a rate-limit Redis lookup a couple of ms. Body
inspection is the outlier at roughly 5–50ms depending on size. The working heuristic is to
stay under about 10ms of total L7 on hot paths — and with four layers (edge, gateway, sidecar
out, sidecar in) that means every layer must earn its place. The common pitfalls follow from
this: too many hops nobody measured until p99 spiked; expensive regex matches; sticky sessions
fighting the platform; body inspection blowing the budget; per-request auth lookups cascading
under load; and timeout misalignment, which is the gateway-to-mesh-to-service version of the
retry storm from the Error Handling appendix. The fix is identical — bound retries, align
timeouts top-down, and give the deepest layer the strictest budget.

{% include excalidraw.html
   file="22-hop-cost"
   alt="A latency budget per L7 stage: TLS termination 0.5 to 2 ms, L7 path/header routing under 1 ms, Auth/JWT validation 1 to 5 ms, WAF inspection 2 to 5 ms, mesh sidecar 0.5 to 2 ms per hop, rate-limit Redis lookup 1 to 3 ms, body/payload inspection 5 to 50 ms, and in-app rule eval under 1 ms cached. The rule of thumb is to stay under about 10 ms of total L7 on hot paths, so every hop must earn its place."
   caption="Figure I.7 — Each L7 stage adds latency; stay under ~10 ms of total L7 on hot paths, so every hop must earn its place" %}

## East / west — L7 between services

Most L7 decisions in a microservices system are not at the edge; they happen east/west, every
time one service calls another. The mesh's sidecar pair handles that traffic with no app code:
mTLS (encryption *and* identity), HTTP/2 multiplexing, native gRPC, retries with backoff and
jitter, outlier detection that ejects misbehaving pods, locality-aware load balancing that
prefers same-zone pods, and per-call traces. The same Istio CRDs as the edge, pointed at an
internal host:

{% include excalidraw.html
   file="22-east-west"
   alt="East/west L7 between services. Service A talks to service B through a sidecar pair (Envoy or Linkerd) over mTLS, HTTP/2, and gRPC. What the sidecars do per call with no app code: mTLS, retries with backoff and jitter, outlier detection, locality-aware load balancing, header-based routing and canary weights, rich traces and per-call metrics, circuit breakers, and rate limits."
   caption="Figure I.8 — East/west L7: a sidecar pair gives every service-to-service call mTLS, retries, locality, and traces with no app code" %}

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata: { name: payments }
spec:
  host: payments.acme.svc.cluster.local
  trafficPolicy:
    connectionPool:
      http: { http2MaxRequests: 1000, maxRequestsPerConnection: 10 }
    outlierDetection:                              # eject bad pods
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
    loadBalancer:
      localityLbSetting: { enabled: true }         # prefer same zone
  subsets:
  - { name: v1, labels: { version: v1 } }
  - { name: v2, labels: { version: v2 } }
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: payments }
spec:
  hosts: [payments.acme.svc.cluster.local]            # internal DNS — east/west
  http:
  - route:
    - { destination: { host: payments, subset: v1 }, weight: 95 }
    - { destination: { host: payments, subset: v2 }, weight: 5 }
```

That last block is a canary release of a backend service no external client knows exists —
something you simply cannot do through an edge load balancer. gRPC east/west has a few sharp
edges worth naming: route on the gRPC URI prefix for per-method canaries; prefer least-request
load balancing over round-robin, because gRPC connections are long-lived and round-robining
connections (rather than requests) can starve backends; be careful retrying streaming RPCs,
since replaying a half-finished stream redoes half the work; and remember gRPC returns its real
status in HTTP trailers, so outlier detection must read the trailer — a `200` with a non-OK
gRPC status is a failure, and a naive check would call a failing service healthy.

## When to use which layer

Each layer has a job it is good at, and pushing work to the wrong one is where complexity
comes from. Edge/ingress for the things every client crosses (TLS, host/path). API gateway for
product-shaped policy (auth, rate limits, plans). Mesh for east/west and everything internal.
In-app for business rules. The antipattern this prevents is the slow growth of baroque
`VirtualService` configs that encode rules domain experts need to maintain — if it is a
business rule, it belongs in a rule engine inside a service, not a network CRD. And the
organisational failure to avoid is the cluster that ends up running three ingress controllers
because three teams each picked one: choose one ingress, one gateway, one mesh, manage routing
through GitOps, watch certificate rotation, and load-test the failure paths.

### Cross-check it yourself

Prove a routing decision twice — once at the mesh, once in the app. For the mesh: apply the
canary `VirtualService`/`DestinationRule`, drive a few hundred requests with `hey`, and confirm
the split lands near the configured weight — roughly 10% of responses carrying the `v2` build
marker (a response header or version field), the rest `v1`. Bump the weight in Git, re-apply,
and watch the ratio move within seconds. Then flip a request's `x-internal` header and confirm
it goes to `v2` every time regardless of weight — header match beats weight. For the in-app
router: post one VIP order over the configured threshold and one ordinary order, and confirm
from the broker that the VIP order landed on `orders.priority` (and triggered the `notify-vip`
HTTP call) while the ordinary one fell through to `orders.default` — then change only the
ruleset, not the dispatcher, and confirm the routing changes without a redeploy. Weights that
track the config and a ruleset that can move routing without a code change are the two halves of
this appendix actually working.

---
*Verification status: unverified — config and code transcribed and normalised from the source
decks, not yet run. Highest-risk things to confirm on a real cluster: that the Istio CRD
`apiVersion` (`networking.istio.io/v1`) matches the installed Istio version, the
`localityLbSetting`/`outlierDetection` fields validate against that version's schema, the
gRPC-trailer outlier-detection behaviour, and the per-ecosystem rule wiring — Drools
`KieSession`, NRules `ISession`, durable-rules `post`, and the sol2 `route()` call signature —
against current library versions. The `examples/22-l7-routing/` runner moves it to verified.*
