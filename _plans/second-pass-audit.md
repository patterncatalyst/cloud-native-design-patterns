# Second-Pass Audit — diagram & content fidelity vs. the source decks

**Purpose.** The site was built one-diagram-per-chapter and with condensed prose. The
canonical Python deck carries roughly **one content diagram per concept** (~100 in total)
plus far more per-concept detail. This audit maps the gap so the second pass is systematic:
reproduce every concept diagram in house style, and restore the per-concept detail (the
pros/cons/when-to-use, the per-pattern specifics) that was compressed away.

Reference deck: `Designing-Cloud-Native-APIs-Python.pptx` (canonical). Appendix J is audited
against the .NET deck (it is .NET-only). Slide numbers below are Python-deck indices.

## Scoreboard

- Deck content diagrams (cleaned of title/“Questions?” decoration): **~98**
- Site diagrams today: **31**
- Appendix L already rebuilt at full fidelity (6/6). Chapters 00, 08, 09, 10, 13 already
  match the deck's diagram count.
- **New house diagrams to add across the back catalogue: ~57**, plus **12** for Appendix M
  (new authoring), spread over ~19 chapters.

## Per-chapter gap table

`Δdiag` = deck content diagrams − site diagrams. `code` compares deck code slides to site
codetabs/blocks. Priority weights diagram gap + content/code gap.

| Chapter | Deck diag | Site diag | Δdiag | Deck code | Site codetabs | Content note | Priority |
|---|---|---|---|---|---|---|---|
| 00 Setting up | 2 | 2 | 0 | 2 | 0 | OK | — |
| 01 Cloud-Native Principles | 3 | 1 | **2** | 3 | 1 | 12-factor table + mapping under-covered | High |
| 02 Communications | 3 | 1 | **2** | 3 | 1 | protocol-choice + sync/async detail | High |
| 03 Composition | 2 | 1 | **1** | 1 | 1 | three-compose-ways detail | Med |
| 04 Data | 5 | 1 | **4** | 2 | 1 | per-service DB, CQRS, log-tail, outbox, saga all want figures | High |
| 05 Event-Driven | 5 | 1 | **4** | 1 | 1 | backbone, schemas, sourcing-vs-streaming, landscape, log-as-truth | High |
| 06 Stream Processing | 2 | 1 | **1** | 2 | 1 | derive-streams + KEDA scaling | Med |
| 07 Workflows & Jobs | 2 | 1 | **1** | 0 | 0 | orchestration-vs-choreography; thin prose (702 w) | Med |
| 08 API Management | 1 | 1 | 0 | 1 | 0 | thin prose (581 w) | Low |
| 09 API Registry | 1 | 1 | 0 | 1 | 0 | thin prose (680 w) | Low |
| 10 API Metadata | 1 | 1 | 0 | 0 | 0 | thin prose (565 w) | Low |
| 11 Observability | 5 | 1 | **4** | 5 | 1 | signals, correlation, trace stitch, sampling; 5 code slides → 1 | High |
| 12 Security | 7 | 1 | **6** | 11 | 1 | 4 C's, sidecar, valet-key, zero-trust, PaC, bulkhead, claim-check; **11 code slides → 1** | **Top** |
| 13 Anti-Patterns | 1 | 1 | 0 | 3 | 0 | thin prose (693 w); 3 code slides → 0 | Med |
| A Protocols | 3 | 1 | **2** | 1 | 0 | three-paradigms, fetching, the-wire | High |
| B Versioning | 3 | 1 | **2** | 3 | 0 | REST/gRPC/GraphQL versioning figures | High |
| C WebSockets | 3 | 1 | **2** | 2 | 1 | scaling-fights-K8s, backplane, resume | High |
| D Sagas | 3 | 1 | **2** | 3 | 1 | state, compensation, data-passing | High |
| E Errors | 6 | 1 | **5** | 5 | 4 | one-model-four-formats + 4 protocol figures | High |
| F DDD & Hexagonal | 3 | 1 | **2** | 1 | 1 | strategic-DDD, context-mapping (hexagonal done) | Med |
| G Coupling | 3 | 1 | **2** | 0 | 0 | three-dimensions, strength-ladder (quadrant done) | Med |
| H Graceful Shutdown | 2 | 1 | **1** | 2 | 1 | per-workload-drain (sequence done) | Med |
| I L7 Routing | 8 | 1 | **7** | 6 | 2 | L4-vs-L7, layered-stack, journey, sticky, steering, in-app, hop-cost, east/west | High |
| J .NET Toolkit | 0 (tables) | 0 | 0 | — | — | tables transcribed; OK | — |
| K Monolith→Micro | 8 | 1 | **7** | 2 | 2 | monolith, modular, decomposed-db, identify/move/redirect, proxy, proxy+redirect, shared-db, decorator | High |
| L Caching | 6 | 6 | 0 | 6 | 6 | **done at full fidelity** | ✓ |
| M Failure Modes | 12 | 0 (stub) | **12** | ~6 | 0 | new authoring at full fidelity | New |
| ★ Glossary | 0 | 0 (stub) | 0 | 0 | 0 | new authoring (table) | New |

