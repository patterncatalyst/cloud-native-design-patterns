---
title: "Balancing Coupling"
marker: "G"
label: "Appendix G"
order: 20
part: "Deep-dive appendices"
description: "Coupling has three dimensions — integration strength, distance, and volatility — and it only hurts when all three are high at once, which is why looser is not automatically better and why splitting a system can make coupling worse."
duration: 30 minutes
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

{% include excalidraw.html
   file="20-three-dimensions"
   alt="Khononov's balanced-coupling model has three dimensions, multiplied together. Integration strength: how much knowledge two parts share, from intrusive to contract. Distance: how far apart they sit, from method to class to module to service to system. Volatility: how often the coupled part changes, core versus generic subdomain. The cost of a coupling is that strong plus distant equals global complexity, a distributed monolith — but it only bites when the code is volatile."
   caption="Figure G.1 — Coupling has three dimensions; a coupling only hurts when strength, distance, and volatility are all high at once" %}

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

{% include excalidraw.html
   file="20-strength-ladder"
   alt="Integration strength as a four-rung ladder, worst to best, each with its example in our system. Intrusive coupling reaches into another's private internals — a shared database or scraping internals. Functional coupling shares business logic and rules — duplicated or co-owned domain logic. Model coupling shares a data model or DTOs — a shared library of types. Contract coupling integrates via an explicit, stable contract — REST, gRPC, or GraphQL plus a registry schema. Across services, aim for contract coupling."
   caption="Figure G.2 — The integration-strength ladder; across services, aim for the bottom rung — contract coupling" %}

## Strength × distance, and volatility as the trigger

Put strength and distance on two axes and the design space resolves into four
quadrants — only one of which is dangerous.

{% include excalidraw.html
   file="20-coupling-quadrant"
   alt="A two-by-two of integration strength (vertical) against distance (horizontal). Strong and close is a cohesive module (healthy); strong and distant is the distributed monolith (the trap); weak and close is needless indirection; weak and distant is healthy microservices. A note states that volatility is the trigger — even the trap quadrant is harmless on code that never changes."
   caption="Figure G.3 — Balance means having strength or distance, not both; volatility decides whether an imbalance actually bites" %}

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

## The classical coupling vocabulary, mapped to the model

Khononov's three dimensions are not the only vocabulary for coupling — decades of
practitioner writing named the same forces from different angles. They are not rivals;
each is a finer lens on **strength** or **distance**, and mapping them onto the model
keeps you making decisions instead of collecting terms.

| Term | What it names | Where it lands in the model |
|---|---|---|
| **Module coupling** (content → common → control → stamp → data) | the classic structured-design ladder, content worst, data best | integration **strength**, at the code level |
| **Connascence** (static + dynamic) | the specific way two parts must change together | **strength**, finer-grained — with *locality* = distance |
| **Semantic coupling** | sharing the *meaning* of a concept (what an "order status" is) | strength — shared functional knowledge |
| **Temporal coupling** | one step must happen before another in time | a runtime sequencing dependency |
| **Lifecycle coupling** | parts must be built, released, or scaled together | **distance** collapsing — the distributed-monolith smell |
| **Runtime coupling** | at runtime, one part's availability or latency depends on another | operational distance — synchronous call chains (**Appendix M**) |
| **Afferent / efferent** (Ca / Ce) | who depends on you (Ca) versus whom you depend on (Ce) | a *measurable* proxy for fan-in, fan-out, and distance |

**Connascence** is worth drawing out because it is the most precise of these. It comes
in two families — *static* forms visible in the code and *dynamic* forms that surface
only at runtime — each ordered weakest to strongest, and it carries one rule that is
the three-dimension model in miniature: the stronger the connascence, the more *local*
it must stay. Connascence of position across a service boundary (relying on field
order) is fragile; the same thing inside one function is fine. Protobuf field numbers
are connascence of position made explicit and frozen, which is exactly why you never
renumber a field.

