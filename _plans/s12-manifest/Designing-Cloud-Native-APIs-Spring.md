# Designing-Cloud-Native-APIs-Spring — S12 changes

> Amended 2026-10-12 for user decision 7 (vendor-neutral): see the last section, which supersedes the rows here
> on the valet-key and claim-check slides, the cloud-SDK pins and Appendix S.

Deck: `lgtm-presentation/Designing-Cloud-Native-APIs-Spring.pptx` (276 slides at 8c86d61; sldIds run 4 ahead of
the Python deck from Appendix E on). Edit file: `lgtm-presentation/edits/Designing-Cloud-Native-APIs-Spring.json`
(assembled from the deck-exclusive voice rewrites and the content ops listed here; shared voice, Appendix O,
language-agnostic code, images, agenda and Appendices R and S come from the other parts of the manifest).

## Summary

- Versions: Spring Boot 4.0 → 4.1.1, Spring Framework 7.0 → 7.0.9, Java 25, Jackson 3 (cover notes); "Spring 4.0
  idiomatic style" and "Spring 6 RestClient" lose their stale version labels; the Temporal "1.35 in April 2026"
  claim is dropped (the SDK is at 1.40.0).
- Stack: gRPC on plain grpc-java (the examples do not use grpc-spring-boot-starter); outbox on `JdbcClient` +
  Jackson 3 (example 04); Kafka Streams topology as in example 06 (`JacksonJsonSerde`, `revenue.by-merchant`);
  tracing by the OpenTelemetry Java agent 2.32.0 with `@WithSpan` and the OpenTelemetry Baggage API (Micrometer
  Tracing is not used by the examples); Redis cache values with `RedisSerializer.json()` (Jackson 3) instead of
  `GenericJackson2JsonRedisSerializer`; topic `order-placed` → `order.placed`; Reactor Kafka noted as
  discontinued; Temporal `Saga.Options.Builder()`.
- Appendix D (user decision 6, 2026-10-12): the Spring Statemachine slides now present the hand-rolled saga
  orchestrator that `examples/17-sagas/spring-boot` runs (sagas row + saga_log, `JdbcClient`,
  `TransactionTemplate`, `SELECT ... FOR UPDATE`, resume at startup). Spring Statemachine appears once, as
  archived upstream, and is not offered as an option. Ops: `tools/amend_decisions.py` (tag `_amend`).
- Saga status names follow example 17 (`COMPLETED`, `COMPENSATED`).
- Voice: 37 deck-exclusive units rewritten (ban 5, positional 2, watch 30); none kept.

## Change table

