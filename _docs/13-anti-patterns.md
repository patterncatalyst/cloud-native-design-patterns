---
title: "Anti-Patterns"
order: 13
part: "Security & anti-patterns"
description: "Nearly every cloud-native failure is coupling sneaking back in — the recurring anti-patterns that reintroduce it, the five heuristics that catch them in review, and the whole book compressed to five lines."
duration: 16 minutes
---

Here is the most useful framing in the book, and the one to remember for code
review: **nearly every cloud-native failure is coupling sneaking back in.** You did
the work to separate things into services with contracts and events. Entropy and
deadlines pull them quietly back together. This closing chapter names the specific
ways that happens and gives you heuristics to catch them.

## How cloud-native API systems go wrong

Each of these is a callback to an earlier chapter — and each one reintroduces
exactly the coupling the architecture worked to remove:

{% include excalidraw.html
   file="13-antipatterns-grid"
   alt="A grid of nine anti-patterns, each re-coupling what the architecture worked to separate: distributed monolith (services deploy together), shared database (two services one schema), chatty N+1 APIs (a screen makes 40 calls), sync call chains (A to B to C to D, availability multiplies down), no contract or registry (breaking changes ship silently), smart pipes and dumb endpoints (business logic creeps into the gateway), missing observability (debugging by guesswork), retry storms with no backoff (retries amplify an incident into an outage), and leaky internal models (DB rows exposed as the public API)."
   caption="Figure 13.1 — The recurring anti-patterns; each one re-couples what the platform worked to separate" %}

- **Distributed monolith** — services that must be deployed together. You paid all
  the cost of distribution and kept all the coupling.
- **Shared database** — two services reading and writing one table. The table is
  now an un-versioned, un-owned contract between them.
- **Chatty call chains** — `order` calls `inventory` calls `pricing` calls…, deep
  synchronous hops that couple availability and latency end to end.
- **No contract / leaky internal models** — exposing database rows as the public
  API, so every internal change is a breaking change.
- **Smart pipes, dumb endpoints** — business logic creeping into the gateway or an
  ESB, so the routing layer becomes the new monolith and no single team can change a
  flow safely.
- **Missing observability** — debugging distributed systems by guesswork.
- **Retry storms** — retries with no backoff or bound, turning a blip into an
  outage.

If you keep one diagram for review, keep the pairing below.

{% include excalidraw.html
   file="13-antipattern-heuristics"
   alt="Five anti-patterns on the left — distributed monolith, shared database, chatty call chains, no contract or leaky models, missing observability and retry storms — each paired with the review heuristic on the right that catches it"
   caption="Figure 13.2 — Every anti-pattern is coupling returning; every heuristic is a test you can apply in a PR" %}

## The heuristics that keep you out of them

Five tests to apply in design and code review — paste them into a PR template:

1. **If two services must deploy together, they are one service** — merge them or
   fix the contract.
2. **One writer per dataset.** Everyone else reads through the API or subscribes to
   its events. No shared tables.
3. **Push aggregation to a gateway or BFF**, and forbid synchronous call chains
   deeper than one hop.
4. **No contract in the registry, no merge** — and every retry has a timeout and a
   bound.
5. **If you can't trace it, you can't run it.** Observability is a launch
   requirement, not a follow-up.

## The whole book, in five lines

If you remember nothing else:

1. Cloud-native is a set of **properties**; the platform exists to make them the
   default.
2. **Match each interaction to its style** — REST, gRPC, GraphQL, or async — and
   compose at the edge.
3. **Own your data**; share it as contracts and facts, never as shared tables.
4. Make the contract a **governed artifact**: a registry to enforce it, metadata to
   find it, observability to watch it.
5. Watch for **coupling sneaking back in** — every anti-pattern above is a face of
   that one failure.

## The shoulders this stands on

The slides and these references are enough to actually build the system, not just
talk about it:

- Sam Newman, *Building Microservices* (2nd ed.) — service boundaries and
  integration.
- Martin Kleppmann & Chris Riccomini, *Designing Data-Intensive Applications* (2nd
  ed.) — the data and consistency foundations behind the outbox and saga.
- Adam Bellemare, *Building Event-Driven Microservices* — the event backbone.
- Cornelia Davis, *Cloud Native Patterns*; Unmesh Joshi, *Patterns of Distributed
  Systems*.
- The API-design trio for contracts and versioning depth: JJ Geewax, *API Design
  Patterns*; Olaf Zimmermann et al., *Patterns for API Design*; Mike Amundsen,
  *RESTful Web APIs* — plus the relevant IETF RFCs and drafts.

That closes the thirteen core sections. The appendices that follow go deeper on the
questions that always come up — protocols, versioning, WebSockets, sagas, errors,
DDD, coupling, shutdown, routing, decomposition, caching, and failure modes — and
can be read on demand.

---
*Verification status: conceptual chapter — no runnable code. Its heuristics are the
review-time application of the patterns proven in the preceding chapters.*
