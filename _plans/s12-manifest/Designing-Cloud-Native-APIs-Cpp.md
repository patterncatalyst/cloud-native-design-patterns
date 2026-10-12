# C++ deck: Designing-Cloud-Native-APIs-Cpp

> Amended 2026-10-12 for user decision 7 (vendor-neutral): see the last section, which supersedes the rows here
> on the valet-key and claim-check slides, the cloud-SDK pins and Appendix S.

272 slides at 8c86d61; gains Appendix R only (agenda, R slides: planner, `ops-90-rs`). Sources of
the deck-specific edits: `work/rewrites/30-deck-Cpp.json` (124 voice/positional/stack rewrites of
the deck-exclusive sentences) and `work/ops-30-deck/Designing-Cloud-Native-APIs-Cpp.json` (93
ops), both merged into `lgtm-presentation/edits/Designing-Cloud-Native-APIs-Cpp.json` by the
builder. Generator: `fork-cpp/gen_cpp.py` in the S12 scratchpad.

## Summary

- Kafka moves from modern-cpp-kafka (archived upstream) to librdkafka's C++ API (`rdkafka++`) on
  every slide, chip and note: 3 code slides rewritten (36, 43, 134), 2 code slides with a new
  Kafka block (29, 87), the dispatcher and decorator (189, 208) on `produce_to`, and 20 prose
  mentions in bullets, titles, subtitles, captions and notes.
- Toolchain on the title-slide notes: GCC 15 (gcc-toolset-15 on ubi10/ubi:10.2), CMake 4.4.4,
  Ninja 1.13.2, Conan 2.33.0, static libstdc++ on ubi10/ubi-minimal, libpq direct, Docker Engine.
- C++20 → C++23 for the deck's baseline: chips `c++20` → `c++23` (85, 164, 245), `cpp · C++20`
  replaced (253, 256), closing slide "C++ 20 / 23" → "C++23" (95). Feature-origin mentions become
  "(since C++20)" (std::stop_token, std::jthread, std::counting_semaphore).
- Code agrees with `examples/*/cpp/` on library, API and identifiers: outbox on raw libpq (32),
  stream processor on `MerchantWindows` and commit-after-delivery (43), saga lifecycle machine
  and `compensation_order` (122, 124, 126), synchronous hexagonal ports and `PlaceOrderUseCase`
  (146), graceful shutdown with an atomic flag, `InFlightGuard` and `registerBeginningAdvice`
  (164, 245), tenant router on Drogon's `HttpClient` (206), flagd gRPC `ResolveBoolean` (253,
  256), OTLP/HTTP exporter (64), Apicurio 3.3's HTTP 400 for an incompatible schema (55), the
  AWS SDK `GeneratePresignedUrl(bucket, key, method, expiry)` signature (78), `httplib::`
  namespace (237).
- Voice: all 136 deck-exclusive units handled: 124 rewritten, 8 folded into rewritten notes
  (units 0, 26, 36, 37, 38, 99, 101, 129 on sldIds 256, 291, 298, 377, 379, 419), 4 kept (ledger).
  Positional phrases outside the units fixed on 278, 329, 368, 369, 441, 483 notes and the 494
  code comment; "turn 1" process language removed (294, 331 notes).

## Change table

Slide numbers are those at 8c86d61.

