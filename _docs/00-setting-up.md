---
title: "Setting up · Patterns in the age of AI"
order: 0
part: "Setting up"
description: "Why a shared vocabulary of patterns matters more now that an AI writes the first draft, and the canonical five-service system we design against for the rest of the book."
duration: 10 minutes
---

AI coding tools turn intent into code at a rate that wasn't possible before. Ask
one, in a sentence, for a microservices decomposition, a saga, a cache layer, a
strangler-fig wrapper, or a CQRS write side, and you get back something plausible
enough to compile, deploy, and run. The bottleneck has moved. It is no longer
typing; it is *evaluation* — telling a good answer from a confident, plausible,
wrong one.

That is what this book is about. The patterns here are not nostalgic
computer-science trivia. They are the literacy that lets you **direct** AI tooling
instead of being directed by it: ask for the right thing, recognise what comes
back, and judge why it is or isn't fit for what you're building. AI is the
amplifier; the patterns decide which direction it amplifies.

## Four maxims to carry throughout

Every concrete choice in this book is a deliberate exercise in four ideas. Keep
them in view:

- **The least-worst decision.** Every architecture choice is a set of trades —
  latency for throughput, consistency for availability, simplicity for
  flexibility. The job is not to find the option with no downside; it is to make
  the trades visible and deliberate.
- **Risk management.** You manage the *distribution* of failures, not their
  existence. Failure doesn't go away; you choose where it lands and how it's
  contained.
- **No free lunch.** Every pattern — a cache, a saga, eventing, decomposition —
  has a cost: a stale-read window, a compensation path, a coordination tax,
  operational complexity. The question is whether you are buying the right thing
  for what you are paying.
- **No problem cannot be made worse.** A confidently-wrong intervention amplifies
  the original pain. AI tooling makes confident interventions cheap and easy,
  which is exactly why this maxim earns its place.

## Three layers of patterns literacy

"Pattern" spans three layers, and they build on each other. **Design patterns**
are code-level vocabulary — the Gang of Four: factory, strategy, observer,
repository. **Architecture patterns** describe how an application fits together —
hexagonal, microservices, BFF, federation, event-driven. **System design
patterns** — the focus of this book — span services, data, and runtime: sagas,
the outbox, CQRS, caching, the strangler fig, back-pressure, the bulkhead, L7
routing.

{% include excalidraw.html
   file="00-patterns-literacy"
   alt="Three stacked layers: design patterns (Gang of Four) at the bottom, architecture patterns in the middle, and system design patterns — the focus of this book — on top, with arrows showing each lower layer informing the next"
   caption="Figure 0.1 — Each lower layer informs the one above it" %}

The layers are not independent. You can't reason about a saga (system layer)
without knowing what a state machine and a compensation are (architecture and
design layers); you can't reason about content-based routing without
understanding the strategy pattern. The vocabulary compounds, which is precisely
what lets you ask an AI for the right thing and judge what it returns.

## The running example

Every concern in this book is designed against one small system — the same
example, re-examined from each angle. Anchor on it now; we return to this picture
many times.

{% include excalidraw.html
   file="00-running-example"
   alt="A client calls order-service over REST; order-service calls inventory, payment, and shipping over gRPC and emits an order.placed event to Kafka; a notification service consumes that event; a graphql-gateway composes reads across the internal services"
   caption="Figure 0.2 — Five services and a gateway, each exposing only the protocols that fit its role" %}

The point of the picture is that **each service exposes only the protocols that
fit its role**, not a uniform surface:

- **order-service** owns the order lifecycle and exposes REST at the edge — the
  one public, client-facing surface.
- **inventory**, **payment**, and **shipping** are internal. They are reached by
  gRPC for low-latency service-to-service calls, and they contribute fields to
  composed GraphQL reads.
- **notification-service** is Kafka-only. It never exposes an API; it consumes
  the `order.placed` event and reacts.
- **graphql-gateway** composes reads across the internal services so a client
  asks one question and the gateway fans out.

When a later chapter shows the transactional outbox, or content-based routing, or
a saga, it is wiring up *these* services. Keeping one concrete system in mind is
what stops the patterns from staying abstract.

## How the rest of the book is ordered

The order is deliberate: principles first, because they justify every later
choice; then the synchronous surface (communications, composition); then data
ownership; then the asynchronous backbone (events, streams); then the operational
concerns (workflows and the platform planes); and finally anti-patterns as a
reflective close. The deep-dive appendices at the end go deeper on the questions
that always come up — protocols, versioning, WebSockets, sagas, and more — and
can be read on demand.

---
*Verification status: conceptual chapter — no runnable code. The patterns named
here are defined and applied in their own chapters, where the code ships with a
runnable example per language.*
