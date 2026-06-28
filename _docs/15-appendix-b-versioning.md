---
title: "Versioning & Evolution"
marker: "B"
label: "Appendix B"
order: 15
part: "Deep-dive appendices"
description: "How to change an API without breaking everyone — the four ways to version REST, what counts as a breaking change in protobuf, GraphQL's evolve-don't-version stance, and the principles common to all three."
duration: 28 minutes
---

The question every team fights about: how do we change this without breaking
everyone? The answer differs sharply by protocol — but the principles underneath
rhyme, so we end with those.

## Four ways to version a REST API

Ordered coarse to fine:

- **URI path** (`/v2/orders`) — visible and trivial to route, but couples the
  version to the URL and arguably breaks REST's idea that a URL identifies a
  *resource*, not a representation. Common precisely because it's obvious.
- **Query parameter** (`?version=2`) — easy to default, but muddies caches (the
  same URL now returns different shapes).
- **Custom header** (`X-API-Version: 2`) — keeps URLs clean, but is invisible and
  easy to forget.
- **Media type** (`Accept: application/vnd.acme.order.v2+json`) — keeps the URL
  stable and versions the *representation*, which is the most RESTful choice.

{% include excalidraw.html
   file="15-rest-versioning"
   alt="Four ways to version a REST API, coarse to fine. URI path: a v2 orders path, visible and trivial to route, couples the version to the URL, most widely used. Query param: an orders path with a version query, easy to default, muddies caching keys, least recommended. Custom header: an X-API-Version header, keeps the URL clean but is invisible and easy to miss, needs discipline. Media type: an Accept header naming the v2 representation, content negotiation, the URL still identifies the resource, the RESTful way."
   caption="Figure B.1 — Four ways to version REST, from coarse URI paths to RESTful media-type negotiation" %}

```http
# Media-type versioning: the URL stays the same; the version lives in Accept
GET /orders/A-1001
Accept: application/vnd.acme.order.v2+json

HTTP/1.1 200 OK
Content-Type: application/vnd.acme.order.v2+json
```

## Which REST scheme to start with — and what it costs HATEOAS and security

For a new public or partner API, **start with URI-path versioning** (`/v1/orders`).
It is the least elegant of the four but the most operable: trivially routable,
visible in logs and dashboards, cacheable without surprises, and impossible for a
client to get wrong. Reach for **media-type versioning** when you specifically need
the URL to stay stable — which, as it happens, is exactly what HATEOAS needs.

**Impact on HATEOAS.** Hypermedia only works if a client can follow the links the
server hands it without guessing a version, so the scheme decides how the version
travels with those links:

- **Media-type** keeps every link clean (`/orders/A-1001/items`) and lets the
  version ride in `Accept` on each follow — the representation is versioned, the
  resource identity is not. This is the HATEOAS-friendly choice.
- **URI-path** works too, but every emitted link must already carry the version
  (`/v2/orders/A-1001/items`); a client that follows links stays pinned to one
  version, which is fine until you want it to move.
- **Query-param** and **custom-header** versioning quietly break link-following: the
  version lives outside the URL, so a naively followed link drops it.

**Impact on security.** Each live version is attack surface you must keep patched —
the real cost of versioning is *sprawl*, not the scheme. Two scheme-specific notes:
URI and query versions sit in URLs, so they surface in proxy logs, browser history,
and `Referer` headers (more fingerprintable, but also routable by a WAF), while header
and media-type versions hide there instead. And never let an older version skip a
check the newer one added — an auth scope, an input bound, a rate limit — or `/v1`
becomes the soft way in. Deprecate and retire on the lifecycle every protocol shares
(Figure B.4): a version you forgot to turn off is a version you forgot to patch.

## gRPC: field numbers are the contract

protobuf's rules are precise because the wire format is **positional** — the field
*number* is the contract, not the name or the order. Safe, wire-compatible changes:
add a field with a *new* number, add an rpc method, add an enum value, rename a
field (the number is what matters), mark fields deprecated, and **reserve** removed
tags. Breaking: changing a field's type, moving a field to a different number, or
reusing a retired tag.