| Slide | sldId | Title | Category | Change |
|---|---|---|---|---|
| 1 | 256 | Designing Cloud-Native APIs | version, notes | notes rewritten: Spring Boot 4.1.1, Framework 7.0.9, Java 25, Jackson 3, grpc-java, Kafka Streams, OTel Java agent, appendix list incl. R and S |
| 11 | 266 | The twelve-factor app, revisited | voice | subtitle em-dash pair (unit 600) |
| 14 | 269 | A 12-factor Spring Boot service | voice, version | notes: "Spring 4.0 idiomatic style … trivially testable" (unit 601) |
| 17 | 272 | REST at the edge with Spring Web | voice, version | notes: units 602, 603 ("for free"); "the Spring 4.0 idiomatic style" → "the idiomatic Spring style" |
| 18 | 273 | gRPC for internal service-to-service calls | stack, code, notes | chip `protobuf + java · Spring Boot 4 + grpc-java`; code = proto + example 02 grpc-java server; notes rewritten (Spring Integration 7.1 gateway mention removed) |
| 24 | 279 | A composing resolver in Spring for GraphQL | code | code = site 03 tab (`inventory.remaining(...)`) + `@BatchMapping` comment |
| 29 | 284 | CQRS in practice | positional | notes "from the next two slides" → "shown in the outbox write" |
| 32 | 287 | The outbox write | stack, code, notes, voice | chip `java · Spring Boot 4 + JdbcClient + Debezium CDC`; code = example 04 excerpt; notes rewritten (unit 604 also rewritten first) |
| 36 | 291 | Producing and consuming with Spring Kafka | code, stack, voice | `"order-placed"` → `"order.placed"` (2); notes: Reactor Kafka discontinued; unit 605 (AFTER) |
| 43 | 298 | A windowed aggregation with Kafka Streams | code, notes | code = example 06 excerpt; notes rewritten (window.seconds, BigDecimal, HALF_UP, revenue.by-merchant) |
| 57, 72 | 312, 327 | (metadata, security notes) | voice | "actually" (units 606, 607) |
| 64 | 319 | Auto-instrument with the OpenTelemetry Java agent | stack, code, notes | title, chip, code (site 11 tab), caption and notes: OTel Java agent 2.32.0 + `@WithSpan` |
| 66 | 321 | Baggage in practice | stack, code, notes | chip, code (OTel Baggage API filter + consumer), caption, notes |
| 85 | 340 | Resilience4j bulkheads in Spring Boot | voice, stack | notes unit 608: resilience4j-spring-boot4 starter named, em dashes |
| 96, 97 | 351, 352 | Glossary of acronyms | voice | em-dash pairs (units 609, 610) |
| 110 | 365 | Deprecating a field in Spring for GraphQL | voice | units 611 (IS), 612 (simply), 613 |
| 113 | 368 | A WebSocket endpoint with Spring WebSocket | voice | caption "Declarative and easy" (unit 614) |
| 117 | 372 | Binary framing with protobuf | voice | unit 615 ("critically for what comes next") |
| 46 | 301 | Workflows and Jobs divider | stack | notes: Appendix D sets the hand-rolled orchestrator (Example 17) beside Temporal; Spring State Machine dropped |
| 94 | 349 | References | stack | bullet: "Spring State Machine" dropped from the docs list |
| 121 | 376 | Where a saga keeps its state | stack | figure (names "Temporal / State Machine") → `17-saga-state.png` (site figure); notes: Example 17 runs the first option |
| 122 | 377 | A persisted saga state machine | code, voice | `setStatus("DONE")` → `"COMPLETED"`; notes unit 616 ("remember that … slide"); notes: "Temporal, in this appendix, … Example 17 runs the hand-rolled version with JdbcClient" |
| 124 | 379 | Running compensations in reverse | code | `setStatus("FAILED")` → `"COMPENSATED"` |
| 125 | 380 | When step B needs data only step A produced | stack | notes: Spring State Machine sentence → Example 17 stores each step's result in the JSONB context |
| 126 | 381 | Two ways to make a saga durable | stack | title "Two ways to keep a saga durable"; bullets and notes rewritten: hand-rolled orchestrator (Example 17) vs Temporal; one bullet and one notes paragraph state that Spring Statemachine is archived upstream and not offered (replaces the unit 617 and archived-repository ops) |
| 127 | 382 | Temporal: your saga is plain Java | voice | unit 618 |
| 128 | 383 | Temporal saga workflow + activity | code | `new Saga.Options()` → `new Saga.Options.Builder().build()` |
| 129 | 384 | The hand-rolled orchestrator: one row, one log, no extra cluster | stack | title, caption and notes rewritten; figure `63-appD-statemachine` → `17-sagas-architecture.png` (`examples/17-sagas/architecture.svg`, cairosvg 2.9.1, 1400 px); replaces the unit 619/620 and archived-repository ops |
| 130 | 385 | The hand-rolled orchestrator: one step per transaction | code, stack | title, chip `java · Spring Boot 4 + JdbcClient`, caption, notes; code = `SagaService.advance()` excerpt (22 lines, 94 columns; was 35 lines over the box capacity of 26, with lines over 95 columns) |
| 134 | 389 | REST errors with Spring 7 ProblemDetail | voice | unit 621 ("deliberately absent") |
| 136 | 391 | gRPC errors with rich status details | stack | chip `java · grpc-java + StatusProto` |
| 150 | 405 | Ports & adapters in code | voice | units 622, 623 |
| 172 | 427 | Appendix I divider notes | voice | unit 624 ("actually") |
| 192, 193 | 447, 448 | Camel route / Drools rule | voice | units 625, 626 |
| 202 | 457 | Appendix K divider | version | notes "RestClient (Spring 6+)" → "RestClient" |
| 208, 209 | 463, 464 | Strangler fig slides | voice | units 627 (earns its keep), 628 (NOT) |
| 210 | 465 | Content-based routing during migration | version, voice | code comment, caption and notes drop "Spring 6"; unit 629 (powerful) |
| 213 | 468 | Modular monolith with decomposed DBs | voice | units 630 (genuinely), 631 (powerful) |
| 217 | 472 | Cache-aside in Spring Boot | positional, voice | notes "(write-through, two slides later)" → "(write-through)"; "OUTSIDE" lowercased |
| 219 | 474 | Read-through with @Cacheable | stack, code, notes | code: `RedisSerializer.json()` (Jackson 3), 25 lines (fits the box); notes name the serializer; unit 632 |
| 222 | 477 | Write-around | voice | unit 633 |
| 223 | 478 | Write-around in Spring Boot | code, notes | code = site 25 tab (single write path); notes rewritten |
| 226, 227 | 481, 482 | Refresh-ahead | voice, positional | units 634 (BEFORE), 635 ("TTL is below" → "drops under") |