{% include excalidraw.html
   file="20-connascence"
   alt="Connascence in two families, each weaker at the top and stronger at the bottom. Static connascence, visible in the code: Name (agree on an identifier), Type (agree on a type or shape), Meaning (a shared convention or magic value), Position (the same order of arguments or fields), Algorithm (the same algorithm on both sides). Dynamic connascence, only at runtime: Execution order (A must run before B), Timing (race-sensitive), Value (values must stay in agreement), Identity (the same instance or entity). The rule: the stronger the connascence between two parts, the more local they must stay."
   caption="Figure G.4 — Connascence: static and dynamic forms, weakest to strongest — keep stronger forms more local" %}

The **afferent / efferent** entry is the one you can actually measure. Afferent
coupling (Ca) counts who depends on a module; efferent (Ce) counts what it depends on.
Their ratio gives an *instability* score, `I = Ce / (Ca + Ce)`, running from 0 (nothing
depends outward — maximally stable) to 1 (depends on everything, depended on by nothing
— maximally unstable). The guidance that falls out is the stable-abstractions idea:
things many others depend on (low instability, high Ca) should change rarely and expose
abstractions, not concretions — which is just "keep strong, distant coupling on stable
code," restated as a number you can compute from an import graph.

## Choosing a coupling strategy with Cynefin

How much coupling is "right" depends on how well you understand the domain, and the
Cynefin framework names the four situations you might be in. The mistake it guards
against is applying a mature-domain answer — standardise everything on tidy contracts —
to a domain you don't yet understand, where the boundaries themselves are still guesses.

{% include excalidraw.html
   file="20-cynefin-coupling"
   alt="The four Cynefin domains, each with its coupling posture. Complex (probe, sense, respond): keep coupling loose and reversible — favour events and contracts, and don't split prematurely. Complicated (sense, analyse, respond): design boundaries deliberately with DDD context mapping and invest in the right contracts. Chaotic (act, sense, respond): stabilise first with strong, local coupling, even a monolith, then refactor as it clarifies. Clear (sense, categorise, respond): standardise on contract coupling and codify the known-good with registry-checked schemas."
   caption="Figure G.5 — Cynefin and coupling: match the posture to how well you understand the domain" %}

The throughline with the rest of the appendix: in a **complex** domain you keep
strength low and reversibility high because you *will* move the boundaries; once the
domain becomes **clear**, you can afford to standardise on the loosest workable strength
— contract coupling — and freeze it. The anti-pattern is treating an early, complex
domain as if it were clear, splitting it into services with contracts you then break
repeatedly. That is the model's "don't split prematurely" lesson dressed as a
sense-making framework.

Domain-Driven Design's context-mapping patterns (**Appendix F**) are this same choice,
catalogued. A *shared kernel* is high strength at low distance; *conformist* and
*anti-corruption layer* are ways to survive someone else's strength across distance; an
*open host service* with a *published language* is contract coupling by another name.
Picking a context-map relationship is picking where on the strength ladder a boundary
sits.

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
- Name the **connascence** before you move code: stronger forms (position, algorithm,
  value, identity) must stay local — weaken them to a contract before they cross a
  service boundary.
- Match coupling to **certainty**: in an unclear, complex domain keep it loose and
  reversible; standardise on contracts only once the domain is clear.

The two references behind this appendix and the DDD one are Vlad Khononov's *Learning
Domain-Driven Design* (O'Reilly) for the boundary tools and *Balancing Coupling in
Software Design* (Addison-Wesley) for this model. The classical vocabulary in this appendix draws on
Khononov's `coupling.dev` core-concepts series, Meilir Page-Jones's connascence
(`connascence.io`), and Robert C. Martin's afferent/efferent stability metrics.

### Cross-check it yourself

This appendix has no code to run, so cross-check it against your own system in a design
review. Pick one real cross-service integration and score its connection on all three
dimensions: rate the **strength** by naming the rung — does the consumer touch a shared
table (intrusive), import a shared model (model), or speak only a registered schema
(contract)? Then name the strongest **connascence** that crosses the boundary — if it is
position, algorithm, value, or identity, that is your first thing to weaken. Rate the **distance** — same module, or two services owned by two teams?
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