| Slide | sldId | Title | Category | Change |
|---|---|---|---|---|
| 1 | 256 | Designing Cloud-Native APIs | stack, version | notes rewritten: toolchain pins, rdkafka++, libpq, Docker Engine, C++23 (folds unit 0) |
| 4, 5, 6 | 259–261 | Setting up / running example | voice | units 3–6 |
| 8 | 265 | Design-first | voice | bullet unit 7; notes units 8, 9 |
| 9–12 | 266–269 | Twelve factors | voice, positional | units 10–13 |
| 13 | 268 | Twelve factors, mapped | stack | notes: Kafka via librdkafka (rdkafka++) |
| 16 | 271 | Pick the protocol | stack, voice | notes unit 14 (rdkafka++) |
| 18, 19 | 273, 274 | gRPC / sync vs async | voice, stack | units 15, 16; notes: process-scoped librdkafka producer |
| 21 | 276 | Resilience as configuration | voice | notes unit 17 (code: shared-code fork) |
| 23 | 278 | One query, many services | positional | notes: "next two slides" removed |
| 24, 25 | 279, 280 | Composition | voice, positional | units 18, 20 |
| 28 | 283 | CQRS | voice | unit 21 |
| 29 | 284 | CQRS in practice | code, stack | set_code: projection on rdkafka++, outbox topic `order.placed` (was `order.created`); notes unit 22 |
| 30 | 285 | Log tailing | voice | unit 24 |
| 32 | 287 | The outbox write | code, notes | set_code: libpq excerpt from example 04; set_notes |
| 35 | 290 | Event backbone | stack | notes: RdKafka::Producer |
| 36 | 291 | Producing and consuming | stack, code, notes | title, chip `c++ · rdkafka++`, set_code (rdkafka++, group per example), set_notes (folds unit 26) |
| 37, 38, 40 | 292, 293, 295 | Event-driven | voice | units 29, 30, 31, 33 (27 kept) |
| 39 | 294 | Tools landscape | voice | "turn 1" removed (unit 32 kept: survey term) |
| 42 | 297 | Derive new streams | stack, voice, positional | notes: librdkafka; units 34, 35 |
| 43 | 298 | In-process windowed aggregation | code, stack, notes | chip, set_code from example 06, caption, set_notes (folds units 36–38) |
| 44 | 299 | KEDA | voice | unit 39 |
| 48 | 303 | Choosing between the two | stack | bullet: rdkafka++ |
| 51 | 306 | Four planes | voice | unit 42 |
| 54 | 309 | Apicurio | voice | unit 43 |
| 55 | 310 | Gate breaking changes in CI | code | Apicurio 3.3 rejects with HTTP 400 (comment and status check) |
| 58 | 313 | Catalog | voice | unit 44 |
| 60–64 | 315–319 | Observability | voice, stack, code | units 45–49; 318 bullet and notes: librdkafka; 319 code: OTLP/HTTP exporter |
| 67–69 | 322–324 | Correlation, sampling | voice | units 50–53 |
| 73–76 | 328–331 | Security | voice | units 54–62; 331 notes "turn 1" removed |
| 74 | 329 | Seven patterns | positional | notes: "in the next slides" removed |
| 78 | 333 | S3 pre-signed URL | code, voice | set_code: SDK signature, Python leftover comment removed; notes unit 63 |
| 79–83 | 334–338 | Strangler, zero-trust, policy | voice, positional | units 65–69 |
| 84, 85 | 339, 340 | Bulkhead | voice, version | unit 70, 71; chip `c++23`, code comment and notes "(C++20)" wording |
| 87 | 342 | Claim-check code | code, stack, voice | chip, set_code (rdkafka++), notes librdkafka; unit 72 |
| 88 | 343 | Choosing the pattern | voice | units 73, 75 |
| 91, 92 | 346, 347 | Anti-patterns | voice | units 76–78 |
| 93 | 348 | In closing | stack | bullet and notes: librdkafka |
| 95 | 350 | Thank you | version | "C++ 20 / 23" → "C++23" |
| 96, 97 | 351, 352 | Glossary | voice | units 81, 84, 85 |
| 99, 102, 103 | 354, 357, 358 | Appendix A | voice, stack | units 88, 90; 357 bullet and notes: rdkafka++ |
| 113–119 | 368–374 | Appendix C | voice, positional, stack | units 93–98; 368, 369 notes positional; 371 notes and 374 bullet: rdkafka++ |
| 122 | 377 | Saga state machine | code, notes | set_code (example 17 Lifecycle machine), caption, set_notes (folds unit 99) |
| 123 | 378 | Compensating transactions | voice | unit 100 |
| 124 | 379 | Compensations in reverse | code, notes | set_code (compensation_order), set_notes (folds unit 101) |
| 126 | 381 | Context forward | code | set_code (jsoncpp context per example 17); notes: jsoncpp |
| 128, 130, 134 | 383, 385, 389 | Appendix E | voice, stack, code | units 102–104; 389 title, chip, set_code (site 18 C++ tab, rdkafka++) |
| 141–146 | 396–401 | Appendix F | voice, code | units 106–112; 401 set_code (example 19 ports and use case), caption, notes `PlaceOrderUseCase` |
| 150–158 | 405–413 | Appendix G | voice, positional | units 113–122 |
| 159–162 | 414–417 | Appendix H | voice, version | units 123–128; 415 bullet and 417 notes: stop_token wording, request_stop not in the handler |
| 164 | 419 | Graceful shutdown in Drogon | code, version, notes | title, chip `c++23`, set_code (example 21), caption, set_notes (folds unit 129) |
| 167 | 422 | Shutdown checklist | code, version | handler bullet (flag only), "(since C++20)" |
| 168–175 | 423–430 | Appendix I | voice, positional | units 130–140 |
| 178, 180 | 433, 435 | TLS, sticky sessions | voice | units 142, 145 |
| 186, 187 | 441, 442 | Business-rule routing | voice, positional, stack | units 147–149; 441 notes positional; 442 subtitle and notes: librdkafka |
| 189 | 444 | The dispatcher | code, stack | set_code (site 22 C++ tab, `produce_to`) |
| 191, 192 | 446, 447 | L7 pitfalls, east/west | voice, positional | units 152, 153 |
| 201–204 | 456–459 | Appendix K | voice | units 154–156 |
| 206 | 461 | Content-based routing | code | set_code (example 24 router, Drogon HttpClient), caption, notes |
| 207, 208 | 462, 463 | Decorator | stack, code | notes librdkafka; set_code (rdkafka++ `produce_to`, synchronous sw/redis++), caption, notes |
| 215, 222, 224 | 470, 477, 479 | Appendix L | voice | units 162, 163, 165 |
| 221 | 476 | Write-back | version | notes: "leans on the standard library" |
| 228 | 483 | Failure taxonomy | positional | notes: "the matrix on slide 247" → "the failure-mode matrix" |
| 231–248 | 486–503 | Appendix M | voice, version | units 170–178 (171 kept); 497 notes "(since C++20)" |
| 237 | 492 | Timeouts | code | `cpp_httplib::` → `httplib::` |
| 239 | 494 | Retry | positional | code comment "(next slide)" removed |
| 245 | 500 | Shutdown recap | code, version | chip, set_code (aligned with 164), caption, notes |
| 253 | 508 | Evaluating a flag | code, stack, notes | chip `c++ · flagd gRPC`, set_code (example 27), set_notes |
| 256 | 511 | A kill switch | code, stack | chip `c++ · flagd`, set_code (example 27 /recommendations) |

