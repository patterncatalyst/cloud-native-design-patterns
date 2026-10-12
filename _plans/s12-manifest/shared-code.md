# Language-agnostic code slides

The YAML, proto, JSON and proxy-config slides that every language deck carries. Ops are in each deck's
edit file (group 5 of the op order, `cat: code` / `notes`). Status: `matches` (agrees with the site and
`examples/`, no change), `replaced` (code changed), `illustrative-ok` (no site or example counterpart;
checked against the current API and left, or corrected only where the API was wrong).

sldIds: Py = Python, Qk = Quarkus, Go, Sp = Spring, DN = .NET, C = C++.

| Slide title | sldIds | Source | Status | Change |
|---|---|---|---|---|
| Resilience as configuration, not per-call code (Istio retries) | Py/Qk/Go/Sp 276, DN 277, C 276 | `_docs/02-communications.md` VirtualService | replaced (comment only); C matches | The first comment promised outlier detection the manifest does not have: now "Istio: bounded retries and timeout for inventory-service" (the C++ variant already said so). |
| Scale on lag (events) and on RPS (HTTP) (KEDA) | Py/Qk/Go/Sp 300, DN 302, C 300 | `_docs/06-stream-processing.md` (stale, see site fixes); KEDA v2.21.0 and the http-add-on API | replaced | `ScaledObject` gains `metadata.name` and the kafka trigger `bootstrapServers: "cndp-kafka-bootstrap:9092"` (both required); `HTTPScaledObject` gains `apiVersion: http.keda.sh/v1alpha1`, `metadata.name`, `hosts` and `scaleTargetRef { name, service, port }`. 20 lines (the box holds 20 at 12 pt). The HTTP comment names each deck's service (FastAPI, Quarkus, Spring Boot, ASP.NET Core, Go, Drogon): the Go deck said "FastAPI". |
| Gate breaking changes in CI (.NET, CI + Apicurio v3 REST) | DN 312 | `examples/09-api-registry/verify.sh`, `.github/workflows` (checkout@v7) | replaced | `actions/checkout@v4` → `@v7`; the v3 create-version call now posts a JSON body (`content.content`, `contentType`) built with `jq --rawfile`, artifact `order-placed` as in Example 09; "409" → "400 with RuleViolationException" (Apicurio 3.3). 19 lines. |
| OPA Gatekeeper ConstraintTemplate (Rego) | Py/Qk/Go/Sp 338, DN 340, C 338 | `_docs/12-security.md` | matches | Gatekeeper parses the `rego:` field as Rego v0, so the v0 rule syntax is correct; the slide adds the Constraint and the `allowedRegistries` parameter to the site's shorter version. |
| Evolving a .proto safely | Py/Qk/Go/Sp 363, DN 365, C 363 | `_docs/15-appendix-b-versioning.md` | matches | none |
| The Kubernetes side: probes, preStop, grace period | Py/Qk/Go 420, Sp 424, DN 428 | `_docs/21-appendix-h-shutdown.md`; `examples/21-graceful-shutdown/*` | replaced (paths and one comment) + notes | Liveness `/livez` → `/healthz` (.NET: `/healthz/ready` → `/readyz`, `/healthz/live` → `/healthz`): every example exposes `/readyz` and `/healthz`. Comment "must NOT fail" → "keeps answering during the drain". Notes rewritten (they named `/livez`). |
| Content-based routing with HAProxy | Py/Qk/Go 430, Sp 434, DN 438, C 430 | none (illustrative) | illustrative-ok, one fix | The TLS `bind` gains `alpn h2,http/1.1`: without HTTP/2 on the listener, gRPC clients cannot connect, and the `is_grpc` ACL never matches. |
| Content-based routing with Nginx | Py/Qk/Go 431, Sp 435, DN 439, C 431 | none (illustrative) | illustrative-ok, one fix | `listen 443 ssl http2;` → `listen 443 ssl; http2 on;` (the `http2` listen parameter is deprecated since nginx 1.25.1). |
| Content-based routing in the mesh: Istio VirtualService | Py/Qk/Go 432, Sp 436, DN 440, C 432 | `_docs/22-appendix-i-l7-routing.md` | matches | none |
| Canary release: weighted Istio routing | Py/Qk/Go 437, Sp 441, DN 445, C 437 | `_docs/22-appendix-i-l7-routing.md` | matches | none |
| Header-based steering: dark launches | Py/Qk/Go 438, Sp 442, DN 446, C 438 | none (illustrative) | illustrative-ok | none (networking.istio.io/v1, header match syntax current for Istio 1.31.1) |
| Header injection and URL rewrites | Py/Qk/Go 440, Sp 444, DN 448, C 440 | none (illustrative) | illustrative-ok, two fixes + notes | `x-request-id: "%REQ(x-request-id)%"` set the header to itself (Envoy generates it anyway) → `x-client-ip: "%DOWNSTREAM_REMOTE_ADDRESS_WITHOUT_PORT%"`; `x-tenant-id: "%DOWNSTREAM_PEER_CERT_V_END%"` used the certificate expiry as an identity → `x-peer-identity: "%DOWNSTREAM_PEER_URI_SAN%"` (the SPIFFE ID in the mesh). Notes rewritten in all six decks (the C++ notes called the expiry operator the SPIFFE ID). |
| Istio for east/west: DestinationRule + VirtualService | Py/Qk/Go 449, Sp 453, DN 457, C 449 | `_docs/22-appendix-i-l7-routing.md` | matches (C++ is a compact variant of the same manifest) | none |
| Targeting and rollout live in config (flagd) | Py/Qk/Go 509, Sp 513, DN 523, C 509 | `examples/27-feature-flags/flags/flags.json` | replaced | Adds the `"$schema": "https://flagd.dev/schema/v0/flags.json"` line the example carries; the `new-checkout` flag is otherwise identical. 17 → 18 lines. |

Small changes use `replace` on the code text (expect 1, `sldIds` given) so the inline comment runs keep
their colour; whole boxes use `set_code` (KEDA, flagd, .NET CI). Ops per deck: Python, Quarkus, Go and
Spring 13 each, .NET 15, C++ 9 (76 in all). Status count over the 78 deck slides: matches 31, replaced
23 (5 of them comment-only), illustrative-ok 24 (18 with a correctness fix). Dry run: `deck_edit.py
--dry-run` with each deck's group-5 ops alone, from the repository root, succeeded for all six decks
with no cross-run merges; `check_rewrites.py` 0 errors.

Not owned here: the Appendix O code slides (Postman JSON, Newman bash, GitHub Actions), the Maven/Drools
slides of the JVM decks and the `protobuf + <language>` slides, which the deck reviews cover.
