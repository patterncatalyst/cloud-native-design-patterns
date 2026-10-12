# Designing-Cloud-Native-APIs-Quarkus — S12 manifest

> Amended 2026-10-12 for user decision 7 (vendor-neutral): see the last section, which supersedes the rows here
> on the valet-key and claim-check slides, the cloud-SDK pins and Appendix S.

272 slides at 8c86d61. Content ops: `lgtm-presentation/edits/Designing-Cloud-Native-APIs-Quarkus.json`
(assembled from the deck-exclusive voice rewrites and the content ops listed here; the shared voice,
Appendix O, image, language-agnostic code and R/S ops are documented in the README and their own
sections).

## Summary

- Version: Quarkus 3.35 (slide 1 notes) and Quarkus 3.32 (Appendix H code comment and notes) become
  Quarkus 3.40.1 (LTS, Java 25).
- Stack: Poetry comparison dropped (slide 14 notes), "corollary to Faust" becomes faust-streaming
  (slide 43 notes), RESTEasy Reactive becomes Quarkus REST (slide 130 notes).
- Code: 22 code boxes changed (21 `set_code`, one token replace in the Appendix H comment). The main drift was in Appendices K and L, where the deck showed
  reactive Mutiny variants (ReactiveRedisDataSource, Panache Reactive) while the site and
  `examples/25-caching/quarkus` use the blocking RedisDataSource; in slide 85, which used a
  programmatic SmallRye API that does not exist (`FaultToleranceProvider.bulkhead`); in the gRPC
  service base class (the example implements the generated Mutiny interface); in topic and
  identifier names (`revenue.by-merchant`, artifact `order-placed`, saga states `COMPLETED` /
  `COMPENSATED`); and in feature flags (the example registers the flagd provider itself).
- Notes: 8 notes rewritten where they described code that changed; 29 deck-exclusive voice and
  positional rewrites (`rewrites/30-deck-Quarkus.json` in the work tree, folded into the deck file).

## Changes

