---
title: "API Management"
order: 8
part: "The operational platform"
description: "API management as four cooperating planes rather than one gateway product — runtime, contract, discovery, and signal — and versioning and evolution as a managed lifecycle, not an afterthought."
duration: 15 minutes
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
four becomes exactly the god-service the workflows chapter warned about — runtime
policy, contract storage, discovery UX, and telemetry pipelines have genuinely
different owners and release cadences, and fusing them into one box recreates the
monolith at the edge. Distinct planes have distinct owners and evolve independently;
this chapter's job is largely to insist they stay distinct.

### Mapping the planes to concrete tools

In this stack each plane maps to a specific tool with a specific owner:

| Plane | Tool | Owner | What it enforces |
|---|---|---|---|
| **Runtime** | Istio + Envoy | Platform team | Traffic routing, mTLS, rate limits, retries |
| **Contract** | Apicurio Registry | API team / CI pipeline | Schema compatibility (`BACKWARD`, `FORWARD`, `FULL`) |
| **Discovery** | OpenMetadata | Data governance | Searchable catalog, lineage, ownership, PII tags |
| **Signal** | LGTM (Loki, Grafana, Tempo, Mimir) | SRE / platform team | Logs, traces, metrics, dashboards, alerts |

The separation is enforced by ownership, not by good intentions — the platform team
cannot break the contract plane because they don't own the registry; the API team
cannot change the retry policy because they don't own the mesh config.

## The runtime plane in practice: rate limiting

The cross-check section tells you to confirm the gateway returns `429` with a
`Retry-After` — here is the configuration that makes it happen. The rate limit is a
runtime-plane concern: it lives in the mesh, not in application code, and it applies
uniformly to every caller.

```yaml
# Istio EnvoyFilter — local rate limit on order-service
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata: { name: order-ratelimit, namespace: istio-system }
spec:
  workloadSelector:
    labels: { app: order-service }
  configPatches:
    - applyTo: HTTP_FILTER
      match:
        context: SIDECAR_INBOUND
        listener:
          filterChain:
            filter: { name: envoy.filters.network.http_connection_manager }
      patch:
        operation: INSERT_BEFORE
        value:
          name: envoy.filters.http.local_ratelimit
          typed_config:
            "@type": type.googleapis.com/udpa/type/v1/TypedStruct
            type_url: type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
            value:
              stat_prefix: http_local_rate_limiter
              token_bucket:
                max_tokens: 100            # burst capacity
                tokens_per_fill: 50        # 50 requests per second
                fill_interval: 1s
              response_headers_to_add:
                - header:
                    key: Retry-After
                    value: "1"             # tell the client when to try again
```

The `Retry-After: 1` header is what makes the 429 useful rather than merely
hostile — the client knows *when* to retry, not just that it was rejected. This is
policy, not code; changing the rate or the burst is a config commit, not a redeploy.

## Versioning and evolution are part of management

Versioning is a management concern, not an afterthought bolted on when something
breaks. The core discipline is to **evolve additively**: add optional fields and new
endpoints; never repurpose a field's meaning and never silently remove one. This
works because well-behaved consumers ignore fields they do not recognise, so a new
optional field is invisible to old clients while available to new ones. A consumer
written against last year's contract should still work against this year's service
without a single change.

When you genuinely must break compatibility, you don't mutate the existing
contract — you stand up a new major version beside the old one. Carry the major in
the path (`/v2`) or in the media type, run both side by side, publish a **sunset
date**, and migrate consumers off before retiring the old one. The mechanics —
four ways to version, additive evolution, deprecation headers — are the subject of
**Appendix B**.

What makes this more than good intentions is that the registry enforces it
**mechanically**. Its compatibility rules — `BACKWARD`, `FORWARD`, `FULL` — are
checked at publish time, so a change that would break existing consumers is rejected
before it ships. Every contract therefore moves through one managed lifecycle:

{% include excalidraw.html
   file="08-contract-lifecycle"
   alt="A six-stage horizontal lifecycle: design, register, publish, consume, deprecate, retire. Each stage flows into the next; the last two transitions (deprecate, retire) are highlighted as the wind-down."
   caption="Figure 8.2 — One managed contract lifecycle; each arrow is an owned transition, not an accident" %}

Each arrow is a managed transition with an owner, not an accident. A contract is
*designed* against the domain, *registered* in the schema registry, *published* once
CI's compatibility check passes, *consumed* by services that code against it, and —
when a successor exists — *deprecated* with headers and a sunset date before it is
finally *retired*. Skipping a step is where breakage comes from: publishing without
the registry check ships an incompatible schema, and retiring without a deprecation
window strands consumers who never got the signal to move. The registry and the
metadata catalog — the next two chapters — are what make the middle of this lifecycle
real and observable.

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