## Code map (every code slide)

Status: `matches` (agrees with the site codetab and the example on library, API, identifiers),
`replaced` (set_code in this manifest), `edited` (token replace in the box),
`illustrative-ok` (teaching code with no example counterpart; API checked against the locked
library versions). Teaching wrappers (`PgTxn`, `Task<>` handlers, `json_response`) appear in the
site codetabs too and are accepted as illustration.

| Slide | sldId | Title | Chip | Site codetab | Example | Status |
|---|---|---|---|---|---|---|
| 14 | 269 | A 12-factor Drogon service | c++ · Drogon | `_docs/01` twelve-factor | `01-cloud-native-principles/cpp/src/main.cpp` | matches |
| 17 | 272 | REST at the edge with Drogon | c++ · Drogon | `_docs/02` REST at the edge | `02-communications/cpp/order-service` | matches (deck adds the `list` handler) |
| 18 | 273 | gRPC for internal calls | c++ · gRPC | `_docs/02` gRPC | `02-communications/cpp/inventory-service` (`InventoryServiceImpl`) | matches (deck name `InventoryServicer`, illustrative) |
| 21 | 276 | Resilience as configuration | yaml · istio | — | — | owner: shared-code |
| 24 | 279 | Composing resolver | c++ · cppgraphqlgen | `_docs/03` resolver | `03-composition/cpp/gateway` | matches |
| 29 | 284 | CQRS in practice | c++ · libpq + kafka | `_docs/05` local views | `05-event-driven/cpp` (rdkafka++) | replaced |
| 32 | 287 | The outbox write | c++ · libpq | `_docs/04` (stale, site fix) | `04-data/cpp/order-service/src/main.cpp` | replaced |
| 36 | 291 | Producing and consuming | c++ · rdkafka++ | `_docs/05` Producing and consuming | `05-event-driven/cpp/{order-service,notification-consumer}` | replaced |
| 43 | 298 | Windowed aggregation | c++ · rdkafka++ | `_docs/06` (stale, site fix) | `06-stream-processing/cpp/stream-processor` | replaced |
| 45 | 300 | Scale on lag and RPS | yaml · KEDA | — | — | owner: shared-code |
| 55 | 310 | Gate breaking changes in CI | c++ · Apicurio | `_docs/09` (cpr) | none (09 is configuration only) | edited (HTTP 400) |
| 64 | 319 | Auto-instrument Drogon | c++ · OpenTelemetry | `_docs/11` (stale, site fix) | `11-observability/cpp/*/src/telemetry.hpp` | edited (OTLP/HTTP) |
| 66 | 321 | Baggage in practice | c++ · OpenTelemetry | `_docs/11` correlation | none | illustrative-ok (opentelemetry-cpp 1.26 baggage API) |
| 78 | 333 | S3 pre-signed URL | c++ · AWS SDK | `_docs/12` valet key | `12-security/cpp` uses jwt-cpp tokens | replaced (illustrative pattern; SDK call fixed) |
| 83 | 338 | OPA Gatekeeper | yaml · Gatekeeper | — | — | owner: shared-code |
| 85 | 340 | Per-tenant bulkheads | c++23 · semaphore | `_docs/12` bulkhead | none | edited (comment), illustrative-ok |
| 87 | 342 | Claim-check | c++ · S3 + rdkafka++ | `_docs/12` (stale, site fix) | none | replaced |
| 106 | 361 | Media-type versioning | c++ · Drogon | none | none | illustrative-ok |
| 108 | 363 | Evolving a .proto | protobuf | — | — | owner: shared-code |
| 110 | 365 | Deprecating a field | graphql + c++ | `_docs/15` GraphQL | none | matches (deck adds a span attribute) |
| 113 | 368 | WebSocket endpoint | c++ · Drogon | `_docs/16` endpoint | `16-websockets/cpp/ws-server` (`WsCtrl`, `/ws`) | matches site; illustrative names |
| 117 | 372 | Binary framing | protobuf + c++ | `_docs/16` binary framing | none | matches |
| 122 | 377 | Saga state machine | c++ · boost::sml | `_docs/17` saga state | `17-sagas/cpp/saga-orchestrator/src/saga_machine.hpp` | replaced |
| 124 | 379 | Compensations in reverse | c++ · boost::sml | `_docs/17` (stale, site fix) | `17-sagas/cpp/.../main.cpp` | replaced |
| 126 | 381 | Context forward | c++ · boost::sml | none | `17-sagas/cpp/.../main.cpp` | replaced (B reading A's output shown as the pattern on the example's context) |
| 130 | 385 | REST errors | c++ · Drogon | `_docs/18` REST | `18-errors/cpp` | matches |
| 132 | 387 | gRPC rich status | c++ · gRPC | `_docs/18` gRPC | `18-errors/cpp/inventory-service` | matches |
| 134 | 389 | Kafka retry + DLQ | c++ · rdkafka++ | `_docs/18` Kafka | none | replaced (site tab) |
| 136 | 391 | GraphQL field errors | c++ · cppgraphqlgen | `_docs/18` GraphQL | none | matches |
| 146 | 401 | Ports & adapters | c++ · hexagonal | `_docs/19` (stale, site fix) | `19-ddd-hexagonal/cpp/order-service/src/domain` | replaced |
| 164 | 419 | Graceful shutdown | c++23 · Drogon | `_docs/21` (stale, site fix) | `21-graceful-shutdown/cpp/src/main.cpp` | replaced |
| 175 | 430 | HAProxy | haproxy.cfg | — | — | owner: shared-code |
| 176 | 431 | Nginx | nginx.conf | — | — | owner: shared-code |
| 177 | 432 | Istio VirtualService | yaml · Istio | — | — | owner: shared-code |
| 182 | 437 | Canary | yaml · Istio | — | — | owner: shared-code |
| 183 | 438 | Header-based steering | yaml · Istio | — | — | owner: shared-code |
| 185 | 440 | Header injection | yaml · Istio | — | — | owner: shared-code |
| 188 | 443 | The rules: Lua | lua | `_docs/22` Lua | `22-l7-routing/cpp/router-service/routing.lua` (simpler `route(order, rules)`) | matches site; illustrative-ok |
| 189 | 444 | The dispatcher | c++ · Drogon + sol2 | `_docs/22` dispatcher | `22-l7-routing/cpp/router-service` | replaced (site tab) |
| 194 | 449 | Istio east/west | yaml · Istio | — | — | owner: shared-code |
| 206 | 461 | Content-based routing | c++ · Drogon | `_docs/24` (stale, site fix) | `24-monolith-to-microservices/cpp/router` | replaced |
| 208 | 463 | Decorating collaborator | c++ · Drogon | `_docs/24` (stale, site fix) | `24-monolith-to-microservices/cpp/decorator` | replaced |
| 213 | 468 | Cache-aside | c++ · Drogon | `_docs/25` cache-aside | `25-caching/cpp/cache-service` | matches |
| 215 | 470 | Read-through | c++ · template | `_docs/25` read-through | `25-caching/cpp/cache-service` | matches |
| 217 | 472 | Write-through | c++ · Drogon | `_docs/25` write-through | `25-caching/cpp/cache-service` | matches (deck adds a fast variant) |
| 219 | 474 | Write-around | c++ · Drogon | `_docs/25` write-around | `25-caching/cpp/cache-service` | matches |
| 221 | 476 | Write-back | c++ · jthread | `_docs/25` write-back | `25-caching/cpp/cache-service` | matches |
| 223 | 478 | Refresh-ahead | c++ · jthread | `_docs/25` refresh-ahead | `25-caching/cpp/cache-service` | matches |
| 237 | 492 | Timeouts + deadlines | c++ · gRPC | `_docs/26` timeouts | `26-failure-modes/cpp/edge-service` (libcurl) | edited (`httplib::`) |
| 239 | 494 | Retry with backoff | c++ | `_docs/26` retry | `26-failure-modes/cpp/edge-service` | edited (comment) |
| 241 | 496 | Circuit breaker | c++ · atomic | `_docs/26` circuit breaker | `26-failure-modes/cpp/edge-service` | matches |
| 245 | 500 | Shutdown recap | c++23 · Drogon | `_docs/21` (stale) | `21-graceful-shutdown/cpp` | replaced |
| 253 | 508 | Evaluating a flag | c++ · flagd gRPC | `_docs/27` (stale, site fix) | `27-feature-flags/cpp/flag-service` | replaced |
| 254 | 509 | flagd targeting | json · flagd | — | — | owner: shared-code |
| 256 | 511 | A kill switch | c++ · flagd | `_docs/27` (stale, site fix) | `27-feature-flags/cpp/flag-service` | replaced |
| 264, 266, 267, 269 | 519, 521, 522, 524 | Appendix O | json, bash, yaml | `_docs/28` | `28-newman` | owner: planner (App O) |