## Code map (every code slide)

Status: `matches` (agrees with the site codetab and, where one exists, the example), `replaced` (set_code in this
file), `illustrative-ok` (no site or example counterpart, or the example is a minimal variant; API checked current
for Spring Boot 4.1.1 / Framework 7.0.9 / Jackson 3), `owner: shared-code`, `owner: planner (App O)`.

| Slide | sldId | Title | Chip | Site codetab | Example file | Status |
|---|---|---|---|---|---|---|
| 14 | 269 | A 12-factor Spring Boot service | java · Spring Boot 4 + Actuator | 01 "A twelve-factor service" | examples/01-cloud-native-principles/spring-boot (minimal variant) | matches |
| 17 | 272 | REST at the edge with Spring Web | java · Spring Boot 4 + Spring Web | 02 "REST at the edge" | examples/02-communications/spring-boot/order-service/OrderController.java (minimal) | matches |
| 18 | 273 | gRPC for internal calls | protobuf + java · Spring Boot 4 + grpc-java | 02 "gRPC for internal calls" (stale, site fix) | examples/02-communications/spring-boot/inventory-service/InventoryServiceApplication.java | replaced |
| 21 | 276 | Resilience as configuration | yaml · istio | — | — | owner: shared-code |
| 24 | 279 | A composing resolver | java · Spring for GraphQL | 03 "The resolver makes it concrete" | examples/03-composition/spring-boot (gateway) | replaced |
| 29 | 284 | CQRS in practice | java · Spring Boot 4 + Spring Data JPA + Spring Kafka | — | — | illustrative-ok |
| 32 | 287 | The outbox write | java · Spring Boot 4 + JdbcClient + Debezium CDC | 04 "The code, in your language" (stale, site fix) | examples/04-data/spring-boot/order-service/OrderController.java | replaced |
| 36 | 291 | Producing and consuming with Spring Kafka | java · Spring Boot 4 + Spring Kafka | 05 "Producing and consuming" | examples/05-event-driven/spring-boot (order.placed) | replaced (topic) |
| 43 | 298 | A windowed aggregation with Kafka Streams | java · Spring Kafka Streams | 06 "A windowed aggregation" (stale, site fix) | examples/06-stream-processing/spring-boot/stream-processor/RevenueTopology.java | replaced |
| 45 | 300 | Scale on lag and on RPS | yaml · KEDA | — | — | owner: shared-code |
| 55 | 310 | Gate breaking changes in CI with Maven | xml · Maven + Apicurio | 09 uses RestClient + dry run | examples/09-api-registry (config only) | illustrative-ok (apicurio-registry-maven-plugin 3.x documents `test-update`, `/apis/registry/v3`) |
| 64 | 319 | Auto-instrument with the OpenTelemetry Java agent | java · Spring Boot 4 + OpenTelemetry Java agent | 11 "Auto-instrument your service" | examples/11-observability/spring-boot (agent 2.32.0) | replaced |
| 66 | 321 | Baggage in practice | java · Spring Boot 4 + OpenTelemetry API | 11 "How correlation works" (Baggage API) | — | replaced |
| 78 | 333 | S3 pre-signed URL | java · Spring Boot 4 + Spring Security + AWS SDK for Java v2 | 12 "The valet key" (same API) | examples/12-security ValetKeyService (HMAC variant) | illustrative-ok |
| 83 | 338 | OPA Gatekeeper ConstraintTemplate | yaml · OPA Gatekeeper | — | — | owner: shared-code |
| 85 | 340 | Resilience4j bulkheads | java · Spring Boot 4 + Resilience4j | 12 "Bulkhead" (programmatic Resilience4j) | examples/12-security BulkheadService (Semaphore variant) | illustrative-ok (resilience4j-spring-boot4 2.4.0 exists) |
| 87 | 342 | Claim-check producer/consumer | java · Spring Boot 4 + AWS SDK for Java v2 + Spring Kafka | 12 "Claim-check" | — | illustrative-ok |
| 106 | 361 | Media-type versioning | java · Spring Boot 4 + Spring Web | — | — | illustrative-ok (Framework 7 API versioning mentioned correctly) |
| 108 | 363 | Evolving a .proto safely | protobuf | — | — | owner: shared-code |
| 110 | 365 | Deprecating a field | graphql + java · Spring for GraphQL | 15 "GraphQL evolves" | — | illustrative-ok |
| 113 | 368 | A WebSocket endpoint | java · Spring Boot 4 + spring-boot-starter-websocket | 16 "A WebSocket endpoint" | examples/16-websockets/spring-boot/ws-server | matches |
| 117 | 372 | Binary framing with protobuf | protobuf + java · Spring WebSocket | 16 "Binary framing" + "Receiving and dispatching" | — | matches |
| 122 | 377 | A persisted saga state machine | java · Spring Data JPA | 17 "Where the saga keeps its state" | examples/17-sagas/spring-boot/saga-orchestrator (JdbcClient variant; statuses) | replaced (status) |
| 124 | 379 | Running compensations in reverse | java · Spring Data JPA | 17 "Compensation unwinds a failed saga" | examples/17-sagas (statuses) | replaced (status) |
| 128 | 383 | Temporal saga workflow + activity | java · io.temporal:temporal-sdk + Spring Boot | — | — | replaced (Saga.Options builder); otherwise illustrative-ok |
| 130 | 385 | The hand-rolled orchestrator: one step per transaction | java · Spring Boot 4 + JdbcClient | 17 "Where the saga keeps its state" | examples/17-sagas/spring-boot/saga-orchestrator/.../service/SagaService.java (`advance`) | replaced (excerpt: `lockRow`, `saveProgress`, `logStep`, `markStatus` name the condensed JdbcClient calls, as the first comment line says) |
| 134 | 389 | REST errors with Spring 7 ProblemDetail | java · Spring Boot 4 + Spring 7 ProblemDetail | 18 "REST" | examples/18-errors/spring-boot/order-service | matches |
| 136 | 391 | gRPC errors with rich status details | java · grpc-java + StatusProto | 18 "gRPC" | examples/18-errors/spring-boot/inventory-service (plain grpc-java) | matches (chip replaced) |
| 138 | 393 | Kafka retry + DLQ | java · Spring Boot 4 + Spring Kafka | 18 "Kafka" | — | matches |
| 140 | 395 | GraphQL field errors | java · Spring for GraphQL | 18 "GraphQL" | — | matches |
| 150 | 405 | Ports & adapters in code | java · ports & adapters in Spring Boot | 19 "Hexagonal architecture" | examples/19-ddd-hexagonal/spring-boot | matches |
| 168 | 423 | Graceful shutdown in Spring Boot | java · Spring Boot 4 | 21 "The application side" | examples/21-graceful-shutdown/spring-boot | matches |
| 169 | 424 | The Kubernetes side | yaml · Kubernetes | — | — | owner: shared-code |
| 179–189, 198 | 434, 435, 436, 441, 442, 444, 453 | HAProxy, nginx, Istio | haproxy.cfg / nginx.conf / yaml | — | — | owner: shared-code |
| 192 | 447 | A Camel route calling Drools | java · Spring Boot 4 + Apache Camel | 22 "Routing inside the app" (Camel) | examples/22-l7-routing/spring-boot (minimal router) | matches |
| 193 | 448 | A Drools rule | drl · Drools rules | 22 "Routing inside the app" (drl) | — | matches |
| 210 | 465 | Content-based routing during migration | java · Spring Boot 4 + Spring Web + RestClient | 24 "Content-based routing during migration" | examples/24-monolith-to-microservices/spring-boot/router | matches (comment label fixed) |
| 217 | 472 | Cache-aside with Redis | java · Spring Boot 4 + Spring Data JPA + Spring Data Redis | 25 "Cache-aside" | examples/25-caching/spring-boot (minimal) | matches |
| 219 | 474 | Read-through with @Cacheable | java · Spring Boot 4 + Spring Cache + Spring Data Redis | 25 "Read-through" | — | replaced |
| 223 | 478 | Write-around | java · Spring Boot 4 + Spring Cache + Spring Data Redis | 25 "Write-around" | — | replaced |
| 241 | 496 | Timeouts + deadlines | java · Spring Boot 4 + Resilience4j | 26 "Timeouts and deadline propagation" | examples/26-failure-modes (hand-rolled variant) | matches |
| 243 | 498 | Retry with backoff + jitter | java · Spring Boot 4 + Resilience4j | 26 "Retry" | — | matches |
| 245 | 500 | Circuit breaker + fallback | java · Spring Boot 4 + Resilience4j | 26 "Circuit breaker" | examples/26-failure-modes CircuitBreaker.java (hand-rolled) | matches |
| 249 | 504 | Graceful shutdown | java · Spring Boot 4 + Actuator | 21 | examples/21-graceful-shutdown | matches |
| 257 | 512 | Evaluating a flag | java · Spring Boot | 27 "Evaluating a flag" | examples/27-feature-flags/spring-boot FlagController (new-checkout) | matches |
| 258 | 513 | Targeting and rollout | json · flagd | — | — | owner: shared-code |
| 260 | 515 | A kill switch | java · Spring Boot | 27 "The kill switch" | examples/27-feature-flags (recommendations-enabled) | matches (chip is already Spring Boot) |
| 268–273 | 523, 525, 526, 528 | Appendix O code | json / bash / yaml | — | — | owner: planner (App O) |

