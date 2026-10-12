# Designing-Cloud-Native-APIs-Python

> Amended 2026-10-12 for user decision 7 (vendor-neutral): see the last section, which supersedes the rows here
> on the valet-key and claim-check slides, the cloud-SDK pins and Appendix S.

272 slides at 8c86d61. Deck-specific edits live in `lgtm-presentation/edits/Designing-Cloud-Native-APIs-Python.json`
(built from the work files `rewrites/30-deck-Python.json` and `ops-30-deck/Designing-Cloud-Native-APIs-Python.json`);
shared voice, Appendix O, shared code, images, agenda and Appendices R and S come from the other parts of the
manifest (see `README.md`).

## Summary

- Stack: Poetry is gone (slides 10 and 14: pip with a full `==` freeze in `requirements.txt`, as every Python
  example does); `@app.on_event("startup")` is replaced by a FastAPI lifespan (slides 221, 223); Faust becomes
  faust-streaming 0.15.3 (slides 43, 186).
- Code: 11 Python code boxes rewritten or patched to match the site codetab and `examples/` (Pydantic 2
  `model_dump*`, the `order.placed` topic, Apicurio 3.3's 400, the saga statuses of example 17, the protobuf
  envelope field numbers of Appendix C, the gRPC servicer of example 02, a Python syntax error on slide 78).
- Notes: notes rewritten where the code changed (14, 43) and token fixes (55, 123); the cover, overview and
  thank-you notes no longer say "four appendices".
- Voice: 10 deck-exclusive units (2 ban `for free`, 1 ban `deliberately`, ALL-CAPS, em-dash pairs, `actually`,
  `Easy`).

## Changes

| Slide | sldId | Title | Category | Change |
|---|---|---|---|---|
| 1 | 256 | Designing Cloud-Native APIs | notes | "four appendices go deep on…" → the appendices A–S, incl. Example 05 on minikube and OpenShift Local |
| 3 | 258 | What we'll build | notes | "four deep-dive appendices" → appendices A to S |
| 10 | 265 | Design-first | stack | bullet "Poetry for reproducible Python builds" → "pip with a fully pinned requirements.txt…" |
| 14 | 269 | A 12-factor FastAPI service | code, notes | code from `examples/01-cloud-native-principles/python/main.py` (Settings with defaults, version from SERVICE_VERSION, lifespan, readyz runs `SELECT 1`); notes follow |
| 17 | 272 | REST at the edge | voice | "for free" (unit 556) |
| 18 | 273 | gRPC for internal calls | code | servicer is the sync `grpc.server` servicer of `_docs/02` / example 02 (`remaining = stock.reserve(...)`) |
| 24 | 279 | A composing resolver in Strawberry | code | `ReserveStock_view` → `reserve_stock_view` (site tab) |
| 29 | 284 | CQRS in practice | code | `order.json()` → `order.model_dump_json()`; topic `order.created` → `order.placed` (code and comment) |
| 32 | 287 | The outbox write | code, voice | site tab (`model_dump_json`); notes "deliberately" (unit 557) |
| 36 | 291 | Producing and consuming with aiokafka | voice | "commit AFTER" (unit 558) |
| 43 | 298 | A windowed aggregation with faust-streaming | stack, code, notes | title, chip `python · faust-streaming`, code from `_docs/06` (memory store, `revenue.by-merchant`, `relative_to_stream`), notes rewritten |
| 55 | 310 | Gate breaking changes in CI | code, version | 409 → 400 (Apicurio 3.3.3) in code and notes |
| 78 | 333 | S3 pre-signed URL | code | parameter order (`body` before the `Depends` default; was a SyntaxError) |
| 96, 97 | 351, 352 | Glossary | voice | em-dash pairs in the WAL/TTL/LRU/SETEX and WSGI/ASGI entries |
| 106 | 361 | Media-type versioning | code | `order.dict()` → `order.model_dump()` (2) |
| 113 | 368 | A WebSocket endpoint | voice | caption "Easy to write — but note" (unit 561) |
| 117 | 372 | Binary framing with protobuf | code | envelope field numbers and `type="OrderPlaced"` as in `_docs/16`; `push()` from the site tab |
| 122 | 377 | A persisted saga state machine | code | status `DONE` → `COMPLETED` (example 17) |
| 123 | 378 | Compensating transactions (diagram) | notes | "persisted FAILED state" → "persisted COMPENSATED state" |
| 124 | 379 | Running compensations in reverse | code | status `FAILED` → `COMPENSATED` |
| 168 | 423 | Appendix I divider | voice | "actually" (unit 562) |
| 186 | 441 | Beyond the edge: routing inside the app | stack | "a Faust agent" → "a faust-streaming agent" |
| 187, 188 | 442, 443 | durable-rules | voice | em-dash pairs (units 563, 564) |
| 221 | 476 | Write-back | code | lifespan task instead of `@app.on_event("startup")` (site tab, 25-line excerpt) |
| 223 | 478 | Refresh-ahead | code | lifespan task instead of `@app.on_event("startup")` (site tab, read path shortened to the hot-list touch) |
| 237 | 492 | Timeouts + deadlines | voice | "for free" (unit 565) |
| 95 | 350 | Thank you | notes | "The four appendices" → "The appendices" |

