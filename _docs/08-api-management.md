---
title: "API Management"
order: 8
part: "The operational platform"
description: "API management as four cooperating planes rather than one gateway product — runtime, contract, discovery, and signal — and versioning and evolution as a managed lifecycle, not an afterthought."
duration: 12 minutes
---

"API management" is sold as a product — one box that does gateways, keys, docs,
and analytics. The cloud-native version is different: it is **four cooperating
planes with distinct owners**, each of which is a section of this book. Seeing
them as separate responsibilities is what keeps any one of them from becoming a
monolith.

## Four cooperating planes

{% include excalidraw.html
   file="08-four-planes"
   alt="Four planes side by side: the runtime plane (gateway and mesh), the contract plane (registry, section 9), the discovery plane (metadata, section 10), and the signal plane (observability, section 11)"
   caption="Figure 8.1 — Four planes, four owners — each a section of the platform" %}

- **Runtime plane** — the gateway and the Istio mesh. Traffic, authentication,
  rate limiting, and resilience happen here, on the wire, as configuration. This
  is where a `429 Too Many Requests` with a `Retry-After` comes from, and it is
  policy, not application code.
- **Contract plane** — the registry (**09 · API Registry**). Every REST, gRPC,
  and event schema, versioned and gated in CI.
- **Discovery plane** — the catalog and metadata (**10 · API Metadata**). How a
  human finds an API and decides whether to trust it.
- **Signal plane** — observability (**11 · Observability**). What is actually
  happening to the APIs in production.

The point is the separation. A single "API gateway product" that tries to own all
four becomes exactly the god-service the previous chapter warned about. Distinct
planes have distinct owners and evolve independently.

## Versioning and evolution are part of management

Versioning is a management concern, not an afterthought bolted on when something
breaks. The core discipline is to **evolve additively**: add optional fields and
new endpoints; never repurpose a field's meaning and never silently remove one. A
consumer written against last year's contract should still work.

When you genuinely must break compatibility, you don't mutate the existing
contract — you stand up a new major version beside the old one. Carry the major in
the path (`/v2`) or in the media type, run both side by side, publish a **sunset
date**, and migrate consumers off before retiring the old one. The mechanics —
four ways to version, additive evolution, deprecation headers — are the subject of
**15 · Appendix B**.

What makes this more than good intentions is that the registry enforces it
**mechanically**. Its compatibility rules — `BACKWARD`, `FORWARD`, `FULL` — are
checked at publish time, so a change that would break existing consumers is
rejected before it ships. Every contract therefore moves through one lifecycle:

> design → register → publish → consume → deprecate → retire

Each arrow is a managed transition with an owner, not an accident. The next two
chapters are the registry and the metadata catalog that make the middle of that
lifecycle real.

### Cross-check it yourself

The runtime plane is observable from the outside. Drive `order-service` past its
limit with `hey` and confirm the gateway returns `429` with a `Retry-After` rather
than letting the load through — that response is the runtime plane doing its job as
configuration. The contract-plane enforcement is demonstrated in the registry
chapter, where a breaking change is rejected at publish time.

---
*Verification status: conceptual chapter — no per-language runnable code. The
runtime-plane and contract-plane behaviours it describes are exercised in the
security, registry, and Appendix B chapters.*
