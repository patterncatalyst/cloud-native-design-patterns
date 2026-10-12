# S12 deck edit manifest

Step 4 of `_plans/s12-deck-refresh-plan.md`. The Sonnet batches apply these files mechanically;
nothing here needs judgment at apply time. Author: Opus planner, 2026-10-12, branch
`docs/deck-refresh` at 8c86d61.

## Files

| File | What |
|---|---|
| `lgtm-presentation/edits/_shared.json` | `replace` ops (no `sldIds`) that match the same number of times in all six language decks: voice, positional and old-engine fixes, including Appendix O |
| `lgtm-presentation/edits/<deck>.json` | everything else for one deck, in apply order (see "Op order") |
| `lgtm-presentation/edits/png/*.png` | figures for `replace_picture`: `31-*` (Appendix R), `27-black-box`, `27-ci-gate` (Appendix O), the image-audit replacements, and the decision-7 figures `12-valet-key`, `12-zero-trust`, `net-advisory-*` (`tools/vendor_figures.py`), rendered from `assets/diagrams/` with cairosvg 2.9.1 at 1400 px; the `32-*` Appendix S figures are removed |
| `_plans/s12-manifest/<deck>.md` | per deck: what changes and why, the code map (slide → site codetab → example file → status), image audit, notes |
| `_plans/s12-manifest/site-fixes.md` | site codetabs that are stale against `examples/` (the `docs(site)` commit) |
| `_plans/s12-manifest/companions.md` | the `.md` and `.docx` companions of the two policy decks |
| `_plans/s12-manifest/companions/` | decision 7: the exact new text of `network-policy-process-advisory.md` and the generated docx paragraph operations |
| `_plans/s12-manifest/watch-ledger.md` | watch-tier hits that stay, with reason codes |
| `_plans/s12-manifest/tools/` | the generators and checks used to build the edit files (scratch copies; reproducible) |
| `_plans/s12-manifest/fit/<deck>.json` | layout-fit plan per language deck (font fits, excerpts, frame changes, title shortenings); `tools/gen_fit.py apply` folds it into the deck file (see "Layout fit") |
| `scripts/deck_fit.py` | the rendered-layout check: text outside its frame, over the page number or logo, off the slide, or on top of other text |

## How to apply (per batch)

Run from the repository root (the `png` paths in the edit files are relative to it), with the S12
venv python:

```bash
V=/tmp/claude-1000/-home-rsedor-Dev/0dea024d-0bf0-4ae5-bddd-7dec0cf60b22/scratchpad/s12/venv/bin/python
export DECK_BACKUP_DIR=/tmp/claude-1000/-home-rsedor-Dev/0dea024d-0bf0-4ae5-bddd-7dec0cf60b22/scratchpad/s12/backup
D=lgtm-presentation/Designing-Cloud-Native-APIs-Python.pptx
$V scripts/deck_edit.py "$D" lgtm-presentation/edits/_shared.json \
   lgtm-presentation/edits/Designing-Cloud-Native-APIs-Python.json --dry-run   # review the diff
$V scripts/deck_edit.py "$D" lgtm-presentation/edits/_shared.json \
   lgtm-presentation/edits/Designing-Cloud-Native-APIs-Python.json             # apply in place
```

The policy decks take only their own file (no `_shared.json`). Every `replace` carries the exact
`expect` count measured on the deck at 8c86d61 in this order; a mismatch means the deck changed
and the batch stops. Apply each deck's files exactly once, to the committed deck.

After applying: `python3 scripts/deck_text.py --write`, then remove the deck from
`KNOWN_MISSING_NOTES` (.NET batch), run `scripts/voice-scan.sh --tier ban lgtm-presentation/text`
(0 ban), `python3 scripts/validate_site.py`, `python3 scripts/deck_text.py --check`, and render
every slide whose sldId appears in the edit file plus every new slide.


## Summary (build of 2026-10-12)

`_shared.json`: 58 `replace` ops (engine 10, positional 4, stack 4, voice 40).

| Deck file | Ops | By category | Dry run | Ban after | Watch after | Positional | Old engine | Denylist |
|---|---|---|---|---|---|---|---|---|
| `Designing-Cloud-Native-APIs-Python.json` | 464 | code 33, fit 53, new 67, notes 5, positional 37, stack 36, version 1, voice 232 | ok | 0 | 54 | 0 | 0 | 0 |
| `Designing-Cloud-Native-APIs-Quarkus.json` | 474 | code 53, fit 55, new 67, notes 10, positional 34, stack 32, version 3, voice 220 | ok | 0 | 51 | 0 | 0 | 0 |
| `Designing-Cloud-Native-APIs-Spring.json` | 491 | code 39, fit 83, new 67, notes 2, positional 9, stack 58, version 7, voice 226 | ok | 0 | 54 | 0 | 0 | 0 |
| `Designing-Cloud-Native-APIs-DotNet.json` | 631 | code 56, engine 2, fit 88, new 66, notes 43, positional 36, stack 93, version 5, voice 242 | ok | 0 | 63 | 0 | 0 | 0 |
| `Designing-Cloud-Native-APIs-Go.json` | 517 | code 58, fit 40, new 67, notes 30, positional 38, stack 52, version 1, voice 231 | ok | 0 | 55 | 0 | 0 | 0 |
| `Designing-Cloud-Native-APIs-Cpp.json` | 399 | code 50, fit 29, new 65, notes 8, positional 17, stack 91, version 12, voice 127 | ok | 0 | 45 | 0 | 0 | 0 |
| `K8s-Environment-Access-Policies.json` | 26 | positional 1, stack 12, voice 13 | ok | 0 | 8 | 0 | 0 | 0 |
| `Network-Policy-Process-Advisory.json` | 55 | stack 55 (decision 7 rework: set_text 33, set_notes 19, replace_picture 3) | ok | 0 | 0 | 0 | 0 | 0 |

Amended 2026-10-12 for user decision 6 (plan): Spring Appendix D presents the hand-rolled saga orchestrator of
`examples/17-sagas/spring-boot` (Spring Statemachine only as archived upstream); Go valet key and claim-check follow
`examples/12-security/go` (golang-jwt ticket, minio-go removed; site fix in `site-fixes.md`); C++ compendium and
library references verified upstream (table in the C++ file). Generator: `tools/amend_decisions.py` (ops tagged
`_amend`, inserted before the agenda and Appendix R ops); new figure `png/17-sagas-architecture.png`. The dry runs
and scans were re-run for all eight decks after the amendment.

Amended 2026-10-12 for user decision 7 (plan; vendor-neutral, house dependency and platform policy): nothing relies on
AWS, Azure, Google Cloud, ACS or OpenShift, and only maintained open-source libraries appear.

- No Appendix S in any deck: `tools/amend_vendor.py` drops the `s0`-`s9` clone ops and every `$s*` op (71 ops per
  deck, 79 in .NET; the C++ deck never had them); the agenda line is "Appendix R · Example 05 on minikube" (.NET:
  "Appendices P–R · .NET on Linux, Blazor, minikube"), so the agenda keeps 13 lines and its fit; agenda, title,
  overview and Appendix R notes no longer mention OpenShift Local. Appendix R stays in all six. The `32-*` PNGs are
  deleted. `tools/gen_rs.py` still emits S; `amend_vendor.py` removes it, so run it last.
- Valet key and claim check (slides 78 and 87; .NET 80 and 89) follow `examples/12-security/<lang>`: an HMAC-SHA256
  ticket (HS256 JWT in Go and C++) the service mints and verifies itself, a generic encrypted object store and no
  `s3://` URI; boto3, the AWS SDK for Java v2 / quarkus-amazon-s3, the AWS SDK for .NET and the AWS SDK for C++ are
  gone (the Go slides were fixed in `amend_decisions.py`). The same code is the site fix (`site-fixes.md`).
- About 20 vendor mentions per deck are rewritten by shared find/replace pairs (4C's, valet and claim-check concept
  notes, strangler-fig IdPs, zero-trust edge proxies, glossary SAS, Appendix I Apigee, Appendix M AWS Builders'
  Library → gRFC A6) and deck pairs (.NET Azure SignalR / App Service / "supported on OpenShift"; C++ AWS SDK and
  MinIO). Figures: the valet-key and zero-trust concept figures become the neutral site figures, the Python,
  Quarkus and Spring Appendix I layered-stack figure (Apigee) becomes the site `22-l7-layers`, and the .NET
  Appendix J tables are re-rendered without "Azure".
- The network advisory deck and companion are reworked to upstream Kubernetes (ClusterNetworkPolicy Admin and
  Baseline tiers, NetworkPolicy, Calico or Cilium, Inspektor Gadget, Kyverno / Gatekeeper, Trivy, Falco, Argo CD);
  see `Network-Policy-Process-Advisory.md` and `companions.md`. The K8s policies deck needed no change.
- Generators: `tools/amend_vendor.py` (ops tagged `_vendor`, before the agenda op; replace finds and counts from
  the pre-decision text copies), `tools/gen_advisory.py`, `tools/vendor_figures.py`, `tools/companion_docx.py`,
  `tools/watch_ledger_md.py`. Run order after `build.py`: `amend_decisions.py`, `amend_vendor.py`, `verify_all.py`.