## Code map (every code slide)

Status: `matches` (agrees with the site codetab and the example), `replaced` (rewritten or patched by this
manifest), `illustrative-ok` (no site tab or example for this exact code; checked against the locked stack
and current APIs), or the owner when another part of the manifest handles the slide.

| Slide | sldId | Title | Chip | Site codetab | Example | Status |
|---|---|---|---|---|---|---|
| 14 | 269 | A 12-factor FastAPI service | python · FastAPI | `_docs/01` "A twelve-factor service" (stale: site fix 1) | `examples/01-cloud-native-principles/python/main.py` | replaced |
| 17 | 272 | REST at the edge with FastAPI | python · FastAPI | `_docs/02` "REST at the edge" | `examples/02-communications/python/order-service/main.py` | matches |
| 18 | 273 | gRPC for internal calls | protobuf + python · grpc | `_docs/02` "gRPC for internal calls" | `examples/02-communications/python/{proto/inventory.proto,inventory-service/main.py}` | replaced |
| 21 | 276 | Resilience as configuration | yaml · istio | — | — | owner: shared-code |
| 24 | 279 | A composing resolver in Strawberry | python · Strawberry | `_docs/03` "The resolver makes it concrete" | `examples/03-composition/python/gateway/main.py` (adds a DataLoader) | replaced |
| 29 | 284 | CQRS in practice | python · FastAPI + asyncpg + aiokafka | none (04 has only the outbox tab) | `examples/04-data/python/order-service/main.py` (outbox, `order.placed`) | replaced |
| 32 | 287 | The outbox write | python · asyncpg + Debezium | `_docs/04` "The code, in your language" | `examples/04-data/python/order-service/main.py` | replaced |
| 36 | 291 | Producing and consuming with aiokafka | python · aiokafka | `_docs/05` "Producing and consuming" | `examples/05-event-driven/python/*` | matches |
| 43 | 298 | A windowed aggregation | python · faust-streaming | `_docs/06` "A windowed aggregation" | `examples/06-stream-processing/python/stream-processor/main.py` | replaced |
| 45 | 300 | Scale on lag and on RPS | yaml · KEDA | — | — | owner: shared-code |
| 55 | 310 | Gate breaking changes in CI | python · Apicurio v3 | `_docs/09` registry client tab | `examples/09-api-registry/verify.sh` (400 + RuleViolationException) | replaced |
| 64 | 319 | Auto-instrument FastAPI | python · OpenTelemetry | `_docs/11` "Auto-instrument your service" | `examples/11-observability/python/*` | matches |
| 66 | 321 | Baggage in practice | python · OpenTelemetry baggage API | `_docs/11` "How correlation works" (shorter) | — | illustrative-ok (opentelemetry-api 1.45.1 baggage/context API) |
| 78 | 333 | S3 pre-signed URL | python · FastAPI + boto3 | `_docs/12` "The valet key…" (shorter, same `generate_presigned_url`) | `examples/12-security/python` (HMAC valet key, no S3) | replaced (syntax) |
| 83 | 338 | OPA Gatekeeper ConstraintTemplate | yaml · OPA Gatekeeper | — | — | owner: shared-code |
| 85 | 340 | Per-tenant bulkheads in asyncio | python · asyncio + aiohttp | `_docs/12` "Bulkhead" (Semaphore per tenant) | `examples/12-security/python/order-service/main.py` (`_tenant_sem`) | illustrative-ok |
| 87 | 342 | Claim-check | python · boto3 + aiokafka | `_docs/12` "Claim-check" (store/token variant) | — | illustrative-ok |
| 106 | 361 | Media-type versioning | python · FastAPI | none (http/proto blocks only) | — | replaced (Pydantic 2) |
| 108 | 363 | Evolving a .proto safely | protobuf | — | — | owner: shared-code |
| 110 | 365 | Deprecating a field in Strawberry | python · Strawberry | `_docs/15` "GraphQL evolves" | — | matches |
| 113 | 368 | A WebSocket endpoint in FastAPI | python · FastAPI | `_docs/16` "A WebSocket endpoint" | `examples/16-websockets/python/ws-server/main.py` | matches |
| 117 | 372 | Binary framing with protobuf | protobuf + python | `_docs/16` envelope.proto + "Binary framing" tab | — (example 16 uses JSON frames) | replaced |
| 122 | 377 | A persisted saga state machine | python · asyncpg | `_docs/17` "Where the saga keeps its state" | `examples/17-sagas/python/saga-orchestrator/main.py` | replaced |
| 124 | 379 | Running compensations in reverse | python · asyncpg | `_docs/17` "Compensation unwinds" | same | replaced |
| 126 | 381 | Carrying context forward | python · asyncpg | — | same (context accumulated per step) | illustrative-ok |
| 130 | 385 | REST errors with FastAPI | python · FastAPI | `_docs/18` REST tab | `examples/18-errors/python/order-service` | matches |
| 132 | 387 | gRPC errors with rich status | python · grpc + grpcio-status | `_docs/18` gRPC tab | `examples/18-errors/python/inventory-service` | matches |
| 134 | 389 | Kafka retry + DLQ | python · aiokafka | `_docs/18` Kafka tab | — | matches |
| 136 | 391 | GraphQL field errors | python · Strawberry | `_docs/18` GraphQL tab | — | matches |
| 146 | 401 | Ports & adapters in code | python · ports & adapters | `_docs/19` "Hexagonal architecture" | `examples/19-ddd-hexagonal/python` | matches |
| 164 | 419 | Graceful shutdown in FastAPI / uvicorn | python · FastAPI + uvicorn | `_docs/21` "The application side" | `examples/21-graceful-shutdown/python` | matches |
| 165 | 420 | The Kubernetes side | yaml · Kubernetes | — | — | owner: shared-code |
| 175 | 430 | HAProxy | haproxy.cfg | — | — | owner: shared-code |
| 176 | 431 | Nginx | nginx.conf | — | — | owner: shared-code |
| 177 | 432 | Istio VirtualService | yaml | — | — | owner: shared-code |
| 182 | 437 | Canary | yaml | — | — | owner: shared-code |
| 183 | 438 | Header-based steering | yaml | — | — | owner: shared-code |
| 185 | 440 | Header injection | yaml | — | — | owner: shared-code |
| 188 | 443 | The rules, externalised | python · durable-rules | `_docs/22` rules tab | — (example 22 routes in plain code) | matches |
| 189 | 444 | The dispatcher, in FastAPI | python · FastAPI + aiokafka | `_docs/22` dispatcher tab | — | matches |
| 194 | 449 | Istio east/west | yaml | — | — | owner: shared-code |
| 206 | 461 | Content-based routing during migration | python · FastAPI + httpx | `_docs/24` routing tab (comments differ only) | `examples/24-monolith-to-microservices/python` | matches |
| 208 | 463 | A decorating collaborator | python · FastAPI + httpx + redis + aiokafka | `_docs/24` decorator tab (line wrap only) | same | matches |
| 213 | 468 | Cache-aside | python · FastAPI + redis.asyncio + Postgres | `_docs/25` cache-aside tab | `examples/25-caching/python` | matches |
| 215 | 470 | Read-through | python · read-through wrapper | `_docs/25` read-through tab (assignment style only) | same | matches |
| 217 | 472 | Write-through | python · write-through | `_docs/25` write-through tab (slide adds the "fast" variant) | same | matches |
| 219 | 474 | Write-around | python · write-around | `_docs/25` write-around tab (slide adds the invalidate variant) | same | matches |
| 221 | 476 | Write-back | python · asyncio background task | `_docs/25` write-back tab | same | replaced |
| 223 | 478 | Refresh-ahead | python · Redis sorted set | `_docs/25` refresh-ahead tab | same | replaced |
| 237 | 492 | Timeouts + deadlines | python · httpx + asyncio | `_docs/26` timeouts tab | `examples/26-failure-modes/python/edge-service/main.py` | matches |
| 239 | 494 | Retry with backoff + jitter | python · tenacity | `_docs/26` retry tab | same (hand-written retry) | matches |
| 241 | 496 | Circuit breaker + fallback | python · purgatory | `_docs/26` breaker tab | same (hand-written breaker) | matches |
| 245 | 500 | Graceful shutdown (App. H) | python · FastAPI lifespan | `_docs/26` / `_docs/21` | `examples/21-graceful-shutdown/python` | illustrative-ok (lifespan, current) |
| 253 | 508 | Evaluating a flag | python · FastAPI | `_docs/27` OpenFeature tab | `examples/27-feature-flags/python` (openfeature-sdk 0.10.0, provider-flagd 0.5.2) | matches |
| 254 | 509 | Targeting and rollout | json · flagd | — | — | owner: shared-code |
| 256 | 511 | A kill switch | python · FastAPI | `_docs/27` kill-switch tab | same | matches |
| 264 | 519 | Tests live in the request | json · Postman | — | — | owner: planner (App O) |
| 266 | 521 | Launch the service under test | bash · Python | — | — | owner: planner (App O) |
| 267 | 522 | Running Newman | bash | — | — | owner: planner (App O) |
| 269 | 524 | Newman in CI | yaml · GitHub Actions | — | — | owner: planner (App O) |