## Diagram manifest (the to-do list)

Each line is a deck slide carrying a content diagram to reproduce in house style. Chapters
already at parity (00, 08, 09, 10, 13, J, L) are omitted.

**01 Cloud-Native Principles** — s7 cloud-native runtime properties · s11 the twelve factors · s12 twelve factors mapped to the system
**02 Communications** — s15 pick the protocol for the interaction · s18 synchronous coupling vs asynchronous facts · s19 the mesh handles the wire
**03 Composition** — s22 one query, many services · s24 three ways to compose
**04 Data** — s26 database-per-service · s27 CQRS · s29 log tailing (commit log as event source) · s30 dual-write is a lie / outbox · s32 saga (consistency without DTX)
**05 Event-Driven** — s34 the event backbone · s36 schemas as contract / registry · s37 event sourcing vs streaming · s38 tools landscape · s39 the log is the source of truth
**06 Stream Processing** — s41 derive streams from streams · s43 KEDA scales on the right signal
**07 Workflows & Jobs** — s46 orchestration vs choreography · s48 jobs / CronJobs / queue workers
**11 Observability** — s59 three signals, one story · s60 signals in depth · s64 context propagation · s66 a single trace stitches the request · s67 head vs tail sampling
**12 Security** — s71 the 4 C's · s74 sidecar pattern · s76 valet-key · s79 zero-trust / IAP · s81 policy-as-code · s83 bulkhead · s85 claim-check
**A Protocols** — s98 three paradigms · s99 over/under-fetching & round trips · s100 the wire (transport/encoding/streaming)
**B Versioning** — s104 four ways to version REST · s106 gRPC breaking changes · s108 GraphQL evolution
**C WebSockets** — s113 why WebSockets fight K8s scaling · s115 pub/sub backplane · s117 resume don't restart
**D Sagas** — s120 where a saga keeps state · s122 compensating transactions · s124 step B needs step A's data
**E Errors** — s127 one model, four formats · s128 REST problem+json · s130 gRPC rich status · s132 Kafka retry/DLQ · s134 GraphQL errors[] · (retry-storm done)
**F DDD** — s140 strategic DDD subdomains · s142 context mapping · (hexagonal done)
**G Coupling** — s150 three dimensions · s152 strength ladder · (quadrant done)
**H Shutdown** — s162 per-workload drain · (sequence done)
**I L7 Routing** — s169 L4 vs L7 · s171 layered stack · s172 request journey · s178 sticky sessions · s180 traffic steering · s186 in-app rule routing · s189 hop-cost budget · s191 east/west
**K Monolith→Micro** — s198 monolith as deploy unit · s199 modular monolith · s200 decomposed DBs · s201 identify/move/redirect · s202 proxy step-zero · s203 proxy + redirection · s204 shared DB · (decorator/strangler done)

## Content (non-diagram) gaps

Separate from diagrams, these chapters under-carry the deck's prose/code and should be
deepened in the same pass:

- **12 Security** — the deck has **11 code slides** (sidecar, valet-key, zero-trust, PaC,
  bulkhead, claim-check, mTLS, JWT, …); the site chapter has one codetab. Biggest single gap.
- **11 Observability** — 5 code slides → 1 codetab; restore traces/metrics/logs + correlation code.
- **13 Anti-Patterns** — 3 code slides → 0; thin prose.
- **01, 02, 04, 06** — each has 2–3 code slides collapsed to one codetab.
- **07, 08, 09, 10** — thin prose (565–702 words); deepen per-concept detail.

## Second-pass sequence

Front-to-back, one chapter per round (Top/High first within the natural order). 00 is
already at parity, so the pass effectively begins at **01**:

1. 01 → 02 → 03 → 04 → 05 → 06 → 07 (core, first half)
2. 11 → 12 → 13 (the high-value Observability/Security/Anti-patterns block; 08–10 are light touch-ups)
3. A → B → C → D (early appendices)
4. E → F → G → H → I → K (later appendices; E/I/K are the big ones)
5. New authoring: **M** (r-series, 12 diagrams) and the **Glossary**

Each round: re-extract the chapter's deck slides, add the missing house-style diagrams,
fold in the condensed detail (and any missing codetabs), re-run the validation suite, ship a
`feat(rNN): enrich <chapter> — diagrams + detail` delta.