- Dry runs against fresh copies of the committed decks: all `ok`; slides after: Python, Quarkus, Go, C++ 281,
  Spring 285, .NET 312, K8s 18, advisory 20; ban 0, positional 0, old engine 0, denylist 0 with the decision-7
  entries; `AWS|Amazon|S3\b|STS|Azure|GCS|Google Cloud|OpenShift|\bOCP\b|\bACS\b` matches only `ALREADY_EXISTS`
  (a gRPC status code) in the gRPC-errors notes.
- BUILD.md (step 14) must drop its minio-go / "AWS SDK" line (lgtm-presentation/BUILD.md lines 46-47), which the
  new `minio` and `cloud-sdk` denylist entries flag.

Watch-after counts are scanner lines in the post-edit text copy; every one is in `watch-ledger.md` with a reason. Dry runs: `deck_edit.py --dry-run` with `_shared.json` (language decks) and the deck file, against a copy of each deck at 8c86d61, all `ok`.

## Conventions

- Slides are addressed by sldId. Slide numbers appear only in `_slide` comments and in the per-deck
  notes; they are the numbers of the deck at 8c86d61 and shift after the R and S slides are added
  only at the end.
- Extra keys in an op (`cat`, `_slide`, `_why`, `_src`, `_keep`, `_amend`, `_amended`) are documentation; deck_edit
  ignores them. `cat` is one of `version`, `stack`, `code`, `voice`, `positional`, `notes`, `new`
  (plus `engine` for the old container engine, a kind of `stack` change kept separate for the
  report).
- JSON files spell the old container engine's name with a `o` escape, so the repository text
  never contains the word and `validate_site.py` can scan `lgtm-presentation/` (step 15).
