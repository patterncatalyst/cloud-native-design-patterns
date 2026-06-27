---
title: "Versioning & Evolution"
marker: "B"
label: "Appendix B"
order: 15
part: "Deep-dive appendices"
description: "How to change an API without breaking everyone — the four ways to version REST, what counts as a breaking change in protobuf, GraphQL's evolve-don't-version stance, and the principles common to all three."
duration: 20 minutes
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

## Principles that cut across all three

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
compatibility behaviour is exercised against the registry in the
`examples/09-api-registry/` runner.*