Counts over the 43 C++-owned code slides: replaced 21, edited 5, matches 13, illustrative-ok 4
(321, 340, 361, 443; 333 and 340 are also counted under replaced/edited). Owned by others: 12
shared-code slides, 4 Appendix O slides.

## Version strings left in the deck after the edits

| String | Where | Pin |
|---|---|---|
| C++23 | chips, closing slide, title notes | C++23 (`CMAKE_CXX_STANDARD 23`) |
| GCC 15 / gcc-toolset-15, CMake 4.4.4, Ninja 1.13.2, Conan 2.33.0 | slide 1 notes | MP S7 |
| ubi10/ubi:10.2, ubi10/ubi-minimal | slide 1 notes | MP pins table (builder ubi10/ubi:10.2-1791444044, runtime ubi10/ubi-minimal:10.2-1791444377) |
| librdkafka 2.14.2 | slide 36 notes | MP S7 (ConanCenter newest; upstream 2.16.0) |
| .NET 10 | slide 1 notes (sibling decks) | .NET 10.0.12 |
| since C++20 (stop_token, jthread, counting_semaphore), C++17 (PMR) | slides 85, 160, 167, 221, 242, 352 | history, not pins |
| Apicurio `/apis/registry/v3` | slide 55 code | Apicurio 3.3.3 |
| TLS 1.3, RFC 9457, 10.1.0.10/11 | various | not software pins |