| Slide | sldId | Title | Category | Change |
|---|---|---|---|---|
| 1 | 256 | Designing Cloud-Native APIs | version, voice | notes: "on Quarkus 3.35" → "on Quarkus 3.40.1 (LTS, Java 25)"; em-dash sentence rewritten |
| 14 | 269 | A 12-factor Quarkus service | code, stack, voice | `PgPool` → `Pool`, readiness runs `SELECT 1` with `executeAndAwait()`; notes drop the Poetry comparison and "for free" |
| 17 | 272 | REST at the edge with Quarkus REST | code, voice | box = site 02 codetab (blocking Quarkus REST, all lines in Red Hat Mono again); notes: Uni sentence describes the blocking method, "for free" rewritten |
| 18 | 273 | gRPC for internal service-to-service calls | code | `implements Inventory` (generated Mutiny interface) instead of `extends InventoryGrpc.InventoryImplBase`; notes token |
| 24 | 279 | A composing resolver in SmallRye GraphQL | code | box = site 03 codetab |
| 29 | 284 | CQRS in practice | code | write side blocking (`Order create`), read side `findByIdOptional`, channel `order-created` → topic `order.created`; notes token |
| 32 | 287 | The outbox write | voice | notes: "deliberately" removed |
| 36 | 291 | Producing and consuming with Reactive Messaging | code, voice, positional | channel `order-placed` bound to topic `order.placed` (comment), as the examples; notes: ALL-CAPS and "the next slide" rewritten |
| 43 | 298 | A windowed aggregation with Kafka Streams | code, stack | output topic `revenue.by-merchant` (site 06 codetab, example 06); notes: topic name, faust-streaming |
| 46 | 301 | Workflows and Jobs divider | voice | notes em dashes |
| 55 | 310 | Gate breaking changes in CI with Maven | code, version | plugin `<version>3.3.3</version>`, artifact `order-placed`, file `order-placed.avsc` |
| 85 | 340 | SmallRye Fault Tolerance bulkheads | code, notes | `@AsynchronousNonBlocking` for the Uni method; per-tenant semaphore bulkhead from site 12 / example 12; notes rewritten |
| 96, 97 | 351, 352 | Glossary | voice | em-dash definitions use colons; AOT mentions Mandrel |
| 110 | 365 | Deprecating a field in SmallRye GraphQL | voice | notes em dashes |
| 113 | 368 | A WebSocket endpoint with WebSockets Next | voice | caption: "Declarative and easy" → "Declarative" |
| 117 | 372 | Binary framing with protobuf | code, positional | `sendBinaryAndAwait(Buffer.buffer(...))` as site 16; codec comment; notes: codec sentence, "the next slide" |
| 122 | 377 | A persisted saga state machine | code, positional, voice | status `COMPLETED`; notes: "next-but-one slide" and "for free" |
| 124 | 379 | Running compensations in reverse | code | terminal status `COMPENSATED` |
| 126 | 381 | Carrying context forward with Quarkus Flow | voice | notes: ALL-CAPS IS |
| 130 | 385 | REST errors with Quarkus REST | stack | notes: RESTEasy Reactive → Quarkus REST |
| 146 | 401 | Ports & adapters in code | voice | notes em dashes |
| 164 | 419 | Graceful shutdown in Quarkus | version, voice, positional | code comment and notes: Quarkus 3.32 → 3.40.1; ALL-CAPS NOT, "the next slide" |
| 168 | 423 | Appendix I divider | voice | notes "actually" |
| 188, 189 | 443, 444 | Camel route / Drools rule | positional, voice | notes "on the next slide", "actually" |
| 204, 205 | 459, 460 | Strangler fig | voice | "earns its keep", ALL-CAPS NOT |
| 206 | 461 | Content-based routing during migration | code, notes | chip, box = site 24 codetab (the old route lines ran to 150 columns), caption, notes |
| 208 | 463 | A decorating collaborator in Quarkus | code, notes | chip, box = site 24 codetab (blocking RedisDataSource), notes |
| 209 | 464 | Choosing the right migration pattern | voice | "genuinely" |
| 211 | 466 | Five things a cache earns you | voice | notes "very", "actually" |
| 213 | 468 | Cache-aside in Quarkus with Redis | code, notes | chip, box = site 25 cache-aside, notes |
| 215 | 470 | Read-through with @CacheResult | code | chip, box = site 25 read-through (resource reduced to a comment) |
| 217 | 472 | Write-through in Quarkus | code, notes | chip, box = site 25 write-through, caption, notes |
| 219 | 474 | Write-around in Quarkus | code, notes | chip, box = site 25 write-around, notes |
| 221 | 476 | Write-back with @Scheduled | code, notes | chip, box = site 25 write-back, notes |
| 222 | 477 | Refresh-ahead | voice | notes "actually" |
| 223 | 478 | Refresh-ahead in Quarkus | code, notes | chip, box = site 25 refresh-ahead, notes (also removes the positional "below") |
| 253 | 508 | Evaluating a flag | code | provider registered at StartupEvent, `OpenFeatureAPI.getInstance().getClient()`, SDK 1.23.0 / flagd 0.14.2, as example 27 |

## Code map

Status: `matches` (agrees with the site codetab and the example on library, API and identifiers),
`replaced` (rewritten by this manifest to match), `illustrative-ok` (no site or example counterpart;
API checked for Quarkus 3.40.1), or owned elsewhere.