Counts (Spring-owned code slides, 40 incl. 385): replaced 13, matches 20, illustrative-ok 7; shared-code 13
slides and App O 4 slides owned elsewhere.

## Version strings left in the deck (after all edits) and their pins

| String | Pin / source |
|---|---|
| Spring Boot 4.1.1 (slide 1 notes), "Spring Boot 4" (chips, notes) | MP: Spring Boot 4.1.1 |
| Spring Framework 7.0.9 (slide 1), "Spring 7" / "Spring Framework 7" (App E) | spring-boot-dependencies-4.1.1.pom `spring-framework.version` 7.0.9 |
| Java 25 | MP |
| Jackson 3 | MP; jackson-bom 3.1.5 in the Boot 4.1.1 BOM |
| OpenTelemetry Java agent 2.32.0 (slide 64 notes) | MP S3 evidence; examples/11 Containerfile |
| Bean Validation 3.1 (slide 17 notes) | Jakarta Validation 3.1 in the Boot 4.1.1 BOM (unchanged) |
| Apicurio `/apis/registry/v3` | MP: Apicurio 3.3.3 |
| "Spring Framework 6 introduced ProblemDetail" (slide 134 notes) | history, not a pin |
| AWS SDK for Java v2 | major label of the SDK (illustrative slides) |