## Watch-tier hits kept (deck-exclusive)

| Unit | Slide | Pattern | Reason |
|---|---|---|---|
| 27 | 37 notes | silently | machine-subject (a producer corrupts consumers) |
| 32 | 39 title | landscape | survey-term |
| 91 | 107 notes | silently | machine-subject (an old client misreads data) |
| 171 | 232 notes | lies | machine-subject (gray failure) |

Remaining watch hits in the C++ text after these edits sit in sentences shared with other decks
(voice forks) or are notes paragraphs whose em dashes are spread over sentences with one dash
pair at most (`notes-paragraph`).

## Reference and library verification (user decision 6)

Checked 2026-10-12 with the GitHub API (`gh api repos/...`, releases, commits, contents), the live sites (HTTP 200)
and, for the compendiums, a clone of each repository. Locked-stack libraries (CLAUDE.md) are not repeated here.
Every rewrite is a `replace` op tagged `_amend` in `lgtm-presentation/edits/Designing-Cloud-Native-APIs-Cpp.json`,
inserted before the agenda and Appendix R ops; sources in `tools/amend_decisions.py` (`cpp_pairs`).

### Projects and libraries

| Named in the deck | Exists? Official URL | Maintained (2026-10-12) | License | Verdict and action |
|---|---|---|---|---|
| "cpp-stateless compendium" / "cpp-stateless deck" / "cpp-statelessness compendium" (28 mentions) | yes: the author's companion project `github.com/patterncatalyst/cpp-statelessness`, site https://patterncatalyst.github.io/cpp-statelessness/ (Doc 01–11) | last commit 2026-10-11 | Apache-2.0 (`LICENSE`; GitHub shows NOASSERTION) | kept, renamed to its real name **cpp-statelessness** and cited by Doc number with the chapter URL. The deck's "§N" numbers do not match the site's chapters (for example "§6 PMR" is Doc 03, "§3 Conan" is Doc 11, "§11 stdout" is Doc 08), so each reference names the Doc that holds the content; claims the compendium does not make are rewritten (table below) |
| "cpp-container compendium" (1, references notes) | yes: `github.com/patterncatalyst/cpp-container-optimization-tutorial`, site https://patterncatalyst.github.io/cpp-container-optimization-tutorial/ | last commit 2026-10-11 | Apache-2.0 | kept, named "the C++ container optimization tutorial" with its URL (slide 94) |
| hedge-cpp (slide 137 notes) | no retry library by that name: `github.com/photex/hedge-cpp` is a half-edge mesh experiment (3 stars, no release) | last push 2019-09-23 | none | dropped: "no widely adopted C++ retry library exists; write capped exponential backoff with jitter, as Example 26 does (`retry_with_backoff`)" |
| Hystrix-CPP (slide 240 notes) | only `github.com/dragosbucur2001/hystrix-cpp` (0 stars, no description, no release) | last push 2023-06-06 | none | dropped |
| breaker-cpp (slide 240 notes) | no such repository (GitHub search returns unrelated brick-breaker games) | — | — | dropped: "C++ has no widely adopted circuit-breaker library; Example 26 hand-rolls one (`CircuitBreaker` in edge-service)" |
| openapi-generator-cli, `cpp-pistache-server` (slide 10 bullet) | yes: OpenAPI Generator `github.com/OpenAPITools/openapi-generator`, generator docs list `cpp-pistache-server` and `cpp-httplib-server` as STABLE server generators; Pistache `github.com/pistacheio/pistache` | generator v7.26.0 (2026-10-06); Pistache last commit 2026-07-11, last release v0.4.25 (2024-12-21) | Apache-2.0 / Apache-2.0 | "template is most mature" is not verifiable: rewritten to "stable C++ server generators: cpp-pistache-server, cpp-httplib-server; none targets Drogon" |
| cpp-httplib (slides 16, 17, 55, 207, 237, 242) | yes: `github.com/yhirose/cpp-httplib` | v0.60.1 (2026-10-08) | MIT | kept; slide 55 notes name the repository (and drop "picked back in §2") |
| libcurl (slides 55, 63) | yes: `github.com/curl/curl`, https://curl.se; used by `examples/26-failure-modes/cpp` | curl 8.22.0 (2026-09-02) | curl license (MIT-style) | kept |
| AWS SDK for C++ (slides 78, 87, 89, 93) | yes: `github.com/aws/aws-sdk-cpp` | 1.11.909 (2026-10-09) | Apache-2.0 | removed by decision 7 (a vendor cloud SDK); slides 78/87 follow `examples/12-security/cpp` (jwt-cpp), 89/93 name jwt-cpp |
| OpenTelemetry C++ SDK (slide 60 notes "BSL/Apache 2.0") | yes: `github.com/open-telemetry/opentelemetry-cpp` | v1.29.0 upstream; 1.26.0 pinned (ConanCenter) | Apache-2.0 only | license corrected to "Apache 2.0" |
| opentelemetry-cpp-contrib (slides 63, 64) | yes: `github.com/open-telemetry/opentelemetry-cpp-contrib`; `instrumentation/` holds boost_log, glog, httpd, log4cxx, nginx, otel-webserver-module, spdlog | active (push 2026-10-12) | Apache-2.0 | the deck's "gRPC, libcurl, MySQL client instrumentations" and "OTel interceptor for gRPC" do not exist: slide 63 bullet and notes and slide 64 notes rewritten (log bridges and web-server modules only; gRPC context injected by hand with the W3C propagator, as opentelemetry-cpp's `examples/grpc` does); slide 62 notes name the contrib spdlog sink |
| protobuf `Arena::CreateMessage` (slide 117 notes) | not public in protobuf 6.33.5 (`src/google/protobuf/arena.h` at v33.5 has `Arena::Create<T>` only) | protobuf v36.2 upstream; 6.33.5 pinned | BSD-3-Clause | rewritten to `google::protobuf::Arena::Create<Envelope>(&arena)` |
| Boost.Beast (slide 113 notes) | yes: `github.com/boostorg/beast` | Boost 1.92.0 (2026-08-12) | BSL-1.0 | kept |
| jsoncpp (slide 126 code comment and notes) | yes: `github.com/open-source-parsers/jsoncpp` (Drogon's `Json::Value`) | 1.9.8 (2026-06-14) | MIT or public domain | kept |
| OpenSSL (slide 178 notes) | yes: `github.com/openssl/openssl` | 4.0.3 (2026-09-29) | Apache-2.0 | kept |
| Unleash (slide 260 footnote and notes) | yes: `github.com/Unleash/unleash` | v8.2.0 (2026-09-08) | AGPL-3.0 (open source; paid tiers exist) | kept as an open-source backend; "behind the same OpenFeature SDK" corrected: `open-feature/cpp-sdk-contrib` ships only a flagd provider (C++ SDK v0.1.4), so a C++ service calls Unleash's own API |

### Compendium references, one by one

"Holds" means the named cpp-statelessness chapter covers the claim; the deck then cites it by Doc number and URL
(`patterncatalyst.github.io/cpp-statelessness/docs/<doc>/`). Slide numbers are those at 8c86d61.

| Slide | sldId | Original reference | Verified against | Action |
|---|---|---|---|---|
| 21 | 276 | 'budget-aware' retry rule | Doc 07 ("Cap the retry budget at the request deadline") | holds; cited |
| 24 | 279 | composition root (DI by reference) | Doc 04 (`main()` as composition root, pass by reference) | holds; cited |
| 27 | 282 | ScopedConnection (RAII checkout, invalidate on broken) | Doc 07 (`ScopedConn`, `invalidate()`) | holds; real name `ScopedConn`, cited |
| 29 | 284 | "cpp-stateless idioms: PgTxn" | not in the compendium (no `PgTxn`) | rewritten: PgTxn described as a small RAII wrapper over a libpq transaction; Example 04 uses libpq calls directly |
| 60 | 315 | "the cpp-stateless deck has the configuration" (Batch span processor) | Doc 04 (`BatchSpanProcessorFactory`) | holds; cited |
| 62 | 317 | "§11 logs to stdout, not a file" | Doc 08 (`basic_logger_mt`, read-only root filesystem) | holds under Doc 08; cited |
| 84 | 339 | "§6 PMR per-request arenas" | Doc 03 | holds; cited; ALL-CAPS "CONCURRENCY" lowercased |
| 91 | 346 | per-service in-process state (PMR arenas, RAII pools) | Docs 03, 04 | holds; cited (Doc 04) |
| 94 | 349 | "cpp-stateless / cpp-container compendiums" | both repositories and sites | holds; both named with URLs |
| 99, 102 | 354, 357 | "port/adapter pattern" | not in the compendium (no ports/adapters or hexagonal chapter) | rewritten to Appendix F and Example 19 |
| 111 | 366 | "§3 Conan lockfile pinning" | Doc 11 (Conan profiles, one lockfile) | holds; cited; "(e.g., 3.21 → 4.0)" protobuf example dropped (protobuf C++ versions are 6.x now) |
| 117 | 372 | "§5 PMR integrates cleanly with protobuf arenas" | Doc 03 says the opposite emphasis: keep protobuf on its own allocator, the PMR arena for handler internals, boundary explicit in review | rewritten to the Doc 03 position; cited |
| 118, 119 | 373, 374 | "§6 PMR arenas" per connection | Doc 03 (per-request arenas) | holds as an extension; worded "the per-request arena of Doc 03, applied to a connection's lifetime" |
| 140, 148 | 395, 403 | "§4 composition root + adapter pattern is hexagonal" (slide bullets) | Doc 04 has the composition root, not adapters | rewritten to "a composition root in main() wiring adapters into ports (Example 19)" |
| 146 | 401 | "§4 idiom" (DI by reference) | Doc 04 | holds; cited |
| 147 | 402 | "§6 PMR-arena pattern" for aggregates | Doc 03 | holds; cited |
| 154 | 409 | "Conan + lockfile (cpp-stateless §3)" (slide bullet) | Doc 11; every C++ example commits `conan.lock` | holds; bullet now "Conan + a committed conan.lock" |
| 160 | 415 | "§9 covers this in detail; the cpp-stateless deck is the implementation reference" | Doc 09 (readiness flip on SIGTERM, signal handling) | holds for the readiness side; cited with Example 21 as the runnable C++ version |
| 163 | 418 | "§9 complete sequence" | Docs 09, 10, 05 (signal handler, stop_source, pool join) | holds in substance; cited Doc 09 |
| 180 | 435 | "§11 … stickiness" | Doc 01 (deployment posture: request- and process-scoped state only) | holds under Doc 01; cited |
| 188 | 443 | "§7 watcher pattern … atomically swaps the Lua state" | not in the compendium (no watcher or hot-reload); `examples/22-l7-routing/cpp` compiles the script once at startup and takes rule inputs through PUT /rules | rewritten to what the example does; a file watcher named as an extension |
| 213 | 468 | "PgConn from the §5 pool" | Doc 07 (`ScopedConn` pool) | holds under Doc 07; cited |
| 220 | 475 | "§9 graceful-shutdown discipline" | Appendix H of this deck covers it directly | rewritten to cite Appendix H |
| 227 | 482 | "cpp-stateless idioms (RAII unwinds, std::stop_token)" | Docs 02, 05 | holds; cited |

Not changed: the CQRS slide 29 code still uses the illustrative `PgTxn` wrapper (the notes now say so); the
cache-aside slide 213 code uses `PgConn`/`co_await pg_.acquire()` the same way.

## Unresolved or for the planner

- `examples/21-graceful-shutdown/cpp/src/main.cpp` calls `spdlog::info` inside the SIGTERM
  handler, which is not async-signal-safe; the deck (and the site) state the rule that the
  handler only stores an atomic flag. The slide excerpt omits the log call. Fix the example
  (outside S12 scope) or accept the excerpt.
- Resolved (user decision 6): the compendium and third-party library references are verified upstream; see
  "Reference and library verification". 37 replace ops (tag `_amend`, `tools/amend_decisions.py`).
- Slide 211 bullet "the next six slides" (shared sentence, voice forks) and slide 113 caption
  wording are left to the shared pass.
- The site codetab fixes listed in `site-fixes.md` (C++ rows) are needed for the deck code and
  the site to agree; the deck already carries the example-aligned code.

## Decision 7 amendment (vendor-neutral, 2026-10-12)

Generator: `tools/amend_vendor.py` (ops tagged `_vendor`, inserted just before the agenda op; run after `amend_decisions.py`).
Find strings and counts come from the pre-decision text copy (`verify_all.py` output of the edit files at 39a5b1e).

- Valet key (sldId 333): title "Valet key — scoped, time-bound, op-restricted", chip `c++ · Drogon + jwt-cpp`, `set_code` = `examples/12-security/cpp/order-service/src/valet.hpp` (`mint`, `verify`), 22 lines, notes rewritten (HMAC or HS256 ticket the service mints and verifies; generic object store). Code map row: matches `examples/12-security` (condensed excerpt, first comment line says so).
- Claim check (sldId 342): chip `c++ · rdkafka++ + jwt-cpp`, `set_code` = rdkafka++ produce/consume with a generic `store_`, ticket from `cndp::valet::mint` (15 minutes), 21 lines; caption rewritten; notes rewritten. Same lines as the site claim-check codetab after the site fix (`site-fixes.md`, decision-7 section). No example implements the claim check (illustrative, token from Example 12).
- Removed: AWS SDK for C++ (slides 78, 87, 89, 93); it was kept by the decision-6 amendment and now goes; the S3 pre-signed URL, STS AssumeRole, Azure SAS, GCS framing.
- Shared rewrites (where present in this deck): 4C's notes and bullet (CloudTrail, "S3 bucket open"); event-driven tools notes ("to S3" → "to an object store"); valet-key concept notes (one generic implementation sentence instead of S3/Azure/GCS/STS); strangler-fig IdPs (Keycloak, Dex instead of Auth0, Azure AD); zero-trust edge (Pomerium or OAuth2 Proxy in front of Keycloak instead of Google IAP, Cloudflare Access, AWS Verified Access; licence note Pomerium Apache-2.0, OAuth2 Proxy MIT); claim-check concept notes; choosing-the-pattern notes; glossary SAS entry and note removed; Appendix I gateway list without Apigee; Appendix M references: gRFC A6 instead of the AWS Builders' Library.
- C++ only: valet notes (332) say signed ticket and object store instead of pre-signed URL, S3 or MinIO; claim notes (341) use `https://objects.internal/claims/abc-123` and per-object access policies; take-aways (344) and closing notes (348) name jwt-cpp instead of the AWS SDK for C++; agenda notes and Appendix R notes (528, 536) drop the OpenShift Local sentences (the C++ deck never had Appendix S).
- Kept (not vendor services): Heroku as the origin of the twelve-factor methodology (history), Google SRE Book (reference), gRPC / Google.Protobuf / Google.Rpc (open-source libraries), Netflix concurrency-limits (Apache-2.0 library), Red Hat UBI and the Red Hat brand frame.
- Figures (`replace_picture`, `tools/vendor_figures.py`): sldIds 332, 335. The valet-key figure named S3, Azure SAS, GCS and STS; the zero-trust figure listed Google IAP, Cloudflare Access and AWS Verified Access; both become the neutral site figures (`12-valet-key.png` with "object store" labels, `12-zero-trust.png`).