Counts (the 43 Python-owned code slides): matches 24, replaced 14, illustrative-ok 5. Owned elsewhere: 17
(shared-code 13, planner 4).

## Version strings left in the deck

None of the Python deck's own slides or notes name a library or runtime version after the edits (the code
uses names, not versions). `Apicurio v3` (chip, slide 55) agrees with the pin 3.3.3; `TLS 1.3` and
`Apache 2.0` are standards and licences, not pins.

## Unresolved

- Slide 13 image `42-twelve-factor-map-py.png` probably shows "Poetry" like the site's `01-factors-mapped`
  figure; the image-audit part owns it (site fix 2 regenerates the site figure).
- The "four appendices" correction (slides 1, 3, 95 notes) is a fact shared with the other language decks; each
  deck part must make the same change.
- Slides 85 (aiohttp sessions) and 87 (boto3 calls inside async code) stay as illustrations: neither library is
  in the Python lock, both APIs are current, and the site teaches the same pattern with asyncio only.

## Decision 7 amendment (vendor-neutral, 2026-10-12)

Generator: `tools/amend_vendor.py` (ops tagged `_vendor`, inserted just before the agenda op; run after `amend_decisions.py`).
Find strings and counts come from the pre-decision text copy (`verify_all.py` output of the edit files at 39a5b1e).