## Unresolved

- Resolved (user decision 6): Appendix D presents the example's hand-rolled orchestrator. Spring Statemachine status,
  checked 2026-10-12: `github.com/spring-projects/spring-statemachine` is archived (read-only); the README
  ("Spring Statemachine is no longer maintained", commit 718d0705, 2026-07-03) links the announcement; the last
  commit before the archive is b78817dd, 2026-07-05 ("Create LICENSE prior to archive"); last release v4.0.2,
  2026-06-11; license Apache-2.0. spring.io, "Spring Cloud Data Flow commercial" (2025-04-21,
  https://spring.io/blog/2025/04/21/spring-cloud-data-flow-commercial): "Spring Statemachine 4.0.x will be the last
  open-source lines"; later releases go to Tanzu Spring customers only. The slides state this once (slide 126 bullet
  and notes); the deck offers no state-machine framework.
- Slides 122 and 124 (sldIds 377, 379) stay the illustrative JPA/EntityManager coordinator with example-17 status
  names; the example code itself is on slide 130.
- Slide 43 excerpt condenses the example's 14-line JSON mapping lambda into `toJson(window, acc)`; the manifest
  says "excerpt" in the first line. Slide 18 and 32 excerpts elide variable declarations (marked in comments).
- Unit 275 (slide 63 notes, "Spring — Micrometer Tracing + the OTel bridge, or the Java agent.") is a shared voice
  unit; it stays factually correct, so no Spring-only replace was added (it would collide with the voice rewrite).