| Slide | sldId | Title | Chip | Site codetab | Example | Status |
|---|---|---|---|---|---|---|
| 14 | 269 | A 12-factor Quarkus service | java · Quarkus + SmallRye Health | 01-cloud-native-principles §A twelve-factor service | 01/quarkus (custom /healthz, /readyz) | replaced (PgPool → Pool; site fix filed) |
| 17 | 272 | REST at the edge | java · Quarkus REST | 02-communications §REST at the edge | 01/quarkus OrderResource | replaced |
| 18 | 273 | gRPC for internal calls | protobuf + java · Quarkus gRPC | 02-communications §gRPC for internal calls | 02/quarkus InventoryService | replaced |
| 21 | 276 | Resilience as configuration | yaml · istio | | | owner: shared-code |
| 24 | 279 | A composing resolver | java · SmallRye GraphQL | 03-composition §The resolver makes it concrete | 03/quarkus gateway OrderGraphql | replaced |
| 29 | 284 | CQRS in practice | java · Quarkus REST + Panache + Reactive Messaging | none | none | illustrative-ok (after fix) |
| 32 | 287 | The outbox write | java · Hibernate Panache + Debezium | 04-data §The code, in your language | 04/quarkus OutboxResource | matches |
| 36 | 291 | Producing and consuming | java · SmallRye Reactive Messaging | 05-event-driven §Producing and consuming | 05/quarkus | replaced (channel order-placed; site fix filed) |
| 43 | 298 | A windowed aggregation | java · Quarkus Kafka Streams | 06-stream-processing §A windowed aggregation | 06/quarkus RevenueTopology | replaced |
| 45 | 300 | Scale on lag and on RPS | yaml · KEDA | | | owner: shared-code |
| 55 | 310 | Gate breaking changes in CI with Maven | xml · Maven + Apicurio | 09-api-registry (REST client tabs; no Maven tab) | 09 (curl, group orders, artifact order-placed) | replaced |
| 64 | 319 | Auto-instrument with Quarkus OpenTelemetry | java · Quarkus OpenTelemetry | 11-observability §Auto-instrument your service | 11/quarkus (OTLP 4317) | matches (site fix filed: Uni return) |
| 66 | 321 | Baggage in practice | java · Quarkus + OpenTelemetry baggage API | 11-observability §How correlation works (shorter) | none | illustrative-ok |
| 78 | 333 | S3 pre-signed URL | java · Quarkus REST + AWS SDK for Java v2 | 12-security §The valet key hands out direct access | 12/quarkus ValetKeyService (HMAC token) | matches (site and slide use the S3 presigner; the example uses HMAC tokens) |
| 83 | 338 | OPA Gatekeeper ConstraintTemplate | yaml · OPA Gatekeeper | | | owner: shared-code |
| 85 | 340 | SmallRye Fault Tolerance bulkheads | java · Quarkus + SmallRye Fault Tolerance | 12-security §Bulkhead | 12/quarkus BulkheadService | replaced |
| 87 | 342 | Producer mints claim, consumer fetches payload | java · Quarkus + quarkus-amazon-s3 + Reactive Messaging | 12-security §Claim-check (generic store) | none | illustrative-ok |
| 106 | 361 | Media-type versioning | java · Quarkus REST | none | none | illustrative-ok |
| 108 | 363 | Evolving a .proto safely | protobuf | | | owner: shared-code |
| 110 | 365 | Deprecating a field | java · SmallRye GraphQL | 15-appendix-b-versioning §GraphQL evolves | none | matches (record form of the same @Deprecated mechanism) |
| 113 | 368 | A WebSocket endpoint | java · Quarkus WebSockets Next | 16-appendix-c-websockets §A WebSocket endpoint | 16/quarkus WsEndpoint | matches |
| 117 | 372 | Binary framing with protobuf | protobuf + java | 16-appendix-c-websockets §Binary framing | 16/quarkus | replaced |
| 122 | 377 | A persisted saga state machine | java · Hibernate Panache | 17-appendix-d-sagas §Where the saga keeps its state | 17/quarkus SagaService | replaced |
| 124 | 379 | Running compensations in reverse | java · Hibernate Panache | 17-appendix-d-sagas §Compensation | 17/quarkus SagaService | replaced |
| 126 | 381 | Carrying context forward with Quarkus Flow | java · Quarkus Flow | none | none | illustrative-ok (io.quarkiverse.flow.Flow#descriptor() checked in quarkus-flow 1.2.0) |
| 130 | 385 | REST errors | java · Quarkus REST | 18-appendix-e-errors §REST | 18/quarkus | matches |
| 132 | 387 | gRPC errors with rich status | java · Quarkus gRPC | 18-appendix-e-errors §gRPC | 18/quarkus InventoryServiceImpl | matches (reactive form of the site's blocking tab) |
| 134 | 389 | Kafka retry + DLQ | java · SmallRye Reactive Messaging | 18-appendix-e-errors §Kafka | none | matches |
| 136 | 391 | GraphQL field errors | java · SmallRye GraphQL | 18-appendix-e-errors §GraphQL | none | matches |
| 146 | 401 | Ports & adapters in code | java · ports & adapters | 19-appendix-f-ddd-hexagonal §Hexagonal architecture | 19/quarkus | matches |
| 164 | 419 | Graceful shutdown in Quarkus | java · Quarkus | 21-appendix-h-shutdown §The application side | 21/quarkus | replaced (version in comment) |
| 165 | 420 | The Kubernetes side | yaml · Kubernetes | | | owner: shared-code |
| 175–177 | 430–432 | HAProxy / Nginx / Istio VirtualService | | | | owner: shared-code |
| 182, 183, 185 | 437, 438, 440 | Istio canary / header / Envoy | | | | owner: shared-code |
| 188 | 443 | A Camel route calling Drools | java · Quarkus + Camel | 22-appendix-i-l7-routing (line 360) | 22/quarkus | matches |
| 189 | 444 | A Drools rule | drl · Drools rules | 22-appendix-i-l7-routing (line 196) | none | matches |
| 194 | 449 | Istio east/west | yaml · Istio east/west | | | owner: shared-code |
| 206 | 461 | Content-based routing during migration | java · Quarkus REST + REST Client | 24-appendix-k §Content-based routing | 24/quarkus router | replaced |
| 208 | 463 | A decorating collaborator | java · Quarkus REST + REST Client + Redis + Reactive Messaging | 24-appendix-k §The decorating collaborator | 24/quarkus decorator | replaced |
| 213 | 468 | Cache-aside | java · Quarkus REST + Panache + Redis | 25-appendix-l §Cache-aside | 25/quarkus CacheResource | replaced |
| 215 | 470 | Read-through | java · Quarkus Cache + quarkus-redis-cache | 25-appendix-l §Read-through | 25/quarkus | replaced |
| 217 | 472 | Write-through | java · Quarkus REST + Panache + Redis | 25-appendix-l §Write-through | 25/quarkus | replaced |
| 219 | 474 | Write-around | java · Quarkus REST + Panache + Redis | 25-appendix-l §Write-around | 25/quarkus | replaced |
| 221 | 476 | Write-back | java · Quarkus + @Scheduled + Redis + Panache | 25-appendix-l §Write-back | 25/quarkus BackgroundTasks | replaced |
| 223 | 478 | Refresh-ahead | java · Quarkus + @Scheduled + Redis sorted set | 25-appendix-l §Refresh-ahead | 25/quarkus BackgroundTasks | replaced |
| 237 | 492 | Timeouts + deadlines | java · Quarkus + MicroProfile Fault Tolerance | 26-appendix-m §Timeouts | 26/quarkus | matches (reactive form) |
| 239 | 494 | Retry with backoff + jitter | java · Quarkus + MicroProfile Fault Tolerance | 26-appendix-m §Retry | 26/quarkus | matches |
| 241 | 496 | Circuit breaker + fallback | java · Quarkus + MicroProfile Fault Tolerance | 26-appendix-m §Circuit breaker | 26/quarkus CircuitBreaker | matches |
| 245 | 500 | Graceful shutdown (see App. H) | java · Quarkus + SmallRye Health | none (21 covers the config side) | 21/quarkus | illustrative-ok |
| 253 | 508 | Evaluating a flag | java · Quarkus | 27-appendix-n §Evaluating a flag | 27/quarkus OpenFeatureSetup, FlagResource | replaced (site fix filed) |
| 254 | 509 | Targeting and rollout live in config | json · flagd | | | owner: shared-code |
| 256 | 511 | A kill switch | java · Quarkus | 27-appendix-n §The kill switch | 27/quarkus | matches |
| 264, 266, 267, 269 | 519, 521, 522, 524 | Appendix O code slides | | | | owner: planner (App O) |

Counts (Quarkus-specific code slides, 43): replaced 21, matches 16, illustrative-ok 6 (slide 29 after its fix);
shared-code 13 boxes and App O 4 boxes are owned elsewhere (not counted).

## Version strings left in the deck

| String | Where | Pin |
|---|---|---|
| Quarkus 3.40.1 (LTS, Java 25) | slide 1 notes | MP: Quarkus 3.40.1, Java 25 |
| Quarkus 3.40.1 | slide 164 code comment and notes | MP: Quarkus 3.40.1 |
| apicurio-registry-maven-plugin 3.3.3 | slide 55 | MP: Apicurio 3.3.3 |
| OpenFeature SDK 1.23.0, flagd provider 0.14.2 | slide 253 | MP S2 evidence: OpenFeature sdk 1.23.0, flagd 0.14.2 |
| AWS SDK for Java v2 | slides 78, 87 chips and notes | major label, no pin |
| Bean Validation annotations | slide 17 notes | no version |

## Unresolved

- Slide 1 notes still say "re-examine it from twelve angles, then four appendices go deep on
  protocol internals, versioning, WebSockets and saga mechanics": the deck has thirteen sections and
  appendices A to S. The sentence is shared by the language decks, so the voice/shared pass owns it.
- Slide 66 (baggage) uses the key `tenant_id`; the site snippet uses `tenant.id`. No example
  exercises baggage, so the slide keeps `tenant_id` (caption and notes use it too).
- Slide 87 (claim check) uses S3 through quarkus-amazon-s3, the site uses a generic store; no
  example implements the claim check. Kept as illustrative.
- The Apicurio v3 dry-run fix in `site-fixes.md` affects all six codetabs of
  `_docs/09-api-registry.md`; it should be checked against a running 3.3.3 registry before the
  `docs(site)` commit.

## Decision 7 amendment (vendor-neutral, 2026-10-12)

Generator: `tools/amend_vendor.py` (ops tagged `_vendor`, inserted just before the agenda op; run after `amend_decisions.py`).
Find strings and counts come from the pre-decision text copy (`verify_all.py` output of the edit files at 39a5b1e).

- Appendix S removed: the `clone_slide` ops `s0`–`s9` and every `set_*` op on `$s*` are dropped (71 ops); Appendix R (9 slides) stays. Agenda line "Appendix R · Example 05 on minikube" (same line count, so the agenda fit is unchanged); agenda notes, the title and overview notes and the R0/R1 notes no longer mention OpenShift Local ("carries over to any conformant Kubernetes cluster").
- Valet key (sldId 333): title "Valet key — scoped, time-bound, op-restricted", chip `java · Quarkus REST + javax.crypto (HmacSHA256)`, `set_code` = `examples/12-security/quarkus/.../ValetKeyService.java` (`mint`, `verify`), 22 lines, notes rewritten (HMAC or HS256 ticket the service mints and verifies; generic object store). Code map row: matches `examples/12-security` (condensed excerpt, first comment line says so).
- Claim check (sldId 342): chip `java · Quarkus + SmallRye Reactive Messaging`, `set_code` = Emitter/`@Incoming` on channels bound to `order.documents`, generic `ObjectStore`, ticket from `ValetKeyService.mint`, 24 lines (box held 31); notes rewritten. Same lines as the site claim-check codetab after the site fix (`site-fixes.md`, decision-7 section). No example implements the claim check (illustrative, token from Example 12).
- Removed: AWS SDK for Java v2, quarkus-amazon-s3 (slides 78, 87); the S3 pre-signed URL, STS AssumeRole, Azure SAS, GCS framing.
- Shared rewrites (where present in this deck): 4C's notes and bullet (CloudTrail, "S3 bucket open"); event-driven tools notes ("to S3" → "to an object store"); valet-key concept notes (one generic implementation sentence instead of S3/Azure/GCS/STS); strangler-fig IdPs (Keycloak, Dex instead of Auth0, Azure AD); zero-trust edge (Pomerium or OAuth2 Proxy in front of Keycloak instead of Google IAP, Cloudflare Access, AWS Verified Access; licence note Pomerium Apache-2.0, OAuth2 Proxy MIT); claim-check concept notes; choosing-the-pattern notes; glossary SAS entry and note removed; Appendix I gateway list without Apigee; Appendix M references: gRFC A6 instead of the AWS Builders' Library.
- Kept (not vendor services): Heroku as the origin of the twelve-factor methodology (history), Google SRE Book (reference), gRPC / Google.Protobuf / Google.Rpc (open-source libraries), Netflix concurrency-limits (Apache-2.0 library), Red Hat UBI and the Red Hat brand frame.
- Figures (`replace_picture`, `tools/vendor_figures.py`): sldIds 332, 335, 427 (as Python). The valet-key figure named S3, Azure SAS, GCS and STS; the zero-trust figure listed Google IAP, Cloudflare Access and AWS Verified Access; both become the neutral site figures (`12-valet-key.png` with "object store" labels, `12-zero-trust.png`); the layered stack becomes the site `22-l7-layers.png`, as in the Go, C++ and .NET decks.
