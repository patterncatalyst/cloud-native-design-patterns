# Designing-Cloud-Native-APIs-Go — S12 manifest

> Amended 2026-10-12 for user decision 7 (vendor-neutral): see the last section, which supersedes the rows here
> on the valet-key and claim-check slides, the cloud-SDK pins and Appendix S.

The Go deck was an in-place retarget of the Python deck, so most Go code slides predated the site's Go codetabs
and many notes still described Python code (Faust, `aiohttp`, `tenacity`, `uvicorn` lifespan, `durable-rules`,
`redis-py`, `grpcio-status`). This pass brings every Go code slide in line with the site codetab and
`examples/*/go/` (Go 1.27.2, the locked libraries), rewrites the notes that described the old code, and removes
the graphql-go and Python leftovers from captions, bullets and the glossary.

Edit files (built into `lgtm-presentation/edits/Designing-Cloud-Native-APIs-Go.json`):

- deck content ops: 85 (set_code 26, set_notes 28, set_text 13, replace 18); by category code 41, notes 28,
  stack 12, voice 3, version 1.
- deck-exclusive voice rewrites: 9 (units 507, 508, 526, 544, 555); units 501, 502, 511, 528, 529 are superseded
  by a set_notes or set_text on the same slide (ledger `rewrites/ledger-deck-Go.tsv`).

Owned elsewhere: Appendix O (sldIds 516–527, planner), language-agnostic code slides (shared-code fork: 276, 300,
338, 363, 420, 430, 431, 432, 437, 438, 440, 449, 509), images, agenda (257) and Appendices R/S (planner), shared
voice sentences (voice forks).

## Changes

