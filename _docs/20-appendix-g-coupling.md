---
title: "Balancing Coupling"
marker: "G"
label: "Appendix G"
order: 20
part: "Deep-dive appendices"
description: "Coupling has three dimensions — integration strength, distance, and volatility — and it only hurts when all three are high at once, which is why looser is not automatically better and why splitting a system can make coupling worse."
duration: 16 minutes
---

This book has used "coupled" and "decoupled" throughout as if loose were always the
goal. This appendix sharpens that, using Vlad Khononov's *Balancing Coupling* model.
The reframe is the whole point: coupling is *necessary* — a system with zero coupling
also has zero behaviour — so the skill is to balance it, not eliminate it. The model
gives precise language for why a shared database is bad but a registry-backed API
contract is fine, and it re-diagnoses every anti-pattern from the anti-patterns chapter
as one underlying imbalance.

## Coupling is necessary — balance it, don't eliminate it

Components must share *some* knowledge to collaborate, so "loosely coupled" is too
blunt a target. Khononov's model evaluates the **connection between two components** —
not the components themselves — along three dimensions: integration strength, distance,
and volatility. The headline is a single sentence: a coupling is only painful when
strength, distance, *and* volatility are all high at once, so reducing any one of the
three drops the pain.

That sentence is also why "just split it into microservices" can backfire. Splitting
strongly- and volatile-coupled code across a network does not remove the coupling — it
adds *distance* to it, pushing all three dimensions high simultaneously. The result is
a distributed monolith: the same tangle as before, now with network calls, partial
failures, and multi-team deploys layered on top. Distance is something you pay for; you
only want to pay it where the coupling across that distance is weak.

## The three dimensions

**Integration strength** is how much knowledge two parts share — the more they share,
the more likely a change in one forces a change in the other. **Distance** is how far
apart they sit — same method, class, module, service, or system — and it sets the cost
of any change that has to cross the boundary. **Volatility** is how often the coupled
thing actually changes; it is the dimension you cannot observe directly, but the DDD
appendix already gave the tool to predict it — a subdomain's type tells you its
change-rate, with core subdomains volatile and generic ones stable.

The design rule that falls out of this is Khononov's, rendered as a slogan worth
keeping: **modularity = strength XOR distance.** You want exactly one of strength and
distance, never both. Strong-and-local is a cohesive module — healthy. Weak-and-distant
is healthy microservices integrating through contracts. Strong-and-distant is the trap.
A strong, distant coupling on something that *never* changes still costs nothing — which
is why all three dimensions have to be weighed together rather than chasing "loose
coupling" in the abstract.

## Integration strength is a ladder

Strength is not binary; it is a ladder with four rungs, worst to best:

- **Intrusive** — one component reaches into another's private internals. The canonical
  case is two services sharing one database: either can break the other invisibly,
  because neither knows what the other depends on. This is the shared-database
  anti-pattern, and its strength is both maximal and hidden.
- **Functional** — two parts share business logic or rules and must change together for
  functional reasons.
- **Model** — they share a data model or DTOs, typically a shared library of types.
- **Contract** — they integrate only through an explicit, stable, *versioned* contract.
  That is exactly the REST, gRPC, GraphQL, and Kafka schemas governed by the registry.

Lower on the ladder means less shared knowledge and looser coupling, and the rule that
makes the ladder actionable is: **the greater the distance, the further down this
ladder you must be.** Inside a single bounded context, functional or model coupling is
fine — a shared library among code that already releases together costs little. Across
independently-deployed services, only contract coupling is appropriate, because it is
the loosest strength that still lets services collaborate; reaching for shared state
across that distance is how the distributed monolith forms.

## Strength × distance, and volatility as the trigger

Put strength and distance on two axes and the design space resolves into four
quadrants — only one of which is dangerous.