- Code lines: at most 22 per box (or the box's current count when larger) and 95 columns. Code
  slides agree with `examples/` (library, API, identifiers, topic names); excerpts say so in their
  first comment line. Layout fit (2026-10-12): every code box must also fit its frame in the
  render; long boxes are excerpted with `// ...` / `# ...` ellipsis comment lines (verbatim lines
  kept, the cut summarised on the ellipsis line) and sized down, never under 9 pt (bullets never
  under 12 pt).
- Every new or rewritten sentence follows the voice rules (lgtm-professional-voice): no ban-tier
  phrase, no positional words (`above`, `below`, `next slide`, `previous slide`,
  `previous section`, `following section`, `see slide N`, `preceding`; numeric "above 50%" and
  "at or above" stay), no old engine name, no ALL-CAPS emphasis, no "actually/simply/very/really",
  one em dash per sentence at most.

## Op order (per deck file)

1. `_shared.json` (language decks only).
2. Deck-specific voice, positional and engine rewrites (`replace`, with `sldIds`).
3. Appendix O ops (code box, figures, titles).
4. Image replacements from the image audit.
5. Language-agnostic code slides (YAML, proto, JSON, HAProxy, nginx, Actions).
6. Deck content: version, stack, code, notes (including the 17 .NET slides without notes).
7. Agenda, then Appendix R (all six), appended at the end (Appendix S removed by decision 7).
8. Layout-fit ops (`cat: fit`, from `_plans/s12-manifest/fit/<deck>.json`), last. A fitted box whose
   code a `set_code` op writes gets `pt` (and `line_spacing`) on that op, and its excerpt in its
   `lines`, instead of a separate op.

## Pin table

Every version string on a slide or in the notes after the edits, and the pin it equals. Source:
`_plans/modernization-plan.md` "Target pins" (MP) and the S2–S10 evidence sections, or the file
named. A major-only label ("Spring Boot 4", ".NET 10", "Java 25", "C++23", "Apicurio v3", "Kafka
4") is allowed when it agrees with the pin; a minor without the patch ("Spring Boot 4.0",
"Quarkus 3.35") is not. Versions in a historical sentence ("since .NET 6", ".NET 8 added
IExceptionHandler", "from .NET 4.x") are history, not pins, and stay.

| Component (as written on slides) | Pin | Source |
|---|---|---|
| Quarkus | 3.40.1 (LTS), Java 25 | MP pins; S2 |
| Spring Boot | 4.1.1, Java 25 | MP pins; S3 |
| Spring Framework | 7.0.9 | spring-boot-dependencies 4.1.1 BOM (`spring-framework.version`), the parent of every `examples/*/spring-boot/**/pom.xml` |
| Spring Kafka / Spring Integration / Spring for GraphQL / Spring Security | 4.1.1 / 7.1.1 / 2.0.5 / 7.1.1 | same BOM |
| Jackson | 3 (`tools.jackson`; BOM 3.1.5) | S3; same BOM (`jackson-bom.version`) |
| OpenTelemetry Java agent | 2.32.0 | S3 |
| JVM images | `ubi10/openjdk-25:1.24-15`, `ubi10/openjdk-25-runtime:1.24-15` | MP pins |
| .NET | 10.0.12 (SDK 10.0.112), `net10.0`, C# 14 | MP pins; S4 |
| .NET images | `ubi9/dotnet-100:9.8-1791421718`, `ubi9/dotnet-100-aspnet:9.8-1791363520` (no ubi10 .NET image exists) | MP pins; S4 |
| Confluent.Kafka / Streamiz.Kafka.Net | 2.16.0 / 1.8.2 | S4 |
| OpenTelemetry .NET / Npgsql / Grpc.* / Google.Protobuf / StackExchange.Redis / HotChocolate / OpenFeature / flagd provider / SignalR | 1.19.1 / 10.0.3 / 2.84.0 / 3.36.2 / 3.4.0 / 16.6.8 / 2.14.1 / 0.5.0 / 10.0.12 | S4 |
| Python | 3.14; `ubi10/python-314-minimal:10.2-1791464217` (fallback `ubi9/python-314:9.8-1791466446`) | MP pins; S5 |
| FastAPI / pydantic / aiokafka / grpcio / strawberry / redis-py / OTel Python | 0.143.0 / 2.14.0 / 0.14.0 / 1.84.0 / 0.333.0 / 8.1.0 / 1.45.1 (contrib 0.66b1) | S5 |
| faust-streaming | 0.15.3 | S5 |
| Go | 1.27.2; builder `docker.io/library/golang:1.27.2`; runtime `ubi10/ubi-minimal:10.2-1791444377` | MP pins; S6 |
| Go libraries | franz-go 1.22.1, pgx 5.11.0, go-redis 9.23.0, gqlgen 0.17.95, golang-jwt 5.3.1, OTel Go 1.47.0 (otelhttp/otelgrpc 0.72.0), gobreaker v2.4.0, cenkalti/backoff v7.0.1, gopher-lua 1.1.2, goka 1.1.17, coder/websocket 1.8.15, OpenFeature go-sdk 1.19.0 + flagd 0.7.1, grpc 1.84.0, protobuf 1.36.12 | S6 |
| C++ | C++23; GCC 15 (`gcc-toolset-15`) on `ubi10/ubi:10.2-1791444044`; CMake 4.4.4; Ninja 1.13.2; Conan 2.33.0; runtime `ubi10/ubi-minimal:10.2-1791444377` | MP pins; S7; CLAUDE.md |
| C++ libraries | drogon 1.9.13, grpc 1.84.0, protobuf 6.33.5, librdkafka 2.14.2 (`rdkafka++`), libpq 17.11, redis-plus-plus 1.3.15, jwt-cpp 0.7.2, sml 1.2.0, sol2 3.5.0, lua 5.4.8, opentelemetry-cpp 1.26.0, spdlog 1.17.0, nlohmann_json 3.12.0, cppgraphqlgen 4.5.9 | S7 |
| Kafka (compose, minikube) | 4.3.1 (`apache/kafka:4.3.1`; Strimzi `quay.io/strimzi/kafka:1.2.0-kafka-4.3.1`) | MP pins; S8; S9 |
| Kafka (OpenShift Local) | 4.2.0 (AMQ Streams `amqstreams.v3.2.1-14`, channel `amq-streams-3.2.x`) | S10; Appendix S |
| Postgres | 18 (`postgres:18.6-alpine`; OpenShift: `registry.redhat.io/rhel10/postgresql-18`) | MP pins; Appendix S |
| Redis | `redis:8.10.2-alpine` (AGPLv3 option) | MP pins |
| Debezium / Apicurio / flagd / LGTM / Envoy | `quay.io/debezium/connect:3.7.0.Final` / `apicurio-registry:3.3.3` (REST v3) / `flagd:v0.17.0` / `grafana/otel-lgtm:0.36.0` (Grafana 13.2.3) / `envoyproxy/envoy:v1.39.3` | MP pins |
| Test tools | newman 6.2.3, newman-reporter-htmlextra 1.23.1, hey v0.1.5, ghz v0.121.0, conftest 0.71.1, kcat 1.7.1 | MP pins; S8 |
| GitHub Actions | `actions/checkout@v7`, `actions/upload-artifact@v7` | `.github/workflows/*.yml`; upload-artifact v7.0.2 (2026-10-07) |
| minikube / Kubernetes / kubectl / Helm | v1.39.0 / v1.36.5 / v1.36.5 (kustomize v5.8.1) / v4.3.0 | MP pins; S9; Appendix R |
| Strimzi / CNPG / KEDA / Istio | 1.2.0 / v1.30.1 / v2.21.0 / 1.31.1 | MP pins |
| kubeconform | v0.8.0 (CRDs-catalog 63669a570e231d4f1f8396d229a1de512bcf0a34) | MP pins |
| OpenShift Local | crc 2.64.0, OpenShift 4.22.14, Kubernetes v1.35.6; 12 vCPU, 32768 MiB | MP pins; S10; Appendix S |

Not pins (stay as written): `Apache 2.0` and other license names, `TLS 1.3`, HTTP/1.1 and HTTP/2, RFC numbers, IP addresses such as `10.1.0.10`, `.NET 6`/`.NET 8`/`.NET 9`/`.NET 4.x` and `C# 12` in historical sentences, `AWS SDK for Java v2` (a product name), Bean Validation 3.1 (the Jakarta specification level in Spring Boot 4), `Apicurio v3` (the REST API major).

## Stale-stack denylist (for `validate_site.py`, step 15)

Applied to every line of `lgtm-presentation/text/*.md` (code blocks included) and to
`lgtm-presentation/*.md`. A hit is an error unless the exemption regex matches the same line.
Python `re` syntax; flags as given. The old engine is written `p[o]dman` so this file does not
contain the word.

Machine-readable copy: `_plans/s12-manifest/denylist.json` (`id`, `regex`, `flags`, `exempt`, `files`, `why`).

| id | regex | flags | exemption | scope | why |
|---|---|---|---|---|---|
| old-engine | `p[o]dman` | i |  | all | Docker Engine / docker compose is the runtime (S1) |
| poetry | `\bPoetry\b\|\bpoetry (install\|add\|lock\|run)\b` |  |  | all | Python examples use pip with a full == requirements.txt freeze (S5) |
| fastapi-on-event | `@app\.on_event\b\|\.on_event\(` |  |  | all | FastAPI on_event replaced by lifespan (S5) |
| faust | `\bfaust\b(?![-.])` | i | `faust-streaming` | all | stream processing is faust-streaming 0.15.3 (S5); its Python module is `faust` (faust.App), which stays |
| modern-cpp-kafka | `modern-cpp-kafka\|kafka::clients` | i | `archived` | all | C++ Kafka is librdkafka's C++ API rdkafka++ (S7) |
| masstransit | `MassTransit` | i | `dropped\|commercial licen[cs]e` | all | .NET Kafka is Confluent.Kafka; MassTransit dropped (S4) |
| kafka-ui | `kafka-ui` | i |  | all | kafka-ui removed; kcat or kafka-console-consumer.sh (S8) |
| kubeval | `\bkubeval\b` | i | `kubeconform` | all | kubeval is unmaintained; kubeconform v0.8.0 |
| libpqxx | `\b(lib)?pqxx\b` |  | `\bnot (lib)?pqxx\b` | all | C++ uses libpq directly (S7) |
| cxx-old-standard | `[Cc]\+\+ ?(17\|20)\b\|c\+\+2a\|-std=c\+\+(17\|20)\|CMAKE_CXX_STANDARD (17\|20)\b` |  | `\b(since\|in\|from) [Cc]\+\+ ?(17\|20)\b` | all | C++23 (S7); history ('since C++20') stays |
| gcc-old | `\bGCC 1[0-4]\b\|gcc-toolset-1[0-4]\b` |  |  | all | GCC 15 via gcc-toolset-15 (S7) |
| cmake-old | `\bCMake 3\.\d+` |  | `UBI ships` | all | CMake 4.4.4 (S7) |
| quarkus-old | `\bQuarkus 3\.(?!40\b)\d+` |  |  | all | Quarkus 3.40.1 LTS (S2) |
| spring-boot-old | `\bSpring Boot (3\.\d+\|3\.x\|4\.0)\b` |  | `migrat\|upgrad\|from Spring Boot 3` | all | Spring Boot 4.1.1 (S3) |
| go-old | `\bGo 1\.(1\d\|2[0-6])\b\|golang:1\.(1\d\|2[0-6])\b` |  | `go-toolset\|Go 1\.22\b\|since Go 1\.\d+` | all | Go 1.27.2 (S6); Go 1.22 (method-aware ServeMux patterns) is the version a feature arrived in and stays |
| python-old | `\bPython 3\.([0-9]\|1[0-3])\b\|python:3\.([0-9]\|1[0-3])\b\|python-3(9\|1[0-3])\b` |  |  | all | Python 3.14 (S5) |
| dotnet-old-tfm | `\bnet[5-9]\.0\b\|dotnet-[5-9]0\b\|dotnet/(sdk\|aspnet):[5-9]\.` |  |  | all | .NET 10 (net10.0, ubi9/dotnet-100) (S4) |
| ubi8 | `\bubi8\b` | i |  | all | UBI 10 (UBI 9 only for .NET) |
| confluent-kafka-version | `Confluent\.Kafka[\" ]*(Version=\")?[ @]?2\.(?!16\.0)\d+\.\d+` |  |  | all | Confluent.Kafka 2.16.0 (S4) |
| streamiz-version | `Streamiz(\.Kafka\.Net)?[\" ]*(Version=\")?[ @]?1\.(?!8\.2)\d+\.\d+` |  |  | all | Streamiz.Kafka.Net 1.8.2 (S4) |
| jackson2 | `com\.fasterxml\.jackson\.(databind\|core)\b\|\bJackson 2\b` |  |  | all | Jackson 3 (tools.jackson) with Spring Boot 4 (S3) |
| spring-kafka-json-serde | `support\.serializer\.Json(Serializer\|Deserializer)\b` |  |  | all | Spring Kafka 4 uses the Jackson 3 JacksonJson serializers (S3) |
| topic-order-placed | `\border-placed\b` |  | `artifact\|@(Channel\|Incoming\|Outgoing)\(\|mp\.messaging\.\|channel\|\.avsc` | all | the Kafka topic is order.placed; the Quarkus channel name order-placed (bound to topic order.placed, as in every Quarkus example) and the Apicurio artifact id order-placed (Example 09) stay |
| graphql-go | `\bgraphql-go\b\|github\.com/graphql-go/` |  |  | all | Go GraphQL is gqlgen (S6) |
| go-deck-python-leftovers | `pyproject\|requirements\.txt\|\bpip install\b\|uvicorn\|FastAPI` |  |  | Designing-Cloud-Native-APIs-Go | the Go deck was retargeted from the Python deck; no Python tooling belongs in it |
| ocp-docs-old | `openshift_container_platform/4\.(1\d\|2[01])/` |  |  | all | OpenShift 4.22 (CRC 2.64.0 / OCP 4.22.14); superseded by `openshift` (decision 7) |
| kafka-image | `apache/kafka:(?!4\.3\.1\b)\d+\.\d+` |  |  | all | apache/kafka:4.3.1 (S8) |
| postgres-image | `\bpostgres:(?!18\.6-alpine\b)\d+\.\d+` |  |  | all | postgres:18.6-alpine (S8) |
| redis-image | `\bredis:(?!8\.10\.2-alpine\b)\d+\.\d+` |  |  | all | redis:8.10.2-alpine (S8) |
| otel-lgtm-image | `otel-lgtm:(?!0\.36\.0\b)\d` |  |  | all | grafana/otel-lgtm:0.36.0 (S8) |
| envoy-image | `envoyproxy/envoy:v(?!1\.39\.3\b)\d` |  |  | all | envoyproxy/envoy:v1.39.3 (S8) |
| apicurio-image | `apicurio-registry:(?!3\.3\.3\b)\d` |  |  | all | apicurio-registry:3.3.3 (S8) |
| flagd-image | `flagd:v(?!0\.17\.0\b)\d` |  |  | all | ghcr.io/open-feature/flagd:v0.17.0 (S8) |
| debezium-image | `debezium/connect:(?!3\.7\.0\.Final\b)\d` |  |  | all | quay.io/debezium/connect:3.7.0.Final (S8) |
| five-implementations | `\b(five\|5) (implementations\|backends)\b` | i |  | all | six language implementations (Go added) |
| latest-tag | `[a-z0-9]:latest\b` |  | `never\|no \|not \|nothing uses\|sketchy\|\bblock\b` | all | every image is pinned; :latest appears only as the thing not to do |
| cloud-sdk | `aws-sdk\|\bboto3\b\|AWSSDK\|IAmazonS3\|software\.amazon\|@aws-sdk\|AWS SDK\|azure-sdk\|Azure\.Storage\|google-cloud-\|cloud\.google\.com/go` | i |  | all | decision 7: no vendor cloud SDKs; valet key and claim check follow examples/12-security (a ticket the service signs itself) |
| vendor-cloud | `\bAWS\b\|\bAmazon\b\|\bS3\b\|\bSTS\b\|Azure\|\bGCS\b\|Google Cloud\|Google IAP\|\bEKS\b\|\bGKE\b\|\bAKS\b\|CloudTrail\|AWS Lambda\|Cloudflare Access\|Apigee\|Confluent Cloud` |  |  | all | decision 7: no AWS, Azure, Google Cloud or other managed-service framing in examples or recommendations (object storage is described generically) |
| minio | `minio-go\|\bminio\b` | i |  | all | decision 7: minio-go removed (Go valet key is a golang-jwt ticket) |
| acs | `\bACS\b\|[Aa]dvanced [Cc]luster [Ss]ecurity\|StackRox\|roxctl` |  |  | all | decision 7: nothing relies on ACS; the network advisory uses CNI flow logs, Inspektor Gadget, Kyverno/Gatekeeper, Trivy and Falco |
| openshift | `OpenShift\|\bOCP\b\|EgressFirewall\|OperatorHub\|\bSCCs?\b\|OVN-K\|\boc (apply\|adm\|get\|create\|new-project)\b` |  |  | all | decision 7: decks carry no Appendix S and no OpenShift-only feature; generic Kubernetes (Ingress/Gateway API, Pod Security Standards, Helm/upstream operators) |

## Watch-tier triage policy (slides and notes)

S11 rule 10 (`_plans/s11-professional-voice-plan.md`), adapted to decks:

1. Rewrite by default: `actually` (unless it contrasts with a stated wrong belief), `simply`,
   `obviously`, `trivially`, `of course`, `very`, `really`, `truly`, `crucially`, `notably`,
   `importantly`, `incredibly`, hedges (`arguably`, `perhaps`, `somewhat`, `fairly`,
   `essentially`, `basically`, `kind of`, `sort of`), `note that` / `keep in mind`, `let's ...`,
   summary markers, exclamation marks, soft hype (`powerful`, `seamless`, `leverage` → use,
   `robust` → name the failure, prose `journey` → path), "isn't X — it's Y" unless X is a
   misconception the audience holds, and "this slide/section covers" (notes describe the subject).
2. ALL-CAPS emphasis in prose, titles, bullets and notes becomes lowercase (or the sentence is
   restructured so the word lands at the end). ALL-CAPS labels that are part of the deck design
   stay: the red eyebrow lines (`APPENDIX L · CACHE-ASIDE`), divider letters, the failure-mode
   taxonomy labels (`NETWORK`, `COMPONENT`, `LOAD`), SQL keywords and constants. They are
   identifier-like (reason `design-label`); the scanner's ALL-CAPS pattern matches none of them
   except where an eyebrow or title contains an emphasis word, and those titles are rewritten.
3. Em dashes: a sentence with two or more em dashes (including a parenthetical pair) is rewritten
   to one or none. A notes paragraph whose three or more em dashes sit in different sentences, each
   with at most one, stays (reason `notes-paragraph`): the scanner counts per line and a notes
   paragraph is one line in the text copy. Empty table cells and code stay.
4. `quietly` / `silently` stay with a machine subject (`machine-subject`); drama is rewritten.
   `lie` with a machine subject stays.
5. `minikube`, `OpenShift Local`, `k3d` stay where the environment is the subject (Appendices R
   and S, tool tables): `literal-subject`. `laptop` becomes "workstation" or "locally".
6. `deliberate` (adjective) stays when it names a planned stage ("a deliberate intermediate
   state"): `planned-stage`. The ban-tier `deliberately` is always rewritten.
7. Recorded results and unit lists ("10 passed, 0 failed", "12 vCPU, 32768 MiB") match the
   parallel-number pattern and stay (`table-data`). Titles built as synthetic parallels ("Nine
   capabilities, nine real services") are rewritten.
8. `landscape` for a survey of tools stays (`survey-term`).

Reason codes: `machine-subject`, `literal-subject`, `table-data`, `survey-term`, `idiom`,
`identifier`, `misconception-contrast`, `design-label`, `notes-paragraph`, `planned-stage`,
`quoted`. Surviving watch hits are listed per deck in `watch-ledger.md`.

## Appendices R and S

> Decision 7 (2026-10-12): the decks carry Appendix R only. The Appendix S design that follows is kept as the
> record of the earlier manifest; `tools/amend_vendor.py` removes its ops.

Source: `_docs/31-appendix-r-minikube.md`, `_docs/32-appendix-s-openshift-local.md`,
`examples/05-event-driven/k8s/` and `openshift/`. Generator: `tools/gen_rs.py` (writes the ops that
end each deck file). All new slides are clones of the same deck's Appendix O slides, appended at the
end (after Appendix O; .NET: after Appendix Q), each with its own notes; content slides get the next
static page number.

### Templates (cloned per deck)

| Role | Python, Quarkus, Go, C++ | Spring | .NET | Template slide |
|---|---|---|---|---|
| Divider | 516 | 520 | 530 | "API Testing with Newman" divider (letter, title, subtitle, white logo) |
| Bullets | 527 | 531 | 541 | Appendix O "Take-aways" (eyebrow, title, body, footnote line) |
| Figure | 525 | 529 | 539 | Appendix O "The gate on ..." (eyebrow, title, picture, caption) |
| Code | 521 | 525 | 535 | Appendix O "Launch the service under test" (eyebrow, title, chip, code box, caption) |
| Agenda | 257 | 257 | 257 | second column (`set_text`) and notes (`set_notes`) |

Shape ids are read from each template by role (eyebrow at y 0.42 in, title 0.74 in, caption 6.50 in,
code box = the tall monospace shape, chip = the 11 pt monospace line at y 1.06 in). The figures are
`lgtm-presentation/edits/png/31-minikube-topology.png`, `31-minikube-image-flow.png`,
`32-openshift-topology.png`, `32-openshift-image-flow.png` (cairosvg 2.9.1, 1400 px wide, from
`assets/diagrams/`).

### Agenda

Second column becomes (Python, Quarkus, Spring, Go): 07 to 13 unchanged, then
"Appendices A–D · Protocols, Versioning, WebSockets, Sagas", "Appendices E–I · Errors, DDD,
Coupling, Shutdown, L7 Routing" (shortened so it no longer wraps), "Appendices K–L · Monolith →
Microservices, Caching Patterns", "Appendices M–O · Failure modes, Feature Flags, API Testing",
"Appendices R–S · Example 05 on minikube and OpenShift Local", "Glossary of acronyms" (13 lines, the
same visual height as before). C++: the R–S line reads "Appendix R · Example 05 on minikube". .NET (the
box has no autofit and overflowed with 15 lines): "Appendices J–L · .NET 10 Toolkit, Monolith →
Microservices, Caching" and "Appendices P–S · .NET on Linux, Blazor, minikube, OpenShift Local" replace
the separate J, P and Q lines, so .NET also has 13 lines. The agenda notes are rewritten to name
Appendices R and S (C++: R, and one line saying OpenShift Local covers the other five languages).

### Appendix R (all six decks): 9 slides, 8 page-numbered

| # | Template | Title | Content |
|---|---|---|---|
| R0 | divider | Example 05 on minikube | letter R; subtitle "The same services and the same verify.sh on a single-node Kubernetes cluster" |
| R1 | bullets | From compose to a cluster | what a cluster adds; scope (Example 05, three services, six languages, one node); not production; the contract that carries over; same verify.sh, ten checks. Footnote: site and code paths |
| R2 | bullets | The minikube runtime | profile cndp-k8s, docker driver, containerd, Kubernetes v1.36.5; 8 GB / 4 CPUs / 40 GB; NodePorts 30080 and 30300 on 127.0.0.1; no port-forward/tunnel/service; `--context cndp-k8s`. Footnote: minikube v1.39.0 · kubectl v1.36.5 · Helm v4.3.0 · Strimzi 1.2.0 |
| R3 | figure | One node, two namespaces | `31-minikube-topology.png` |
| R4 | bullets | Compose to Kubernetes | kafka → Strimzi (Kafka 4.3.1); postgres → StatefulSet; Secret; docker build + minikube image load, `imagePullPolicy: Never`; probes; NodePort 30080 |
| R5 | code | One overlay per language | `yaml · kustomize`: the deck language's `k8s/overlays/<lang>/kustomization.yaml` images block and the variables it appends (the .NET connection string uses a YAML escaped line break to stay within 95 columns) |
| R6 | figure | Images built on the host | `31-minikube-image-flow.png` |
| R7 | code | Run it | `bash · minikube`: setup-profile.sh, build-images.sh <lang>, deploy.sh <lang>, `RUNTIME=kubernetes BASE=http://127.0.0.1:30080 ./verify.sh`, verify-matrix.sh, teardown.sh --operator, minikube stop |
| R8 | bullets | Recorded results | 10 passed, 0 failed in six languages; per-language times; Tempo saw the three services; scale-to-zero check; stop the profile |

### Appendix S (Python, Quarkus, Spring, .NET, Go): 10 slides (.NET 11), 9 (10) page-numbered

| # | Template | Title | Content |
|---|---|---|---|
| S0 | divider | Example 05 on OpenShift Local | letter S; subtitle "Operators from OLM, restricted-v2 pods, Routes and an internal registry" |
| S1 | bullets | What OpenShift changes | OLM Subscription with pinned CSV and Manual approval; restricted-v2; edge-TLS Routes; skopeo to the internal registry, `imagePullPolicy: Always`; Kafka 4.2.0, rhel10/postgresql-18 |
| S2 | bullets | The OpenShift Local runtime | crc 2.64.0 / OpenShift 4.22.14 / Kubernetes v1.35.6; 12 vCPU, 32768 MiB, 80 GB; `--context crc-admin`; no secret printed or stored; one cluster at a time |
| S3 | figure | Topology on OpenShift Local | `32-openshift-topology.png` |
| S4 | code | Pinning an operator with OLM | `yaml · OLM`: `openshift/operators/subscription.yaml` (labels omitted) |
| S5 | bullets | restricted-v2 without exceptions | base security context; no runAsUser/fsGroup/SCC binding; numeric USER 185/1001 and group-0 files; otel-lgtm with three emptyDirs; every pod restricted-v2 |
| S6 | figure | Images through the internal registry | `32-openshift-image-flow.png` |
| S7 | code | A registry push without a token on disk | `bash · skopeo`: the token-in-a-pipe `skopeo copy` from the appendix, with the deck language's image name |
| S7n | code | Trace context through Kafka headers (.NET only) | `csharp · Confluent.Kafka`: inject in `OrderService/Program.cs` and extract in `ShippingConsumer/Program.cs` (excerpts; the long `PropagationContext` argument is wrapped) |
| S8 | code | Run it | `bash · OpenShift Local`: setup-crc.sh, build-push-images.sh <lang>, deploy.sh <lang>, the verify.sh call over HTTPS with the ingress CA, verify-matrix.sh, teardown.sh |
| S9 | bullets | Recorded results | 10/10 in five languages, every pod restricted-v2; times; one trace across Kafka; 302 to HTTPS and Grafana 13.2.3; second teardown exits 0 |

The exact slide text and notes are in the deck files (`set_text` and `set_notes` ops after the
`clone_slide` ops); `tools/gen_rs.py` is their source.

New page numbers: Python, Quarkus, Go 244–260; Spring 248–264; .NET 272–289; C++ 244–251.

## Layout fit (amendment 2026-10-12)

The first language batch (Python) showed an overflow the edits caused (slide 45, sldId 300: the
KEDA `ScaledObject` + `HTTPScaledObject` code is longer than the old code and its last line was
clipped at the box bottom, which `set_code`'s capacity estimate of 1.1 x the font size missed) and
pre-existing defects (slide 88 "Choosing the right pattern" running into the page number and logo,
slides 176 and 221 with code clipped at the bottom). `scripts/deck_fit.py` checks the render for
every slide: each `pdftotext -bbox-layout` line of the soffice PDF is matched to its shape (by text,
then geometry) and compared with the shape's frame (12700 EMU per PDF point). It flags text past its
frame (bottom, right, top, left), text over the page-number box or the logo picture, text off the
slide, and text on top of another shape's text. Validation: on the Python deck it flags 45 after the
edits (`overflow-bottom` 22.6 pt), 88, 176 and 221 in both states, and passes known-good slides
such as the section dividers (50) and the agenda.

Calibration (soffice 26.2.6.3 PDFs of the committed Python and .NET decks, 248 multi-line text
boxes): the line pitch of Red Hat Mono and Red Hat Text is 1.20 x the size x `spcPct` (median
1.1995, range 1.1985-1.2020), a rendered line box is 1.32 x the size, and Red Hat Mono advances
0.5985 x the size per character. `box_capacity` in `deck_edit.py` now uses these numbers
(n lines fit when the top inset + (n - 1) pitches + one line box stay inside the frame), so a code
box that would overflow fails at apply time.

New `deck_edit.py` ops: `fit_font` (size every run of a shape to `pt`, or `scale` all sizes; floors
9 pt for code, 12 pt for text; a code box must then fit), `resize_shape` (frame change that must stay
on the slide and clear of the page number and logo), `cut_code` (excerpt a code box in place,
keeping each remaining line's runs and colours; each cut may leave one ellipsis comment line), and
`pt` / `line_spacing` on `set_code`.

Flags per deck (`deck_fit.py`, flags on slides; "after edits" is `_shared.json` + the pre-fit deck
file applied to a copy of the committed deck; edit-caused = not present in the committed render):

| Deck | Committed | After edits: pre-existing | After edits: edit-caused | After fit |
|---|---|---|---|---|
| Python | 107 on 43 | 102 on 42 | 6 on 4 (45 KEDA, 24 and 43 code; 43 and 221 chips) | 0 |
| Quarkus | 129 on 54 | 106 on 54 | 2 on 2 (45 KEDA, 213 chip) | 0 |
| Spring | 183 on 60 | 166 on 60 | 5 on 3 (45 KEDA, 64 chip, 129 title) | 0 |
| .NET | 231 on 65 | 182 on 64 | 9 on 8 (47 KEDA; 38, 45, 68, 87, 142, 196 chips; 122 caption) | 0 |
| Go | 75 on 39 | 65 on 34 | 5 on 3 (45 KEDA, 117 and 241 chips) | 0 |
| C++ | 51 on 31 | 45 on 26 | 8 on 4 (78, 87 chips, 146, 206 captions) | 0 |

The edits themselves removed 5 to 49 flags per deck (rewritten code that fits). The minikube divider
cloned for Appendix R carries the template's 1.7 pt descent into its frame, inside the tolerance.

Fixes (plan entries per deck in `fit/<deck>.json`; each op carries `_fit` with the reason):

| Deck | Chips widened | Code font fits | Code excerpts | Text frames grown | Text font fits | Titles shortened |
|---|---|---|---|---|---|---|
| Python | 28 | 9 | 8 | 10 | 2 | 1 |
| Quarkus | 37 | 7 | 6 | 9 | 3 | 1 |
| Spring | 44 | 12 | 17 | 8 | 3 | 3 |
| .NET | 46 | 17 | 20 | 13 | 6 | 3 |
| Go | 19 | 9 | 2 | 9 | 2 | 1 |
| C++ | 8 | 14 | 8 | 3 | 0 | 1 |

- Chips (the `yaml · KEDA` labels) that wrapped are widened to the left to one line (.NET slide 237:
  two lines, so the chip stays clear of the first code line).
- Code: the largest size (0.5 pt steps, at least 9 pt) at which the box fits, with line spacing
  1.0 where 1.04 does not fit at 9 pt. Boxes that do not fit at 9 pt are excerpted: blank lines
  first, then imports, field and constructor boilerplate, or a second variant, each replaced by one
  ellipsis comment line that names what was cut; every remaining line is verbatim. The OPA
  Gatekeeper template (all six decks) and the Istio east/west pair (Python, Quarkus, Spring, .NET,
  Go) get the same excerpt everywhere.
- Text frames (captions, bullets) grow into free space, never past the next shape, the page
  number or the logo.
- Text that cannot grow: "Choosing the right pattern" 17 -> 15 pt; references 17 -> 14 pt (and
  6 pt paragraph spacing in Quarkus, Spring and .NET, which carry a runtime-docs line); caching
  pitfalls (Quarkus, Spring, .NET) 17 -> 16 pt; .NET known gaps 15 pt, recipe scaled 0.85 (17/14 ->
  14.5/12 pt), migration take-aways 15.5 pt.
- Titles: "Glossary of acronyms (2 of 2) — platform, security, telemetry" (all six); Spring
  "Temporal: a plain-Java saga that the Server makes durable", "A hand-rolled orchestrator: one
  row, one log, no cluster"; .NET "Temporal .NET: a plain-C# saga the Server makes durable",
  divider "Appendix J · .NET 10 Toolkit & Migration".

Regenerate: `tools/gen_fit.py suggest <deck> <after.pptx> <deck_fit --json output>` proposes chip,
code-font and frame entries from the flags; excerpts, text fonts and titles are decided by hand;
`tools/gen_fit.py apply` rebuilds each deck file from its committed pre-fit version
(`FIT_BASE`, default c70ab3a) plus `fit/<deck>.json`. The dry runs and scans in "Summary" were
re-run after the amendment (ban 0, positional 0, old engine 0, denylist 0, same watch counts).
The policy decks are not in this amendment.

## Batch checks

Every batch, after applying its edit files and before committing, renders its deck and runs the
layout check; the batch does not commit until it reports 0 flags:

```bash
V=/tmp/claude-1000/-home-rsedor-Dev/0dea024d-0bf0-4ae5-bddd-7dec0cf60b22/scratchpad/s12/venv/bin/python
LO_PROFILE=/tmp/claude-1000/-home-rsedor-Dev/0dea024d-0bf0-4ae5-bddd-7dec0cf60b22/scratchpad/s12/lo-profile \
  $V scripts/deck_fit.py lgtm-presentation/<deck>.pptx --keep-pdf <scratch dir>
# "deck_fit: <deck>.pptx: 0 flag(s) on 0 slide(s)", exit 0
```

A flag is fixed in the deck's `fit/<deck>.json` plan (then `tools/gen_fit.py apply`) or, for a
new op, in the deck file with `cat: fit`, never by editing the deck by hand. The renders of the
changed slides are still inspected (`deck_render.sh`); `deck_fit.py` does not judge legibility,
image content or colour.

## Fix round A (2026-10-12): colours, caps, accuracy, cross-deck

Found by the Quarkus validation (code lines coloured as comments, ALL-CAPS emphasis, code accuracy) and
applied to every language deck. Inputs: `fixA/` (the validator's `Q.fix1`/`Q.fix2` for Quarkus and the
cross-deck `capsfix` files). Generator: `tools/fixA_build.py` with the rules in `tools/fixA_rules.py`.
Checks: `tools/fixA_verify.py`, `tools/colour_audit.py`, `tools/caps_audit.py`,
`tools/test_set_code_colours.py`.

Tool fix (`scripts/deck_edit.py`): `code_lines()` took the run that ended the previous line
(`"# comment\n"`) as the template of the next line, so `set_code` wrote code lines in the comment green
8FB98F (41-60 lines on the Appendix O/R code slides of each committed deck, plus Quarkus/Spring/.NET slides
with a leading comment). A line's template is now the first run that put non-blank text on it. `set_code`
then colours the box by line type (`code_rgb`, default the box's code colour or E6E6E6; `comment_rgb`,
default the box's comment colour or 8FB98F; `"colour": false` keeps the template colours); the new
`recolour_code` op does the same for a box in place (splits multi-line runs, keeps third colours unless
`force`, fails on a no-op unless `allow_noop`); `cut_code` ellipsis lines are comment-coloured;
`set_geometry` works on the XML, so it also finds pictures on slides cloned earlier in the same run.
`tools/test_set_code_colours.py` reproduces the bug on the old tool and passes on the new one.

Fixup files (apply after the deck's earlier fix files, to the committed deck; replace counts measured on
the committed deck with its existing fixes; the recolour ops are last and carry `allow_noop`, because a
replay of the whole chain with the fixed tool already colours most boxes):

| Deck | File | Ops | From |
|---|---|---|---|
| Python | `Designing-Cloud-Native-APIs-Python.fix1.json` | 137 | capsfix 89, content 10, caps 29, recolour 9 |
| Quarkus | `Designing-Cloud-Native-APIs-Quarkus.fix1.json` | 167 | Q.fix1 101, Q.fix2 5, content 7, caps 17, recolour 37 |
| Spring | `Designing-Cloud-Native-APIs-Spring.fix2.json` | 165 | capsfix 88, content 9, caps 24, recolour 44 |
| .NET | `Designing-Cloud-Native-APIs-DotNet.fix2.json` | 184 | capsfix 84, content 15, caps 37, recolour 48 |
| Go | appended to `Designing-Cloud-Native-APIs-Go.json` (`_fixA`) | 120 | capsfix 89, content 9, caps 21, recolour 1 |
| C++ | appended to `Designing-Cloud-Native-APIs-Cpp.json` (`_fixA`) | 115 | capsfix 24, content 6, caps 84, recolour 1 |

Content ops: the outbox figure re-rendered without "is a lie" (`png/src/04-dual-write-outbox.svg`, 2048x972;
C++ 1181x561); bulkhead 5 as `examples/12-security` (Python, Spring comment, .NET, Go, C++; Quarkus in Q.fix1);
Kafka Streams `.to(..., Produced.with(windowSerde, Serdes.Double()))` on the Quarkus slide (Spring already
maps the window to JSON and passes serdes); OAuth2 Proxy / Pomerium no longer "check device posture";
"Microsoft Cloud Adoption Framework" replaced by the OWASP Microservices Security Cheat Sheet (denylist entry
`vendor-framework`); .NET saga ends in COMPENSATED and maps `/healthz` and `/readyz` as the examples do;
the OpenTelemetry manual-span API on the JVM and .NET slides uses the language's API (it was Python's);
title spacing on three shared titles; the Appendix R topology figure enlarged as in Q.fix2. Caps ops lower
every ALL-CAPS emphasis word outside the `caps_audit.py` allowlist and remove the soft positional
references ("covered next", "next slides", "we'll see next", ...).

Verification (scratch copies, fixed tool): each committed deck + its new fixup applies `ok`, and the full
chain `_shared` + deck JSON + all fix files from the pre-S12 parent gives the same text; Go and C++ apply
`ok` from the committed pre-S12 decks; `deck_fit` 0 flags on all six; `colour_audit` 0 hits (no code line
coloured as a comment, no comment line in code colour, no third colour) on all six; `caps_audit` 0 words
outside the allowlist; voice ban 0 (also `--raw`); positional 0 (soft references included); old engine 0;
denylist 0. Every slide a fixup touches (331 slides) rendered and inspected.

Not changed (figures carry baked-in ALL-CAPS: gray failure "PERCEIVED DIFFERENTLY / NOT fully down /
OBSERVE FROM THE CLIENT", event sourcing vs streaming "ARE / IS / NOT / ABOUT", tools landscape
"COMPLEMENT", coupling "strong OR distant"); `caps_audit` scans text only.

## Watch-tier ledger (final validation, 2026-10-12)

Every watch-tier line that `bash scripts/voice-scan.sh --tier watch --hits all lgtm-presentation` still reports after the
final-validation voice fixes (`edits/<deck>.fix*.json`, `cat: voice`, `_why` "watch triage (final validation)"). Before: 356
lines; fixed: 17 (em-dash pileups of five to seven per notes paragraph in the tools-landscape, auto-instrumentation, CQRS,
.NET saga-state and write-back and C++ error-facts notes; in the same notes, two leaked authoring requests, the garbled
"covered in this appendix.NET" sentence and the soft positional references "we cover next", "we'll show side by side",
"that follow"); kept: 339. The content fixes of the same round add three SQL clauses to the write-back notes
(C++, Go, Python slide 221), so the scanner now reports 342 lines, all kept. Slide numbers are those of the committed decks after the fixes (they do not shift: no slide
is added or removed). Ban tier is 0. One row per distinct line; a deck name is followed by its slide numbers.

### environment-specific noun (155 kept)

Reason: literal-subject (minikube is the subject: Appendix R and the agenda line that names it).

| Where (deck slide, or file:line) | Text | Kept as |
|---|---|---|
| C++ 2; .NET 2-3; Go 1-3; Python 1-3; Quarkus 1-3; Spring 1-3 | title, agenda and overview (the agenda line and notes that name Appendix R) | minikube |
| C++ 273; .NET 304; Go 273; Python 273; Quarkus 273; Spring 277 | Appendix R divider (Example 05 on minikube) | minikube |
| C++ 274-281; .NET 305-312; Go 274-281; Python 274-281; Quarkus 274-281; Spring 278-285 | Appendix R slides and notes | minikube |
| lgtm-presentation/BUILD.md:27 | Every language deck ends with Appendix R (Example 05 on minikube: a divider and  | minikube |
| lgtm-presentation/BUILD.md:83 | - Kubernetes: minikube v1.39.0 with Kubernetes v1.36.5, Strimzi 1.2.0, Helm v4.3 | minikube |

### em-dash pileup (3+ per line) (84 kept)

Reason `notes-paragraph`: a speaker-notes paragraph (one line in the text copy) whose em dashes sit in different
sentences, at most one per sentence (checked per sentence for every line), or a table row whose cells each carry one
dash (`table-data`). Grouped by the paragraph's opening words; the deck columns give the slide number.

| Where (deck slide, or file:line) | Text | Kept as |
|---|---|---|
| C++ 20 | The Istio sidecar handles wire concerns: mTLS, bounded retries with ba… | 3 dashes |
| C++ 39 | Three layers of the event-driven stack: (1) substrate — Kafka (Strimzi… | 4 dashes |
| C++ 49 | Three Kubernetes-native patterns for non-request work. (1) Job: a one-… | 3 dashes |
| C++ 66 | Baggage is a separate concern from trace context — they ride together… | 3 dashes |
| C++ 108 | The four rules of safe proto evolution, in one example: (1) add new fi… | 3 dashes |
| C++ 121 | Three options for saga state durability. (1) Database row — one row pe… | 3 dashes |
| C++ 131 | gRPC's error model is two layers: (1) one of ~16 canonical codes (OK,… | 3 dashes |
| C++ 137 | The retry storm is the classic distributed-systems amplification failu… | 3 dashes |
| C++ 151 | Three dimensions, each measurable. STRENGTH: how intensely are the two… | 3 dashes |
| C++ 202 | Martin Fowler's strangler fig pattern is the safest large-migration ap… | 3 dashes |
| .NET 25 | The resolver makes federation concrete in HotChocolate. The top-level… | 3 dashes |
| .NET 34 | For the WCF/COM+ audience this is the most important pattern. You used… | 3 dashes |
| .NET 63; Go 61; Python 61; Quarkus 61; Spring 61 | Expand the 'three pillars' framing into the five signals modern observ… | 4 dashes |
| .NET 67; Go 65; Python 65; Quarkus 65; Spring 65 | Demystify the magic word 'correlation.' It is not a backend join — it'… | 4 dashes |
| .NET 71; Go 69; Python 69; Quarkus 69; Spring 69 | The decision guide for sampling. Probabilistic is the simplest and the… | 4 dashes |
| .NET 94; Go 92; Python 92; Quarkus 92; Spring 92 | These are the five tests to apply in design and code review. (1) If tw… | 3 dashes |
| .NET 125 | First problem: the orchestrator must survive a crash mid-flow, so in-m… | 3 dashes |
| .NET 126 | This is the DB-backed option made concrete with EF Core — the one I'd… | 3 dashes |
| .NET 129; Go 125; Python 125; Quarkus 125; Spring 125 | This case is a common source of bad designs. The orchestrator calls se… | 3 dashes |
| .NET 133 | Walk the picture. The top row is the saga as a state machine: Created… | 3 dashes |
| .NET 138 | ASP.NET Core has had ProblemDetails (RFC 9457) built into Microsoft.As… | 3 dashes |
| .NET 140 | This is grpc-dotnet's standard rich-error model — the same wire shape… | 4 dashes |
| .NET 144 | Throwing from a single field's resolver is exactly right: HotChocolate… | 4 dashes |
| .NET 154 | Walk the three blocks. Ports: the domain declares plain C# interfaces,… | 3 dashes |
| .NET 158; Go 150; Python 150; Quarkus 150; Spring 154 | Frame the appendix. The central, slightly contrarian idea: coupling is… | 3 dashes |
| .NET 161; Go 153; Python 153; Quarkus 153; Spring 157 | Integration strength has four levels, worst to best. Intrusive couplin… | 3 dashes |
| .NET 163; Go 155; Python 155; Quarkus 155; Spring 159 | This brings strength and distance together into the design rule. Read… | 3 dashes |
| .NET 205; Spring 201 | Leave the checklist up at the end. The first point is the most common… | 3 dashes |
| .NET 220 | The .NET shape. Three named HttpClients registered via IHttpClientFact… | 3 dashes |
| .NET 231 | Two write-through flavours. The first uses IDistributedCache directly:… | 3 dashes |
| Go 121; Python 121; Quarkus 121; Spring 121 | First problem: the orchestrator must survive a crash mid-flow, so in-m… | 4 dashes |
| Go 203; Python 203 | The pre-condition for incremental migration: clients hit the proxy, th… | 3 dashes |
| Go 215 | The wrapper is small but the discipline is significant. Callers can't… | 3 dashes |
| Go 219; Python 219 | Two write variants and the standard cache-aside read for context. The… | 4 dashes |
| Spring 136 | This is grpc-java's standard rich-error model via StatusProto — the sa… | 3 dashes |
| Spring 140 | Throwing from a single field's resolver is exactly right: Spring for G… | 4 dashes |
| K8s policies deck 3 | Walk through the three environments as a risk gradient. Dev is where d… | 3 dashes |
| K8s policies deck 5 | Walk the RBAC matrix column by column. In dev, developers get full CRU… | 4 dashes |
| K8s policies deck 6 | This is the single highest-impact security measure you can apply to a… | 3 dashes |
| K8s policies deck 7 | The same default-deny baseline applies everywhere, but the allow rules… | 3 dashes |
| K8s policies deck 12 | L7 routing enables environment-safe deployments without modifying RBAC… | 3 dashes |
| K8s policies deck 13 | A well-governed namespace is a blast-radius boundary with four control… | 4 dashes |
| K8s policies deck 15 | Governance requires more than access control — it requires proof that… | 3 dashes |
| K8s policies deck 17 | Close with the priority-ordered checklist. First, apply default-deny N… | 3 dashes |
| text/k8s-environment-policies.md (docx copy):37 | Change velocity / High — deploy on every commit / Moderate — deploy on… | 3 dashes |
| lgtm-presentation/k8s-environment-policies.md:33 | Change velocity** / High — deploy on every commit / Moderate — deploy… | 3 dashes |

### quietly / silently (28 kept)

Reason: machine-subject (a producer, schema change or client that breaks or corrupts data without an error).

| Where (deck slide, or file:line) | Text | Kept as |
|---|---|---|
| C++ 37 | it, a producer can ship a breaking schema change and silently corrupt consumers across the fleet. With it, br | and silently |
| C++ 107 | es tag 4 with new semantics will misinterpret the data silently. For C++ specifically: protoc-generated C++ cl | data silently |
| C++ 111; .NET 113; Go 111; Python 111; Quarkus 111; Spring 111 | - Never break silently: deprecate with a reason, a replacement and a | break silently |
| .NET 110; Go 108; Python 108; Quarkus 108; Spring 108 | ) and its name permanently: nobody can reuse them and silently corrupt old data on the wire. We add currency a | and silently |
| .NET 113; Go 111; Python 111; Quarkus 111; Spring 111 | hecked in CI, never a reviewer remembering. Never break silently: deprecate with a reason, a replacement, a su | break silently |
| .NET 165; Go 157; Python 157; Quarkus 157; Spring 161 | pling stable: compatibility rules stop a producer from silently raising the integration strength on its consum | from silently |
| .NET 165; Go 157; Python 157; Quarkus 157; Spring 161 | lity gate is, in this language, a guard against a producer silently increasing integration strength on consume | producer silently |

### ALL-CAPS emphasis (27 kept)

Reasons: `design-label` (the red eyebrow `WORKFLOWS AND JOBS`; the scanner's list now includes AND) and `identifier`
(the SQL clause `ON CONFLICT ... DO NOTHING` / `DO UPDATE`).

| Where (deck slide, or file:line) | Text | Kept as |
|---|---|---|
| C++ 29 | cceeds; at-least-once delivery with an idempotent ON CONFLICT DO UPDATE is the standard pattern. PgTxn stands | ON CONFLICT DO UPDATE |
| C++ 31 | interesting part. Pair with idempotent consumers (ON CONFLICT DO NOTHING / DO UPDATE) and you get exactly-once | ON CONFLICT DO NOTHING |
| C++ 221; .NET 235; Go 221; Python 221; Quarkus 221; Spring 225 | write-back notes: the flusher upserts with INSERT ... ON CONFLICT (id) DO UPDATE | ON CONFLICT DO UPDATE |
| C++ 47; Go 47; Python 47; Quarkus 47; Spring 47 | ## [047] WORKFLOWS AND JOBS · Orchestration vs. choreography (sldId 302) | AND JOBS |
| C++ 48; Go 48; Python 48; Quarkus 48; Spring 48 | ## [048] WORKFLOWS AND JOBS · Choosing between the two (sldId 303) | AND JOBS |
| C++ 49; Go 49; Python 49; Quarkus 49; Spring 49 | ## [049] WORKFLOWS AND JOBS · Jobs, CronJobs and queue workers (sldId 304) | AND JOBS |
| .NET 49 | ## [049] WORKFLOWS AND JOBS · Orchestration vs. choreography (sldId 304) | AND JOBS |
| .NET 50 | ## [050] WORKFLOWS AND JOBS · Choosing between the two (sldId 305) | AND JOBS |
| .NET 51 | ## [051] WORKFLOWS AND JOBS · Jobs, CronJobs and queue workers (sldId 306) | AND JOBS |
| Go 36 | e idempotent. The example's consumer inserts with ON CONFLICT (order_id) DO NOTHING, so a duplicate is a no-op | ON CONFLICT |

### lie / lies / lying (person vs machine) (13 kept)

Reason: machine-subject (failures and remote calls that lie: gray failure).

| Where (deck slide, or file:line) | Text | Kept as |
|---|---|---|
| C++ 227; .NET 241; Go 227; Python 227; Quarkus 227; Spring 231 | - Some failures lie: a node passes its own health check while failing real t | lie |
| C++ 232 | > Gray failure is the failure that lies. The /healthz endpoint returns 200; real traffic is tim | lies |
| C++ 248; .NET 262; Go 248; Python 248; Quarkus 248; Spring 252 | rt: every remote call can succeed, fail, hang, or lie. Timeout everything; the default is often infinite. | lie |

### deliberate (adjective) (11 kept)

Reason: planned-stage (a planned transition strategy / intermediate state).

| Where (deck slide, or file:line) | Text | Kept as |
|---|---|---|
| C++ 205; Go 205; Python 205; Quarkus 205 | IX K · STRANGLER FIG · With a shared database — a deliberate intermediate state (sldId 460) | deliberate |
| .NET 90; Go 88; Python 88; Quarkus 88; Spring 88 | eration and the expiry. Strangler fig (auth) is a deliberate transition strategy; the gateway running translat | deliberate |
| .NET 219 | IX K · STRANGLER FIG · With a shared database — a deliberate intermediate state (sldId 474) | deliberate |
| Spring 209 | IX K · STRANGLER FIG · With a shared database — a deliberate intermediate state (sldId 464) | deliberate |

### exclamation in prose (11 kept)

Reason: quoted (book title 'Release It!', Nygard).

| Where (deck slide, or file:line) | Text | Kept as |
|---|---|---|
| C++ 248; .NET 262; Go 248; Python 248; Quarkus 248; Spring 252 | ddressing Cascading Failures, Handling Overload); 'Release It!' (Nygard — circuit breaker, bulkhead origin); t | 'Release It!' |
| .NET 262; Go 248; Python 248; Quarkus 248; Spring 252 | e the single best free resource; Michael Nygard's 'Release It!' is where the circuit breaker and bulkhead patt | 'Release It!' |

### parallel-number title (7 kept)

Reason: table-data (recorded result / a limit, not a synthetic parallel).

| Where (deck slide, or file:line) | Text | Kept as |
|---|---|---|
| C++ 281; .NET 312; Go 281; Python 281; Quarkus 281; Spring 285 | - 10 passed, 0 failed in all six languages (Fedora 44, Docker | 10 passed, 0 failed |
| lgtm-presentation/BUILD.md:51 | (at most 22 lines, 95 columns) and names the example in its first com | 22 lines, 95 columns |

### soft hype (6 kept)

Reason: survey-term ('tools landscape' is a survey of tools).

| Where (deck slide, or file:line) | Text | Kept as |
|---|---|---|
| C++ 39; Go 39; Python 39; Quarkus 39; Spring 39 | ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka, Pulsar, Flink, NiFi (sldId 294) | landscape |
| .NET 41 | ## [041] EVENT-DRIVEN · Event-driven tools landscape — Kafka, Pulsar, Flink, NiFi (sldId 296) | landscape |


### Kept by decision: section numbers with the concept named

About 120 notes and slide lines cross-reference a section by number and name ("section 11 (Observability)", "Covered in
depth in section 12 (Security)"). The decks number their sections on the agenda and every divider, and each reference
names the concept, so these are references to a labelled part of the deck, not positional language ("above", "next
slide"). They stay; the positional check in `validate_site.py` and `fixA_verify.py` reports 0.

## Final validation (2026-10-12)

Opus validation of the branch against main (2d8c2a8). Fix files, applied once to the committed decks after the earlier
ones: `Designing-Cloud-Native-APIs-Python.fix3.json`, `Quarkus.fix3`, `Spring.fix4`, `DotNet.fix4`, `Go.fix2`,
`Cpp.fix2` (each op keeps `_src`: `watch`, `tone`, `content`, `shutdown`, `registry`, `mine`, `figures`, `hop`).

- Content (examples/ is the authority): Apicurio v3 CreateVersion body on the CI-gate slides (Python, Go, C++; the raw
  schema body is the v2 shape) and `register` + `dryRun` instead of the deprecated `test-update` goal (Quarkus,
  Spring; apicurio-registry-maven-plugin 3.3.3); Python write-back, circuit-breaker import and consumer group id; Go
  write-back upsert; Quarkus Kafka Streams serdes; Spring gRPC stock update and saga class body, Undertow removed (Spring
  Boot 4); .NET saga COMPLETED, Kafka consumer notes, Apache KIE instead of Camunda, no commercial alternatives,
  SignalR backplane MIT, Polly BSD-3; C++ 12-factor service, librdkafka slide, bulkhead, shutdown, write-back rewritten
  from the examples; the Python shutdown slide follows `examples/21-graceful-shutdown/python`, whose SIGTERM handler now
  chains to uvicorn's (before, uvicorn never drained and the lifespan exit never ran).
- Appendix S: the one dangling reference (.NET notes, sldId 323) now names `examples/05-event-driven/dotnet`.
- Figures: gray failure, event sourcing vs streaming, tools landscape and coupling take the site figures (no baked-in
  ALL-CAPS emphasis); the hop-cost footer and the .NET Appendix J library table (Temporalio, MIT rows) re-rendered.
- Voice: 17 watch lines fixed (em-dash pileups, leaked authoring requests, soft positional references), first-person
  tone in the saga notes; survivors in "Watch-tier ledger (final validation)".
- Checks on the result: `deck_fit` 0 flags, `colour_audit` 0, `caps_audit` 0, `fixA_verify` all 0 on the six language
  decks; `validate_site.py` 0 errors; voice scan 0 ban-tier; `deck_text.py --check` ok.
- Site (`docs(site)`): the optional rows of `site-fixes.md` were real defects and are fixed (`02-pick-protocol`,
  `02-mesh-handles-wire`, `22-business-rule-routing`, `22-hop-cost` language-neutral, with their alt text and captions;
  `29-container-layers` label overlap via `scripts/gen_29_diagrams.py`); `_docs/09` codetabs and CI YAML send the v3
  CreateVersion body; codetabs in `_docs/01`, `02`, `05`, `06`, `12`, `21`, `23`, `24`, `25`, `26` follow the examples;
  `_docs/23` keeps Redis 8 (AGPLv3 option, as the examples deploy) and names Valkey as the BSD-3 drop-in; ALL-CAPS
  emphasis lowered in `11-signals-in-depth`, `11-sampling`, `25-cascading`, `25-amplification`.

## Example alignment (2026-10-12)

Three example fixes landed after the final validation: 937f8d7 (Example 01: `/readyz` answers 503 with the same
`"status": "down"` body when the database is down), 9676f32 (Example 21: one SIGTERM drives the whole drain:
readiness 503, `DRAIN_DELAY_SECONDS` = 5, stop accepting, in-flight drain bounded at 20 s, cleanup, exit 0, inside
the 30 s grace period) and ebca295 (Example 25: `PUT /write-back/metrics/{id}` answers 202 Accepted; the flusher
upserts and re-queues failures with a `metric:attempts` hash, a `metric:failed` set after five attempts and a
backoff of 2, 4 and 8 s). Two older divergences in the Quarkus deck go with them: the health slide used SmallRye
Health and the outbox slide the Debezium outbox extension, while `examples/01/quarkus` hand-writes `/healthz` and
`/readyz` and `examples/04-data/quarkus` inserts into the outbox table over JDBC. `examples/` is the authority.

Generator: `tools/align_build.py` (code, captions, chips and notes per slide; checks 95 columns and each box's
line limit, max(22, current lines) capped by the box capacity at its current font, so no font was shrunk) and
`tools/align_site.py` (the same line lists into the site codetabs; Go with tab indentation). Fix files, applied
once to the committed decks after the earlier ones (each op carries `_src: align`):

| Deck | File | Slides (number / sldId) |
|---|---|---|
| Python | `Designing-Cloud-Native-APIs-Python.fix4.json` | 14/269 (503 line, notes), 164/419, 221/476, 245/500 |
| Go | `Designing-Cloud-Native-APIs-Go.fix3.json` | 14/269 (now the example's handlers; the Kafka check and `errors.Join` were not in it), 164/419, 221/476, 245/500 |
| C++ | `Designing-Cloud-Native-APIs-Cpp.fix3.json` | 14/269, 164/419 (watcher thread, drain delay, bounded wait, `app().quit()`), 221/476, 245/500 |
| Quarkus | `Designing-Cloud-Native-APIs-Quarkus.fix4.json` | 14/269 (hand-written `HealthResource`), 32/287 (JDBC outbox), 164/419 (`Signal` handler, `Quarkus.asyncExit`), 221/476 (JDBC per-id upsert), 245/500 |
| Spring | `Designing-Cloud-Native-APIs-Spring.fix5.json` | 14/269 (hand-written `HealthController`), 168/423 (`Signal` handler, `System.exit`), 225/480 (`JdbcClient`, no ShedLock), 249/504 |
| .NET | `Designing-Cloud-Native-APIs-DotNet.fix5.json` | 15/270 (`MapGet` probes), 172/427 (`ManualLifetime`, `PosixSignalRegistration`, `StopApplication`), 234/489 (notes), 235/490 (title, the example's `Task.Run` flusher), 259/514 |

The Appendix M shutdown recaps (245, Spring 249, .NET 259) follow Example 21 as well: they showed the old budgets,
a readiness flip in the lifespan exit (Python), SmallRye Health (Quarkus) or Actuator (Spring). The other Appendix H
slides and notes already describe one SIGTERM and stay. `caps_audit.py` gains HINCRBY, HDEL and SREM (Redis
commands) and JTA (an acronym) on its allowlist.

Checks on scratch copies, then on the committed decks: dry run and apply `ok`; `deck_fit` 0 flags on all six (after
two fit fixes in the generator: the Quarkus outbox chip shortened to one line, the first Spring write-back line
kept clear of the chip); `colour_audit` 0, `caps_audit` 0, `fixA_verify` all 0; every changed slide rendered
(`deck_render.sh`) and read; the committed decks have the same parts as the verified scratch copies;
`validate_site.py` 0 errors; voice scan 0 ban-tier; `deck_text.py --check` ok. Watch tier: 342 lines, unchanged in
number; the em-dash pileups of the .NET 172 and Go/Python 221 notes are gone and the write-back notes of .NET 235,
Quarkus 221 and Spring 225 join the `ON CONFLICT` identifier row (ledger updated).

Site: `_docs/01` (all six codetabs follow Example 01: 503 on the down path, hand-written probes in Spring, Quarkus
and .NET, the Go handlers; the prose says the probe reads the status code), `_docs/21` (Spring, Quarkus, .NET, C++
and Go codetabs follow Example 21; the prose describes the single SIGTERM, the drain delay and the 20 s bound),
`_docs/25` (the six write-back codetabs follow Example 25), and the Example 01 C++ README (503 on the down path).
Open: the `_docs/01` footer still says 10/10 checks, while `examples/01-cloud-native-principles/verify.sh` now has
14; the count needs a green run before it changes.

