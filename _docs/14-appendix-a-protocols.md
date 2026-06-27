---
title: "Protocols in Depth"
marker: "A"
label: "Appendix A"
order: 14
part: "Deep-dive appendices"
description: "The deep dive behind 'pick the protocol' — REST, gRPC, and GraphQL compared on three axes: the mental model each imposes, how each handles fetching and round trips, and what actually travels on the wire."
duration: 18 minutes
---

This is the deep dive behind the protocol choice in **Communications**. The same
`place_order` intent takes three shapes, and the way to choose between them is to
compare the three on three axes: the **mental model** each imposes, how each
handles **fetching and round trips**, and what actually **travels on the wire**.

## Three paradigms, three mental models

Start with the mental model, because it drives everything else:

- **REST is resource-oriented** — nouns and HTTP verbs; you transfer
  representations of state.
- **gRPC is procedure-oriented** — you call typed methods; it's behaviour, not
  state, and the `.proto` is the contract.
- **GraphQL is graph-oriented** — one typed schema the client traverses, picking
  exactly the fields it wants.

{% include excalidraw.html
   file="14-three-paradigms"
   alt="Three columns for the same place_order intent. REST as resources: nouns plus HTTP verbs, POST to orders, GET an order by id, state transfer, server defines payload — resource-oriented. gRPC as procedures: typed method calls like Order.Place and Inventory.Reserve, behaviour not state, contract is the proto — RPC-oriented. GraphQL as a graph: one typed schema, the client picks fields and traverses relationships, contract is the SDL — query-oriented."
   caption="Figure A.1 — One intent, three mental models: resources, procedures, and a typed graph" %}

## The three axes, side by side

| Axis | REST | gRPC | GraphQL |
|---|---|---|---|
| **Mental model** | Resources: nouns + HTTP verbs, transfer state | Procedures: call typed methods, `.proto` is the contract | Typed graph: client traverses one schema, picks fields |
| **Fetching** | Several round trips, or a bespoke aggregate; fixed payloads over/under-fetch | One typed binary call | One tailored query; client names fields — no over/under-fetch |
| **Wire** | HTTP/1.1 or /2, JSON text, request/response, HTTP-cacheable, browser-native — *max reach* | HTTP/2 only, protobuf binary, uni- and bidirectional streaming, no HTTP cache, needs grpc-web in a browser | HTTP POST to one URL, JSON, request/response + subscriptions, caching is app-level |

The fetching axis is the one clients *feel*. With REST you often need several round
trips — order, then its items, then stock, then shipping — or you build a bespoke
aggregate endpoint and still get a fixed shape that over- or under-fetches. GraphQL
collapses that into one query whose fields the client chooses; gRPC is a single
typed binary call.

{% include excalidraw.html
   file="14-protocol-roundtrips"
   alt="REST requires the client to make several round trips to order, items, and stock or shipping, with fixed payloads; GraphQL collapses the same data need into a single query to the gateway where the client names the fields"
   caption="Figure A.2 — Many REST round trips versus one client-shaped GraphQL query" %}

The third axis is what literally travels between processes, and it is the one that
decides reach and caching. REST rides ordinary HTTP, so browsers and shared caches
handle it for free; gRPC trades that reach for HTTP/2 streaming and a compact binary
encoding; GraphQL keeps HTTP reach but moves caching up into the application.

{% include excalidraw.html
   file="14-the-wire"
   alt="Three columns comparing what travels on the wire. REST: transport HTTP/1.1 or 2, JSON text encoding, request and response interaction, cacheable via HTTP, browser-native reach. gRPC: HTTP/2 only, protobuf binary, unidirectional and bidirectional streaming, no HTTP caching, needs grpc-web in a browser. GraphQL: HTTP POST to one URL, JSON text, request and response plus subscriptions, app-level caching, browser-native reach."
   caption="Figure A.3 — What travels on the wire, per protocol: transport, encoding, streaming, caching, and reach" %}

## Choosing between them in practice

Said plainly:

- **Public, partner-facing, browser or third-party clients, caching matters →
  REST.**
- **Internal service-to-service, low latency, high call volume, streaming → gRPC.**
- **Aggregating many back-ends for varied clients that each want different fields →
  GraphQL at the gateway.**
- **A fact that many consumers react to → don't make it a call at all; emit an
  event.**

The closing point ties back to the whole book: forcing one protocol everywhere —
"we're a gRPC shop," "everything is GraphQL" — is *itself* an anti-pattern. Each
protocol earns its place on a specific axis; a healthy system uses all of them
where they fit.

## Common mistakes with each

Drawn from real review comments:

- **REST** — verbs in URLs (`/createOrder`), returning `200` with an error body,
  offset pagination that breaks under concurrent writes, and throwing away free
  HTTP caching.
- **gRPC** — calling it straight from a browser without grpc-web, or treating it as
  "REST with protobuf" and never touching its streaming superpower.
- **GraphQL** — the N+1 resolver explosion (fix with DataLoader batching, as in
  **Composition**), no query depth or complexity limits, and using it for simple
  single-resource fetches where REST would be plainer.

The throughline: each protocol is a tool with a shape. Match the shape to the
interaction, and most of these mistakes never arise.

---
*Verification status: conceptual appendix — no runnable code. The protocol choices
it argues are exercised in the Communications and Composition chapters.*