- Appendix S removed: the `clone_slide` ops `s0`–`s9` and every `set_*` op on `$s*` are dropped (71 ops); Appendix R (9 slides) stays. Agenda line "Appendix R · Example 05 on minikube" (same line count, so the agenda fit is unchanged); agenda notes, the title and overview notes and the R0/R1 notes no longer mention OpenShift Local ("carries over to any conformant Kubernetes cluster").
- Valet key (sldId 333): title "Valet key — scoped, time-bound, op-restricted", chip `python · FastAPI + hmac (stdlib)`, `set_code` = `examples/12-security/python/order-service/main.py` (`_mint_valet`, `_verify_valet`, `/valet-key`), 22 lines, notes rewritten (HMAC or HS256 ticket the service mints and verifies; generic object store). Code map row: matches `examples/12-security` (condensed excerpt, first comment line says so).
- Claim check (sldId 342): chip `python · aiokafka + Example 12 valet key`, `set_code` = aiokafka producer/consumer with a generic `store` and `**_mint_valet(key, "GET", ttl=900)` in the claim, 18 lines; notes rewritten. Same lines as the site claim-check codetab after the site fix (`site-fixes.md`, decision-7 section). No example implements the claim check (illustrative, token from Example 12).
- Removed: boto3 (slides 78, 87); the S3 pre-signed URL, STS AssumeRole, Azure SAS, GCS framing.
- Shared rewrites (where present in this deck): 4C's notes and bullet (CloudTrail, "S3 bucket open"); event-driven tools notes ("to S3" → "to an object store"); valet-key concept notes (one generic implementation sentence instead of S3/Azure/GCS/STS); strangler-fig IdPs (Keycloak, Dex instead of Auth0, Azure AD); zero-trust edge (Pomerium or OAuth2 Proxy in front of Keycloak instead of Google IAP, Cloudflare Access, AWS Verified Access; licence note Pomerium Apache-2.0, OAuth2 Proxy MIT); claim-check concept notes; choosing-the-pattern notes; glossary SAS entry and note removed; Appendix I gateway list without Apigee; Appendix M references: gRFC A6 instead of the AWS Builders' Library.
- Kept (not vendor services): Heroku as the origin of the twelve-factor methodology (history), Google SRE Book (reference), gRPC / Google.Protobuf / Google.Rpc (open-source libraries), Netflix concurrency-limits (Apache-2.0 library), Red Hat UBI and the Red Hat brand frame.
- Figures (`replace_picture`, `tools/vendor_figures.py`): sldIds 332 (valet-key concept), 335 (zero-trust), 427 (Appendix I layered stack, Apigee). The valet-key figure named S3, Azure SAS, GCS and STS; the zero-trust figure listed Google IAP, Cloudflare Access and AWS Verified Access; both become the neutral site figures (`12-valet-key.png` with "object store" labels, `12-zero-trust.png`); the layered stack becomes the site `22-l7-layers.png`, as in the Go, C++ and .NET decks.