| Slide | sldId | Title | Category | Change |
|---|---|---|---|---|
| 1 | 256 | Designing Cloud-Native APIs | version | notes: "Go with net/http" → "Go 1.27.2 with net/http" |
| 10 | 265 | Design-first | stack | bullet: gqlgen generates Go resolvers from the SDL (it is schema-first; it does not generate SDL) |
| 14 | 269 | A 12-factor net/http service | code, notes | site 01 tab; version from `SERVICE_VERSION`; notes rewritten |
| 17 | 272 | REST at the edge with net/http | code, notes | site 02 REST tab (excerpt, `place` handler); caption and notes follow the excerpt |
| 18 | 273 | gRPC for internal calls | code, notes | proto from the example, server from the site 02 gRPC tab (embedded `UnimplementedInventoryServer`, generated getters); notes rewritten |
| 24 | 279 | A composing resolver in gqlgen | code, stack, notes | site 03 tab / example 03 (`Orders`, `attachStock`, one batched gRPC call); graphql-go removed from caption and notes |
| 29 | 284 | CQRS in practice | code, voice | topic `order.created` → `order.placed` (code twice); `SEPARATE` → `separate` |
| 32 | 287 | The outbox write | code, notes | site 04 tab; notes rewritten (unit 501 superseded) |
| 36 | 291 | Producing and consuming with franz-go | code, notes | site 05 tab with the example's group `notification-group`; notes rewritten (unit 502 superseded) |
| 43 | 298 | A windowed aggregation with goka | code, notes | site 06 tab / example 06 (two-stage group, `revenue.by-merchant`); Faust and "Python" removed from code and notes |
| 55 | 310 | Gate breaking changes in CI | code, notes | Apicurio 3.3 answers 400 (was 409); site 09 tab |
| 63 | 318 | Auto-injection vs. instrumentation | stack | bullet: Go OTel API names (`tracer.Start`, `span.SetAttributes`, `span.AddEvent`) |
| 64 | 319 | Instrument net/http with OpenTelemetry | code, notes | site 11 tab; span `reserve-stock` as in example 11; notes: context injected into record headers by the propagator |
| 66 | 321 | Baggage in practice | code, notes | site 11 tab key `tenant.id`; caption and notes |
| 78 | 333 | Valet key  —  scoped, time-bound, op-restricted | stack, code, notes | decision 6: title (was "S3 pre-signed URL …"), chip `go · net/http + golang-jwt v5`, code = example 12 `valetClaims`/`mintValet` + the `verifyValet` parse options (22 lines, 93 columns), notes rewritten (HS256 only, exp required, issuer, res/op/exp match; object-store pre-signed URLs named as the native equivalent); minio-go removed |
| 84 | 339 | Bulkhead | stack | notes: "x/sync/semaphore (Python)" → "buffered channels per tenant (Go)" |
| 87 | 342 | Producer mints claim, consumer fetches payload | stack, code, notes | decision 6: chip `go · franz-go + golang-jwt v5`; code = the site 12 Go claim-check tab shape (generic encrypted `store`, franz-go `ProduceSync`, topic `order.documents`) with the token from example 12's `mintValet`; notes rewritten (ticket lifetime vs consumer lag); minio-go removed |
| 85 | 340 | Per-tenant bulkheads | code, notes | buffered-channel bulkhead (site 12 tab, example 12); chip `go · buffered channel`; notes rewritten |
| 106 | 361 | Media-type versioning | stack | notes: "hand-building dicts" → "building maps by hand" |
| 110 | 365 | Deprecating a field in gqlgen | code, notes | SDL comments use `#` (the box had `//` inside SDL); site 15 tab field shape; notes rewritten |
| 113 | 368 | A WebSocket endpoint in Go | code, voice, notes | site 16 tab; caption rewritten (unit 511); notes rewritten |
| 117 | 372 | Binary framing with protobuf | code, notes | box held Python code: now envelope.proto + the site 16 Go `push`; chip `protobuf + go · coder/websocket` |
| 122 | 377 | A persisted saga state machine | code | site 17 tab; statuses RUNNING / COMPENSATING / COMPLETED as in example 17 |
| 124 | 379 | Running compensations in reverse | code, notes | terminal status `FAILED` → `COMPENSATED` (example 17); notes rewritten |
| 126 | 381 | Carrying context forward | stack | notes: `step_index` → `StepIndex`, `shipping.book` → `shipping.Book` |
| 130 | 385 | REST errors with net/http | code, notes | site 18 tab (unknown errors become a 500 instead of being dropped) |
| 132 | 387 | gRPC errors with rich status details | notes | Python grpcio-status wording replaced by the Go `status`/`errdetails` description |
| 134 | 389 | Kafka retry + DLQ with franz-go | code, notes | site 18 tab (retry and DLQ headers, traceId header); notes rewritten |
| 136 | 391 | GraphQL field errors with gqlgen | code, notes | site 18 tab (adds `Path: graphql.GetPath(ctx)`); caption and notes |
| 146 | 401 | Ports & adapters in code | code, notes | example 19 domain (`Save(ctx, *Order)`, `Publish(OrderPlaced)`, `PlaceOrder.Execute`) |
| 164 | 419 | Graceful shutdown in Go | code, notes | site 21 tab; caption without the uvicorn flag; notes without lifespan |
| 187 | 442 | Go + gopher-lua: routing by business rules | notes | durable-rules / Rete / Python description replaced (unit 528 superseded) |
| 188 | 443 | The rules, externalised | code, notes | site 22 Lua tab (`route(order, ctx)` returning a list); caption and notes (unit 529 superseded) |
| 189 | 444 | The dispatcher, in Go | code, notes | site 22 Go dispatcher (excerpt); notes describe the pooled sandboxed `LState` |
| 206 | 461 | Content-based routing during migration | code, notes | site 24 tab (`http.Client` with a 5 s timeout, as example 24); chip `go · net/http` |
| 207 | 462 | Decorating collaborator | stack | notes: "Common Python implementations" → "A common Go implementation" |
| 213 | 468 | Cache-aside in Go | notes | redis-py idioms (`from_url`, try/except) replaced |
| 215 | 470 | Read-through in Go | stack | caption `.get()` → `Get`; notes `products.Get(ctx, pid)` |
| 219 | 474 | Write-around in Go | voice | code comment without "deliberately NOT" |
| 221 | 476 | Write-back in Go | stack | notes: goroutine on a ticker, `CopyFrom` (was PERIOD_S / execute_many) |
| 223 | 478 | Refresh-ahead in Go | stack | notes: `REFRESH_BEFORE_S` → `refreshBefore` (2) |
| 237 | 492 | Timeouts + deadlines | voice | notes (unit 555): `context.WithTimeout` replaces `goroutines.wait_for`; "for free" removed |
| 239 | 494 | Retry with backoff + jitter | code, notes | cenkalti/backoff v4 API → v7 (`backoff.Retry(ctx, op, WithBackOff, WithMaxTries)`); chip `v7` |
| 241 | 496 | Circuit breaker + fallback | code, notes | sony/gobreaker v1 → v2 generic API (`NewCircuitBreaker[Receipt]`); chip `v2` |
| 245 | 500 | Graceful shutdown (App. M) | stack | notes: Python lifespan wording replaced |
| 253 | 508 | Evaluating a flag | code | `flagd.NewProvider` returns `(provider, error)` (the box did not compile) |
| 96 | 351 | Glossary 1 | stack, voice | unit 507: go-playground/validator row → struct tags; four em dashes → colons |
| 97 | 352 | Glossary 2 | stack | unit 508: no WSGI/ASGI or GIL; goroutine described on its own terms |
| 168 | 423 | Appendix I divider (notes) | voice | unit 526: "actually" removed |
| 215 | 470 | Read-through (notes) | positional | unit 544: "the wrapper above" → "the wrapper on this slide" |