- Images (e.g. `58-appI-camel-drools-sb`, `62-appD-temporal`) are the image-audit fork's; `63-appD-statemachine` and
  the Spring copy of `33-appD-state-options` are replaced here (decision 6).

## Decision 7 amendment (vendor-neutral, 2026-10-12)

Generator: `tools/amend_vendor.py` (ops tagged `_vendor`, inserted just before the agenda op; run after `amend_decisions.py`).
Find strings and counts come from the pre-decision text copy (`verify_all.py` output of the edit files at 39a5b1e).

- Appendix S removed: the `clone_slide` ops `s0`–`s9` and every `set_*` op on `$s*` are dropped (71 ops); Appendix R (9 slides) stays. Agenda line "Appendix R · Example 05 on minikube" (same line count, so the agenda fit is unchanged); agenda notes, the title and overview notes and the R0/R1 notes no longer mention OpenShift Local ("carries over to any conformant Kubernetes cluster").
- Valet key (sldId 333): title "Valet key — scoped, time-bound, op-restricted", chip `java · Spring Boot 4 + javax.crypto (HmacSHA256)`, `set_code` = `examples/12-security/spring-boot/.../ValetKeyService.java` (`mint`, `verify`), 22 lines, notes rewritten (HMAC or HS256 ticket the service mints and verifies; generic object store). Code map row: matches `examples/12-security` (condensed excerpt, first comment line says so).
- Claim check (sldId 342): chip `java · Spring Boot 4 + Spring Kafka`, `set_code` = KafkaTemplate/`@KafkaListener`, generic `ObjectStore`, ticket from `ValetKeyService.mint`, 22 lines (box held 33); notes rewritten. Same lines as the site claim-check codetab after the site fix (`site-fixes.md`, decision-7 section). No example implements the claim check (illustrative, token from Example 12).
- Removed: AWS SDK for Java v2 (slides 78, 87); the S3 pre-signed URL, STS AssumeRole, Azure SAS, GCS framing.
- Shared rewrites (where present in this deck): 4C's notes and bullet (CloudTrail, "S3 bucket open"); event-driven tools notes ("to S3" → "to an object store"); valet-key concept notes (one generic implementation sentence instead of S3/Azure/GCS/STS); strangler-fig IdPs (Keycloak, Dex instead of Auth0, Azure AD); zero-trust edge (Pomerium or OAuth2 Proxy in front of Keycloak instead of Google IAP, Cloudflare Access, AWS Verified Access; licence note Pomerium Apache-2.0, OAuth2 Proxy MIT); claim-check concept notes; choosing-the-pattern notes; glossary SAS entry and note removed; Appendix I gateway list without Apigee; Appendix M references: gRFC A6 instead of the AWS Builders' Library.
- Kept (not vendor services): Heroku as the origin of the twelve-factor methodology (history), Google SRE Book (reference), gRPC / Google.Protobuf / Google.Rpc (open-source libraries), Netflix concurrency-limits (Apache-2.0 library), Red Hat UBI and the Red Hat brand frame.
- Figures (`replace_picture`, `tools/vendor_figures.py`): sldIds 332, 335, 431 (Appendix I layered stack, Apigee). The valet-key figure named S3, Azure SAS, GCS and STS; the zero-trust figure listed Google IAP, Cloudflare Access and AWS Verified Access; both become the neutral site figures (`12-valet-key.png` with "object store" labels, `12-zero-trust.png`); the layered stack becomes the site `22-l7-layers.png`, as in the Go, C++ and .NET decks.