{% include excalidraw.html
   file="20-coupling-quadrant"
   alt="A two-by-two of integration strength (vertical) against distance (horizontal). Strong and close is a cohesive module (healthy); strong and distant is the distributed monolith (the trap); weak and close is needless indirection; weak and distant is healthy microservices. A note states that volatility is the trigger — even the trap quadrant is harmless on code that never changes."
   caption="Figure G.1 — Balance means having strength or distance, not both; volatility decides whether an imbalance actually bites" %}

The two healthy quadrants are a cohesive module (strong, close) and contract-integrated
services (weak, distant). The bottom-left, weak-and-close, is merely needless
indirection — you have split things that could simply be merged. The top-right,
strong-and-distant, is the distributed monolith, where one change ripples across
services and teams.

What turns that danger quadrant from a diagram into an outage is the third dimension.
**Distance is the cost multiplier**: a change contained in one module is a one-line
edit; the same change spanning two services and two teams is a slow, multi-deploy
project. **Volatility is the trigger**: a strong, distant coupling on code that never
changes is harmless, while the same coupling on hot core-domain code is where slow
delivery and outages originate. So you predict volatility from the domain — keep the
couplings around volatile core subdomains weak and local, and spend your tolerance for
stronger or more distant coupling on stable, generic areas. Khononov's full balance
condition: **balance = (strength XOR distance) OR low volatility** — route any
unavoidable strong-and-distant coupling to the code that rarely changes.

## Coupling and the APIs in this book

Read through this lens, every protocol decision in the book was secretly a coupling
decision, and the answer was always the same: choose **contract coupling**, the loosest
strength that still works across service distance. The registry is what keeps that
contract coupling stable — its compatibility rules stop a producer from silently
*raising* the integration strength on its consumers, which is precisely what a breaking
change is.

There is a finer-grained classical lens on the same idea: **connascence** (Page-Jones),
which names the specific ways two pieces of code must change together. API versioning is
managing connascence of name and position in your schemas — and protobuf field numbers
are connascence of position made explicit and held stable, which is why you never
renumber a field. The model also re-diagnoses the anti-patterns chapter as a single
principle rather than a list of separate rules: a shared database is intrusive strength
at distance; chatty synchronous call chains are strong, distant, *and* volatile all at
once; leaky internal models are model coupling reaching across a boundary that should
only carry a contract.

## Heuristics for balanced coupling

The design-review checklist, drawn straight from the model:

- Don't chase zero coupling — chase **balance**. Strong coupling is fine when it is
  local and stable.
- As distance grows, drive strength **down**: across services, integrate only through
  versioned contracts, never shared state.
- Keep strong, volatile couplings inside a single bounded context or aggregate, where
  distance is small.
- Use DDD subdomain types to **predict volatility**, and put your weakest couplings
  around the parts that change most.

The two references behind this appendix and the DDD one are Vlad Khononov's *Learning
Domain-Driven Design* (O'Reilly) for the boundary tools and *Balancing Coupling in
Software Design* (Addison-Wesley) for this model.

### Cross-check it yourself

This appendix has no code to run, so cross-check it against your own system in a design
review. Pick one real cross-service integration and score its connection on all three
dimensions: rate the **strength** by naming the rung — does the consumer touch a shared
table (intrusive), import a shared model (model), or speak only a registered schema
(contract)? Rate the **distance** — same module, or two services owned by two teams?
Rate the **volatility** — is the thing being shared in a core subdomain that changes
weekly, or a generic one that has not moved in a year? A connection that scores high on
all three is your distributed-monolith risk, and the model tells you which lever is
cheapest to pull: usually drive strength down to a contract, since distance and
volatility are often fixed by the org chart and the domain. If your worst-scoring
integration is already contract-coupled and sits on stable code, the model says to leave
it alone — which is the appendix's real lesson: looser is not automatically better.

---
*Verification status: unverified — this is a conceptual appendix with no runnable
example; its claims are model-level (Khononov's *Balancing Coupling*) rather than code
that executes. There is no `examples/` runner for it; verification here means a design
review confirms the three-dimension scoring matches how changes actually propagate in a
real system.*