## Code map (every code slide)

Status: `replaced` = the box now carries the named source (excerpt allowed); `matches` = already agrees with the
source on library, API and identifiers (token fixes listed); `illustrative-ok` = no Go codetab or example covers it;
API checked against the locked versions.

| Slide | sldId | Title | Chip | Site codetab | Example file | Status |
|---|---|---|---|---|---|---|
| 14 | 269 | A 12-factor net/http service | go · net/http | 01 "A twelve-factor service" | 01-cloud-native-principles/go/cmd/server/main.go | replaced |
| 17 | 272 | REST at the edge | go · net/http | 02 "REST at the edge" | 02-communications/go/order-service/cmd/server/main.go | replaced |
| 18 | 273 | gRPC for internal calls | protobuf + go · grpc | 02 "gRPC for internal calls" | 02-communications/go/proto/inventory.proto, inventory-service/cmd/server/main.go | replaced |
| 21 | 276 | Resilience as configuration | yaml · istio | — | — | owner: shared-code |
| 24 | 279 | A composing resolver in gqlgen | go · gqlgen | 03 "The resolver makes it concrete" | 03-composition/go/gateway/graph/schema.resolvers.go, resolver.go | replaced |
| 29 | 284 | CQRS in practice | go · net/http + pgx + franz-go | 04 (outbox write side) | 04-data/go/order-service/cmd/server/main.go | matches (topic fixed) |
| 32 | 287 | The outbox write | go · pgx + Debezium | 04 "The code, in your language" | 04-data/go/order-service/cmd/server/main.go | replaced |
| 36 | 291 | Producing and consuming | go · franz-go | 05 "Producing and consuming" | 05-event-driven/go/{order-service,notification-consumer} | replaced |
| 43 | 298 | Windowed aggregation | go · goka | 06 "A windowed aggregation" | 06-stream-processing/go/stream-processor/cmd/processor/main.go | replaced |
| 45 | 300 | Scale on lag and RPS | yaml · KEDA | — | — | owner: shared-code (its comment still says "scale FastAPI") |
| 55 | 310 | Gate breaking changes in CI | go · net/http | 09 "register a new version" | 09-api-registry (config only; 400 per S8) | replaced |
| 64 | 319 | Instrument net/http with OpenTelemetry | go · OpenTelemetry | 11 "Auto-instrument your service" | 11-observability/go/order-service/cmd/server/main.go | replaced |
| 66 | 321 | Baggage in practice | go · OpenTelemetry baggage | 11 "How correlation works" | — | replaced |
| 78 | 333 | Valet key | go · net/http + golang-jwt v5 | 12 "The valet key" (site fix: aws-sdk-go-v2 → the example's golang-jwt ticket) | 12-security/go/cmd/server/main.go (`mintValet`, `verifyValet`) | replaced |
| 83 | 338 | OPA Gatekeeper ConstraintTemplate | yaml · OPA Gatekeeper | — | — | owner: shared-code |
| 85 | 340 | Per-tenant bulkheads | go · buffered channel | 12 "Bulkhead" | 12-security/go/cmd/server/main.go | replaced |
| 87 | 342 | Claim-check | go · franz-go + golang-jwt v5 | 12 "Claim-check" (generic `store`, franz-go) | — (token: 12-security/go `mintValet`) | replaced (sketch; first comment line says so) |
| 106 | 361 | Media-type versioning | go · net/http | — (no Go REST tab in 15) | — | illustrative-ok |
| 108 | 363 | Evolving a .proto safely | protobuf | — | — | owner: shared-code |
| 110 | 365 | Deprecating a field in gqlgen | graphql · gqlgen | 15 "GraphQL evolves" | — | replaced |
| 113 | 368 | A WebSocket endpoint | go · coder/websocket | 16 "A WebSocket endpoint" | 16-websockets/go/ws-server/cmd/server/main.go | replaced |
| 117 | 372 | Binary framing with protobuf | protobuf + go · coder/websocket | 16 "Binary framing" | — | replaced |
| 122 | 377 | A persisted saga state machine | go · pgx | 17 "Where the saga keeps its state" | 17-sagas/go/saga-orchestrator/cmd/server/main.go | replaced |
| 124 | 379 | Running compensations in reverse | go · pgx | 17 "Compensation unwinds a failed saga" | 17-sagas/go | matches (status fixed) |
| 126 | 381 | Carrying context forward | go · pgx | 17 | 17-sagas/go (`executeStep`) | matches |
| 130 | 385 | REST errors | go · net/http | 18 "REST" | 18-errors/go/order-service/cmd/server/main.go | replaced |
| 132 | 387 | gRPC errors with rich status | protobuf + go · grpc | 18 "gRPC" | 18-errors/go | matches |
| 134 | 389 | Kafka retry + DLQ | go · franz-go | 18 "Kafka" | — | replaced (header literals instead of `append`; the site uses `append` only to avoid Liquid braces) |
| 136 | 391 | GraphQL field errors | go · gqlgen | 18 "GraphQL" | — | replaced |
| 146 | 401 | Ports & adapters | go · ports & adapters | 19 "Hexagonal architecture" (stale, see site fixes) | 19-ddd-hexagonal/go/order-service/domain | replaced (from the example) |
| 164 | 419 | Graceful shutdown | go · net/http | 21 "The application side" | 21-graceful-shutdown/go/cmd/server/main.go | replaced |
| 165 | 420 | The Kubernetes side | yaml · Kubernetes | — | — | owner: shared-code |
| 175–177 | 430–432 | HAProxy, Nginx, Istio VirtualService | — | — | — | owner: shared-code |
| 182, 183, 185 | 437, 438, 440 | Istio canary, header-based, Envoy | — | — | — | owner: shared-code |
| 188 | 443 | The rules, externalised | lua · gopher-lua | 22 Lua tab | 22-l7-routing/go/router-service (its `routing.lua` is a threshold variant) | replaced |
| 189 | 444 | The dispatcher | go · gopher-lua + franz-go | 22 Go dispatcher | 22-l7-routing/go/router-service/cmd/server/main.go | replaced |
| 194 | 449 | Istio east/west | yaml · Istio east/west | — | — | owner: shared-code |
| 206 | 461 | Content-based routing | go · net/http | 24 "Content-based routing" | 24-monolith-to-microservices/go/router | replaced |
| 208 | 463 | A decorating collaborator | go · net/http + go-redis + franz-go | 24 "The decorating collaborator" | 24-monolith-to-microservices/go/decorator | matches |
| 213 | 468 | Cache-aside | go · go-redis + pgx | 25 "Cache-aside" | 25-caching/go/cache-service | matches |
| 215 | 470 | Read-through | go · go-redis (generics) | 25 "Read-through" | 25-caching/go/cache-service | matches (loader returns `(T, error)`; the site's adds a found flag) |
| 217 | 472 | Write-through | go · go-redis + pgx | 25 "Write-through" | 25-caching/go | matches |
| 219 | 474 | Write-around | go · go-redis + pgx | 25 "Write-around" | 25-caching/go | matches (comment reworded) |
| 221 | 476 | Write-back | go · go-redis + goroutine | 25 "Write-back" | 25-caching/go (`flusher`, `metric:dirty`) | matches |
| 223 | 478 | Refresh-ahead | go · go-redis + goroutine | 25 "Refresh-ahead" | 25-caching/go (`refresher`, `product:hot`) | matches |
| 237 | 492 | Timeouts + deadlines | go · net/http + context | 26 "Timeouts" (gRPC variant) | 26-failure-modes/go | illustrative-ok |
| 239 | 494 | Retry with backoff + jitter | go · cenkalti/backoff v7 | 26 "Retry" | 26-failure-modes/go/edge-service | replaced |
| 241 | 496 | Circuit breaker + fallback | go · sony/gobreaker v2 | 26 "Circuit breaker" (stale, see site fixes) | 26-failure-modes/go/edge-service | replaced (v2 API from the example) |
| 245 | 500 | Graceful shutdown (App. M) | go · net/http | 21 | 21-graceful-shutdown/go | matches |
| 253 | 508 | Evaluating a flag | go · OpenFeature + flagd | 27 "Evaluating a flag" (stale, see site fixes) | 27-feature-flags/go/flag-service | replaced |
| 254 | 509 | Targeting and rollout | json · flagd | — | — | owner: shared-code |
| 256 | 511 | A kill switch | go · OpenFeature | 27 "The kill switch" | 27-feature-flags/go | matches |
| 264, 266, 267, 269 | 519, 521, 522, 524 | Appendix O code | — | — | — | owner: planner (App O) |

Counts for the 43 Go-owned code slides: replaced 26, matches 13, illustrative-ok 4.

## Version strings left in the deck

| String | Pin |
|---|---|
| Go 1.27.2 (cover notes) | Go 1.27.2 (modernization plan) |
| cenkalti/backoff v7 (chip) | v7.0.1 |
| sony/gobreaker v2 (chip) | v2.4.0 |
| golang-jwt v5 (chips) | v5.3.1 |
| Go 1.22 / 1.22+ (ServeMux, `PathValue`) | history: the release that added method patterns, not a pin |
| Apicurio `/apis/registry/v3` | API path; Apicurio 3.3.3 |

## Unresolved

- Resolved (user decision 6): the valet-key and claim-check slides follow `examples/12-security/go` (golang-jwt
  v5 HS256 ticket); minio-go is gone from the deck, and the site's Go valet-key tab is fixed to the same code
  (`site-fixes.md`, Go deck pass). Ops: `tools/amend_decisions.py` (tag `_amend`).
- Slide 1 notes (shared sentence) say "four appendices go deep"; the deck has many more. Fact fix belongs to the
  shared voice pass.
- Slide 45 (sldId 300, shared-code owner) carries the comment "scale FastAPI on concurrent requests".
- set_code on sldId 377: the box has no comment line, so new comment lines take the code colour (deck_edit log).

## Decision 7 amendment (vendor-neutral, 2026-10-12)

Generator: `tools/amend_vendor.py` (ops tagged `_vendor`, inserted just before the agenda op; run after `amend_decisions.py`).
Find strings and counts come from the pre-decision text copy (`verify_all.py` output of the edit files at 39a5b1e).

- Appendix S removed: the `clone_slide` ops `s0`–`s9` and every `set_*` op on `$s*` are dropped (71 ops); Appendix R (9 slides) stays. Agenda line "Appendix R · Example 05 on minikube" (same line count, so the agenda fit is unchanged); agenda notes, the title and overview notes and the R0/R1 notes no longer mention OpenShift Local ("carries over to any conformant Kubernetes cluster").
- Shared rewrites (where present in this deck): 4C's notes and bullet (CloudTrail, "S3 bucket open"); event-driven tools notes ("to S3" → "to an object store"); valet-key concept notes (one generic implementation sentence instead of S3/Azure/GCS/STS); strangler-fig IdPs (Keycloak, Dex instead of Auth0, Azure AD); zero-trust edge (Pomerium or OAuth2 Proxy in front of Keycloak instead of Google IAP, Cloudflare Access, AWS Verified Access; licence note Pomerium Apache-2.0, OAuth2 Proxy MIT); claim-check concept notes; choosing-the-pattern notes; glossary SAS entry and note removed; Appendix I gateway list without Apigee; Appendix M references: gRFC A6 instead of the AWS Builders' Library.
- Go: the valet-key and claim-check ops stay in `tools/amend_decisions.py` (decision 6) and were made vendor-neutral there: claim URI `https://objects.internal/`, notes without S3/Azure SAS/GCS. No set_* ops from decision 7 on slides 78 and 87.
- Kept (not vendor services): Heroku as the origin of the twelve-factor methodology (history), Google SRE Book (reference), gRPC / Google.Protobuf / Google.Rpc (open-source libraries), Netflix concurrency-limits (Apache-2.0 library), Red Hat UBI and the Red Hat brand frame.
- Figures (`replace_picture`, `tools/vendor_figures.py`): sldIds 332, 335. The valet-key figure named S3, Azure SAS, GCS and STS; the zero-trust figure listed Google IAP, Cloudflare Access and AWS Verified Access; both become the neutral site figures (`12-valet-key.png` with "object store" labels, `12-zero-trust.png`).