{% include excalidraw.html
   file="15-grpc-breaking"
   alt="Two columns for protobuf changes. Safe and wire-compatible: add a field with a new number, add a new rpc method, add a value to an enum, rename a field since the number is unchanged, deprecate with the deprecated option, and widen with reserved for old tags. Breaking and rejected by the gate: change a field's number or type, reuse a removed field number, remove a field without reserving its tag, change an rpc between unary and streaming, rename or move a service or package, or change the request or response message type."
   caption="Figure B.2 — protobuf: safe wire-compatible changes versus breaking ones the registry rejects" %}

```proto
syntax = "proto3";

message Order {
  string id  = 1;
  string sku = 2;
  int32  qty = 3;

  reserved 4;                 // tag 4 once held 'notes' — never reuse it
  reserved "notes";

  string currency     = 5;    // SAFE: brand-new field, new tag number
  PaymentState state  = 6;    // SAFE: new field; old clients ignore it
}

enum PaymentState { PENDING = 0; PAID = 1; REFUNDED = 2; }   // tag 0 must exist

// BREAKING (don't): qty -> int64, or moving 'sku' to tag 7, or reusing tag 4
```

The `reserved` keyword is the whole discipline in one line: it tombstones a retired
tag so no future change can accidentally reuse it and silently corrupt old readers.

## GraphQL evolves, it doesn't version

GraphQL takes a different stance entirely: there is no `/v2`. One schema evolves
continuously. Add new fields and types (additive is always safe — existing queries
don't ask for the new field, so they're unaffected), mark superseded fields
`@deprecated` with a reason, watch usage drop, then retire.

{% include excalidraw.html
   file="15-graphql-evolution"
   alt="A four-step GraphQL evolution flow with no version number. Add: a new field or type, additive and safe, clients opt in. Deprecated: mark the old field with a reason and replacement, still served. Watch usage: field-level metrics show who still queries it and drive migration. Retire: at zero usage, remove the field — the only breaking step."
   caption="Figure B.3 — GraphQL evolves rather than versions: add, deprecate, watch usage, then retire" %}

```python
import strawberry

@strawberry.type
class Order:
    id: str
    total: float = strawberry.field(
        deprecation_reason="Use totalMinor (integer cents) instead.",
    )                                      # still served; shows in introspection
    total_minor: int                       # the replacement, added additively
```

Clients see the deprecation in introspection and in tooling (the Playground),
which is what lets you measure who's still on the old field before removing it.

## Versioning a Kafka API

An event stream is an API too — its **schema is the contract**, exactly like a
`.proto` or an OpenAPI document — and it evolves under the same pressure. The first
thing to separate is the two roles a Kafka message plays, which are easy to conflate:

- The **key** is *identity*: it picks the partition and so fixes ordering for a given
  entity. It is not a version slot — never encode `v2` into the key, or you scatter
  one entity's events across partitions and lose ordering.
- The **version** is *schema*: it lives in the schema registry (Apicurio, from the
  API-management chapter) as a numbered version with a **compatibility rule**, and
  travels on the wire as either the registry's schema id or an explicit
  `schema.version` header.

The default that keeps consumers working is **one topic with a BACKWARD-compatible,
evolving schema**: add fields, never renumber or repurpose them, and old consumers
ignore what they don't know while new consumers read the additions. Only a genuine
breaking change earns a new major — and then you run two topics (or two schema
majors) side by side, dual-write through the migration, and retire the old once
consumers have moved.

{% include excalidraw.html
   file="15-kafka-versioning"
   alt="A producer writes v2 events to one topic, order.placed, which holds an evolving schema. A schema registry over the topic enforces compatibility — v1 to v2 is add-only, BACKWARD. The topic delivers to two consumers: one built against v1 that ignores the added fields, and one built against v2 that uses them. The key is identity and partitioning, never the version; the version is the schema, carried in the registry or a header."
   caption="Figure B.5 — Versioning a Kafka API: one evolving topic, a registry-enforced compatibility rule, old and new consumers side by side" %}

On the wire, the cleanest portable signal is a `schema.version` header the producer
sets alongside the key; a consumer reads it and upcasts an old payload into the
current shape before handling it. The producer side looks like this — the key stays
identity, the version is metadata:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// key is identity (partition + ordering); version is metadata, not the key
ProducerRecord<String, Order> rec =
    new ProducerRecord<>("order.placed", order.id(), order);   // key = order id
rec.headers().add("schema.version", "2".getBytes());           // version header
kafka.send(rec);                                               // schema-aware serde
```

```java
@Inject @Channel("order.placed") Emitter<Order> emitter;       // Reactive Messaging

void publish(Order order) {
  emitter.send(KafkaRecord.of(order.id(), order)               // key = order id
      .withHeader("schema.version", "2".getBytes()));          // version header
}
```

```csharp
// MassTransit — key is the message identity; version travels as a header
public Task PublishAsync(Order o) =>
    bus.Publish(new OrderPlaced(o.Id, o.Sku, o.Quantity),
        ctx => ctx.Headers.Set("schema.version", "2"));        // version, not the key
```

```python
await producer.send_and_wait(
    "order.placed",
    key=order.id.encode(),                       # key = identity / partitioning
    value=serialize(order),                      # schema-aware serde
    headers=[("schema.version", b"2")])          # version as metadata
```

```cpp
// modern-cpp-kafka — key is identity, version is a header
kafka::Headers headers;
headers.emplace_back("schema.version", kafka::Header::Value("2", 1));
auto rec = kafka::clients::producer::ProducerRecord(
    "order.placed", kafka::Key(order.id),        // key = identity
    kafka::Value(serialize(order)), headers);    // value + version header
producer.send(rec, deliveryCb);
```

```go
// franz-go — key is identity; append the version as a header
rec := &kgo.Record{Topic: "order.placed", Key: []byte(order.ID), Value: serialize(order)}
rec.Headers = append(rec.Headers,
    kgo.RecordHeader{Key: "schema.version", Value: []byte("2")})   // version header
cl.Produce(ctx, rec, nil)
```

A consumer completes the picture: read the `schema.version` header, and for an older
version run a small upcaster (`v1 → v2`: default the new fields) before dispatching,
so the rest of the handler only ever sees the current shape. That is the same
tolerant-reader discipline the cross-cutting principles call for — strict in what you emit,
liberal in what you accept.

## Principles that cut across them all

The protocol-specific rules are all faces of four ideas:

- **Additive change is safe; removal and mutation break people** — so design to
  *add*.
- **Make compatibility mechanical** — the registry's `BACKWARD`/`FORWARD`/`FULL`
  rules checked in CI, never a reviewer remembering.
- **Never break silently** — deprecate with a reason, a replacement, and a sunset
  date, and measure who's still on the old version.
- **Run old and new side by side** until consumers have migrated, then retire.

{% include excalidraw.html
   file="15-deprecation-lifecycle"
   alt="A four-step lifecycle: ADD (additive, always safe), DEPRECATE (with reason, replacement, and sunset), MEASURE (who is still using it), then RETIRE after migration"
   caption="Figure B.4 — The same lifecycle for every protocol: add, deprecate, measure, retire" %}

### Cross-check it yourself

Prove the additive/breaking line with the registry from **API Registry**. Add an
optional field to a schema and confirm the `BACKWARD` check passes; change a field's
type or reuse a protobuf tag and confirm it fails with `409`. The mechanical check
catching the breaking change — instead of a reviewer's memory — is the principle
made real.

---
*Verification status: unverified — examples transcribed from the source decks; the
REST, gRPC, and GraphQL compatibility behaviour and the Kafka `schema.version` header
are exercised against the registry in the `examples/09-api-registry/` runner.*
