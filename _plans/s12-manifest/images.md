# S12 image audit (language decks)

Every content image of the six Designing-Cloud-Native-APIs decks, deduplicated by content hash (243 unique images; logos and section panels excluded). The K8s-Environment-Access-Policies and Network-Policy-Process-Advisory images belong to the policy batch; `apxo-ci-gate` and `apxo-black-box` are replaced in the Appendix O ops (27-ci-gate, 27-black-box).

Checks: old container engine, versions against the pins, MassTransit, Poetry, Faust, modern-cpp-kafka, libpqxx, kafka-ui, kubeval, graphql-go, five vs six implementations, positional words, ban-tier phrases, topic names, and a library that is not the deck language's locked one. Watch-tier wording inside figures (ALL-CAPS emphasis such as 'NOT mutually exclusive', 'actually', 'simply') is left: the scanner does not read images, and redrawing every figure for watch-tier wording is out of proportion; listed as a follow-up.

Ops: `W/ops-15-images/<deck>.json` (replace_picture by sldId and shape id; two caption set_text ops). Replacements in `lgtm-presentation/edits/png/`: site figures rendered from `assets/diagrams/` (cairosvg 2.9.1, 1400 px, the arrow glyph written as `->` because cairosvg has no fallback font for it), site figures with per-language label substitutions and authored figures, both with their SVG source in `lgtm-presentation/edits/png/src/` (generators: `gen_images.py` and `gen_ops.py` in the session scratchpad `s12/manifest/fork-images/`; the planner copies them to `_plans/s12-manifest/tools/`).

## Replacements

| Image | Verdict | Replacement per deck:slide |
|---|---|---|
| `01b-windows-to-k8s-bridge.png` (c4bbf68a) | stale: 'MassTransit sagas'; Serilog | DotNet:8->01b-windows-to-k8s-bridge-dn |
| `03-comm-protocol-matrix.png` (0aa9f38c) | wrong language: Python labels in Go; Quarkus labels in .NET and Spring; ok in Python and Quarkus | DotNet:17->02-pick-protocol-dotnet Spring:16->02-pick-protocol-spring |
| `03-comm-protocol-matrix.png` (ae3a36ec) | wrong language: Python labels in Go; Quarkus labels in .NET and Spring; ok in Python and Quarkus | Go:16->02-pick-protocol-go |
| `05-comm-service-mesh.png` (34b40288) | wrong language (as protocol matrix) | DotNet:21->02-mesh-handles-wire-dotnet Spring:20->02-mesh-handles-wire-spring |
| `05-comm-service-mesh.png` (a7e0001b) | wrong language (as protocol matrix) | Go:20->02-mesh-handles-wire-go |
| `06-composition-federation.png` (0ba5c3cd) | wrong language (as protocol matrix) | Go:23->03-composition |
| `06-composition-federation.png` (bc342668) | wrong language (as protocol matrix) | DotNet:24->03-composition Spring:23->03-composition |
| `08b-data-cqrs.png` (819ab318) | stale: 'the next slide' (positional), 'genuinely' (ban) | DotNet:30->04-cqrs Go:28->04-cqrs Python:28->04-cqrs Quarkus:28->04-cqrs Spring:28->04-cqrs |
| `08b-data-cqrs.png` (87ee7f25) | stale: 'the next slide' (positional), 'genuinely' (ban) | Cpp:28->04-cqrs |
| `08c-data-log-tailing.png` (6dcd3755) | stale: '(next slide)' (positional) | Cpp:30->04-log-tailing |
| `08c-data-log-tailing.png` (a1d47b26) | stale: '(next slide)' (positional) | DotNet:32->04-log-tailing Go:30->04-log-tailing Python:30->04-log-tailing Quarkus:30->04-log-tailing Spring:30->04-log-tailing |
| `110-failure-taxonomy.png` (168bd1d1) | stale: 'the rest of this appendix' (ban) | DotNet:242->25-failure-taxonomy Go:228->25-failure-taxonomy Python:228->25-failure-taxonomy Quarkus:228->25-failure-taxonomy Spring:232->25-failure-taxonomy |
| `110-failure-taxonomy.png` (d03d5c63) | stale: 'the rest of this appendix' (ban) | Cpp:228->25-failure-taxonomy |
| `117-failure-circuit-breaker.png` (c0d197f9) | Go deck: library list without sony/gobreaker; ok elsewhere | Go:240->25-circuit-breaker |
| `14-stream-topology.png` (36b98911) | Python/Go copy: 'Faust/Kafka Streams style' (faust-streaming; goka in Go). .NET/Quarkus/Spring copy: ok | Go:42->06-derive-streams Python:42->06-derive-streams |
| `15-stream-keda-scaling.png` (d589d624) | wrong language: FastAPI pods in Go, Quarkus pods in .NET and Spring; ok in Python and Quarkus | DotNet:46->06-scale-on-lag Spring:44->06-scale-on-lag |
| `15-stream-keda-scaling.png` (da1ae4af) | wrong language: FastAPI pods in Go, Quarkus pods in .NET and Spring; ok in Python and Quarkus | Go:44->06-scale-on-lag |
| `23-anti-patterns-grid.png` (db3eaabc) | defect: box text broken mid-word | DotNet:93->13-antipatterns-grid Go:91->13-antipatterns-grid Python:91->13-antipatterns-grid Quarkus:91->13-antipatterns-grid Spring:91->13-antipatterns-grid |
| `23-anti-patterns-grid.png` (e35ef8be) | defect: box text broken mid-word | Cpp:91->13-antipatterns-grid |
| `29-container-layers.png` (6cd65c1b) | stale: old container engine named; separate restore step | DotNet:293->29-container-layers |
| `29-dotnet-compilation.png` (f0d220cd) | defect: missing-glyph boxes | DotNet:289->29-dotnet-compilation |
| `29-kestrel-pipeline.png` (f5cec157) | refresh from site (consistency) | DotNet:291->29-kestrel-pipeline |
| `33-appD-state-options.png` (c8676b1f) | Python copy shown in the Go deck ('Where a Python saga keeps its state'); ok in Python | Go:121->17-saga-state |
| `33-appD-state-options-sb.png` (001c8b8b) | Spring Statemachine named as a workflow engine (decision 6: archived upstream, not offered) | Spring:121->17-saga-state |
| `63-appD-statemachine.png` (c362e9a3) | Spring Statemachine figure (decision 6) | Spring:129->17-sagas-architecture (from `examples/17-sagas/architecture.svg`) |
| `42-twelve-factor-map-py.png` (77e98986) | stale: Poetry (pip + requirements.txt); Python tooling in the Go deck | Go:13->01-factors-mapped-go Python:13->01-factors-mapped-py |
| `54-appI-stack-cpp.png` (cde1d928) | stale: modern-cpp-kafka | Cpp:172->22-l7-layers |
| `54-appI-stack-py.png` (ed5dc6a5) | wrong language in the Go deck (FastAPI + durable-rules); ok in Python | Go:172->22-l7-layers |
| `54-appI-stack-sb.png` (957a85d5) | wrong language in the .NET deck (Spring Boot + Camel + Drools); ok in Spring | DotNet:180->22-l7-layers |
| `55-appI-journey.png` (aa7e6af7) | stale: 'each layer earns its place' (ban) | DotNet:181->22-l7-journey Go:173->22-l7-journey Python:173->22-l7-journey Quarkus:173->22-l7-journey Spring:177->22-l7-journey |
| `55-appI-journey.png` (d6bd2e08) | stale: 'each layer earns its place' (ban) | Cpp:173->22-l7-journey |
| `58-appI-masstransit-routingslip-dn.png` (089c9839) | stale: MassTransit | DotNet:195->22-business-rule-routing-dotnet |
| `59-appI-latency-cpp.png` (1dff3a8e) | stale: 'every hop must earn its place' (ban); rule-engine row per language | Cpp:190->22-hop-cost-cpp |
| `59-appI-latency-py.png` (30a50bbf) | stale: 'every hop must earn its place' (ban); rule-engine row per language | Go:190->22-hop-cost-go Python:190->22-hop-cost |
| `59-appI-latency-sb.png` (6f0c88a1) | stale: 'every hop must earn its place' (ban); rule-engine row per language | DotNet:198->22-hop-cost-nrules Quarkus:190->22-hop-cost-drools Spring:194->22-hop-cost-drools |
| `60-appI-east-west.png` (6dc23201) | stale: 'for free' (ban) | Cpp:192->22-east-west |
| `60-appI-east-west.png` (8badba43) | stale: 'for free' (ban) | DotNet:200->22-east-west Go:192->22-east-west Python:192->22-east-west Quarkus:192->22-east-west Spring:196->22-east-west |
| `61-appI-cpp-router.png` (59c9c14e) | stale: modern-cpp-kafka | Cpp:187->22-business-rule-routing-cpp |
| `61-appI-python-router.png` (fc30e611) | wrong language in the Go deck; ok in Python | Go:187->22-business-rule-routing-go |
| `63-appD-stateless-dn.png` (66042487) | stale: 'MassTransit Sagas'; '@Transactional' | DotNet:133->63-appD-stateless-dn |
| `70-appJ-pinned-libraries-dn.png` (854b9f97) | stale: MassTransit row; 'Every entry above' | DotNet:207->70-appJ-pinned-libraries-dn |
| `71-appJ-pinned-platform-dn.png` (89cd4fd4) | stale: Redis license (Redis 8 is RSALv2/SSPLv1/AGPLv3) | DotNet:208->71-appJ-pinned-platform-dn |
| `72-appJ-migration-reference-dn.png` (5d457c4d) | stale: MassTransit in three rows | DotNet:209->72-appJ-migration-reference-dn |
| `86-appK-strangler-shared-database.png` (81c3d748) | stale: '(decomposed DB above)' (positional) | Cpp:205->24-shared-database |
| `86-appK-strangler-shared-database.png` (cd33b74a) | stale: '(decomposed DB above)' (positional) | DotNet:219->24-shared-database Go:205->24-shared-database Python:205->24-shared-database Quarkus:205->24-shared-database Spring:209->24-shared-database |

## Captions changed with the figure

- C++ slide 187 (sldId 442): 'modern-cpp-kafka does the dispatch' becomes 'rdkafka++ (librdkafka) does the dispatch'.
- .NET slide 195 (sldId 450): caption rewritten for NRules + Confluent.Kafka. The slide title still names MassTransit RoutingSlip; the .NET batch must retitle it (for example '.NET + NRules: rule-based routing').

## Full coverage

| Group | Image (hash) | Used on deck:slide | Verdict |
|---|---|---|---|
| Main sections | `00-patterns-literacy-stack.png` (378aef87) | DotNet 5 Go 5 Python 5 Quarkus 5 Spring 5 | ok |
| Main sections | `00-patterns-literacy-stack.png` (e4f0f2d4) | Cpp 5 | ok |
| Main sections | `01-cloud-native-pillars.png` (28b54bf4) | DotNet 9 Go 8 Python 8 Quarkus 8 Spring 8 | ok |
| Main sections | `01b-windows-to-k8s-bridge.png` (c4bbf68a) | DotNet 8 | stale: 'MassTransit sagas'; Serilog |
| Main sections | `02-canonical-system.png` (6abb3745) | DotNet 6 Go 6 Python 6 Quarkus 6 Spring 6 | ok |
| Main sections | `02-canonical-system.png` (726a15e7) | Cpp 6 | ok |
| Main sections | `03-comm-protocol-matrix-cpp.png` (fa396f9f) | Cpp 16 | ok |
| Main sections | `03-comm-protocol-matrix.png` (0aa9f38c) | DotNet 17 Quarkus 16 Spring 16 | wrong language: Python labels in Go; Quarkus labels in .NET and Spring; ok in Python and Quarkus |
| Main sections | `03-comm-protocol-matrix.png` (ae3a36ec) | Go 16 Python 16 | wrong language: Python labels in Go; Quarkus labels in .NET and Spring; ok in Python and Quarkus |
| Main sections | `04-comm-sync-async.png` (1b292f56) | Cpp 19 | ok |
| Main sections | `04-comm-sync-async.png` (de5f7860) | DotNet 20 Go 19 Python 19 Quarkus 19 Spring 19 | ok |
| Main sections | `05-comm-service-mesh-cpp.png` (96fa621b) | Cpp 20 | ok |
| Main sections | `05-comm-service-mesh.png` (34b40288) | DotNet 21 Quarkus 20 Spring 20 | wrong language (as protocol matrix) |
| Main sections | `05-comm-service-mesh.png` (a7e0001b) | Go 20 Python 20 | wrong language (as protocol matrix) |
| Main sections | `06-composition-federation-cpp.png` (a41edc2b) | Cpp 23 | ok |
| Main sections | `06-composition-federation.png` (0ba5c3cd) | Go 23 Python 23 | wrong language (as protocol matrix) |
| Main sections | `06-composition-federation.png` (bc342668) | DotNet 24 Quarkus 23 Spring 23 | wrong language (as protocol matrix) |
| Main sections | `07-composition-patterns.png` (152860f0) | DotNet 26 Go 25 Python 25 Quarkus 25 Spring 25 | ok |
| Main sections | `07-composition-patterns.png` (354ccced) | Cpp 25 | ok |
| Main sections | `08-data-per-service-db.png` (6dd7f518) | DotNet 29 Go 27 Python 27 Quarkus 27 Spring 27 | ok |
| Main sections | `08-data-per-service-db.png` (c3431cf9) | Cpp 27 | ok |
| Main sections | `08b-data-cqrs.png` (819ab318) | DotNet 30 Go 28 Python 28 Quarkus 28 Spring 28 | stale: 'the next slide' (positional), 'genuinely' (ban) |
| Main sections | `08b-data-cqrs.png` (87ee7f25) | Cpp 28 | stale: 'the next slide' (positional), 'genuinely' (ban) |
| Main sections | `08c-data-log-tailing.png` (6dcd3755) | Cpp 30 | stale: '(next slide)' (positional) |
| Main sections | `08c-data-log-tailing.png` (a1d47b26) | DotNet 32 Go 30 Python 30 Quarkus 30 Spring 30 | stale: '(next slide)' (positional) |
| Main sections | `09-data-outbox-cdc.png` (0d9014a9) | Cpp 31 | ok |
| Main sections | `09-data-outbox-cdc.png` (581ddd6e) | DotNet 33 Go 31 Python 31 Quarkus 31 Spring 31 | ok |
| Main sections | `10-data-saga.png` (0f8dde9b) | DotNet 35 Go 33 Python 33 Quarkus 33 Spring 33 | ok |
| Main sections | `10-data-saga.png` (1b6d1d7a) | Cpp 33 | ok |
| Main sections | `11-event-topology.png` (350a1df4) | DotNet 37 Go 35 Python 35 Quarkus 35 Spring 35 | ok |
| Main sections | `11-event-topology.png` (db4a1e82) | Cpp 35 | ok |
| Main sections | `11b-event-sourcing-vs-streaming.png` (26c99263) | Cpp 38 | ok |
| Main sections | `11b-event-sourcing-vs-streaming.png` (55032ecc) | DotNet 40 Go 38 Python 38 Quarkus 38 Spring 38 | ok |
| Main sections | `11c-event-tooling-landscape.png` (4bac32ca) | DotNet 41 Go 39 Python 39 Quarkus 39 Spring 39 | ok |
| Main sections | `11c-event-tooling-landscape.png` (f866fc13) | Cpp 39 | ok |
| Main sections | `12-event-schema-registry.png` (8c1e4628) | DotNet 39 Go 37 Python 37 Quarkus 37 Spring 37 | ok |
| Main sections | `12-event-schema-registry.png` (ba712841) | Cpp 37 | ok |
| Main sections | `13-event-log-replay.png` (a3193415) | Cpp 40 | ok |
| Main sections | `13-event-log-replay.png` (e86ff185) | DotNet 42 Go 40 Python 40 Quarkus 40 Spring 40 | ok |
| Main sections | `14-stream-topology-cpp.png` (07925fb2) | Cpp 42 | ok |
| Main sections | `14-stream-topology.png` (36b98911) | Go 42 Python 42 | Python/Go copy: 'Faust/Kafka Streams style' (faust-streaming; goka in Go). .NET/Quarkus/Spring copy: ok |
| Main sections | `14-stream-topology.png` (8fb5e970) | DotNet 44 Quarkus 42 Spring 42 | Python/Go copy: 'Faust/Kafka Streams style' (faust-streaming; goka in Go). .NET/Quarkus/Spring copy: ok |
| Main sections | `15-stream-keda-scaling-cpp.png` (24a1aadd) | Cpp 44 | ok |
| Main sections | `15-stream-keda-scaling.png` (d589d624) | DotNet 46 Quarkus 44 Spring 44 | wrong language: FastAPI pods in Go, Quarkus pods in .NET and Spring; ok in Python and Quarkus |
| Main sections | `15-stream-keda-scaling.png` (da1ae4af) | Go 44 Python 44 | wrong language: FastAPI pods in Go, Quarkus pods in .NET and Spring; ok in Python and Quarkus |
| Main sections | `16-workflows-orchestration.png` (0492e3d2) | DotNet 49 Go 47 Python 47 Quarkus 47 Spring 47 | ok |
| Main sections | `16-workflows-orchestration.png` (72c6e641) | Cpp 47 | ok |
| Main sections | `17-workflows-jobs.png` (12ab57e6) | Cpp 49 | ok |
| Main sections | `17-workflows-jobs.png` (ad0c7d76) | DotNet 51 Go 49 Python 49 Quarkus 49 Spring 49 | ok |
| Main sections | `18-api-management-stack.png` (48f50c69) | Cpp 51 | ok |
| Main sections | `18-api-management-stack.png` (fb65a7ba) | DotNet 53 Go 51 Python 51 Quarkus 51 Spring 51 | ok |
| Main sections | `19-api-registry-apicurio.png` (3430e32e) | Cpp 54 | ok |
| Main sections | `19-api-registry-apicurio.png` (bebfa151) | DotNet 56 Go 54 Python 54 Quarkus 54 Spring 54 | ok |
| Main sections | `20-api-metadata-openmetadata.png` (4e333d5e) | Cpp 57 | ok |
| Main sections | `20-api-metadata-openmetadata.png` (b110fe44) | DotNet 59 Go 57 Python 57 Quarkus 57 Spring 57 | ok |
| Main sections | `21-observability-pillars.png` (74ce993f) | Cpp 60 | ok |
| Main sections | `21-observability-pillars.png` (d87306f9) | DotNet 62 Go 60 Python 60 Quarkus 60 Spring 60 | ok |
| Main sections | `21b-observability-signals.png` (4ba0767f) | Cpp 61 | ok |
| Main sections | `21b-observability-signals.png` (56efca31) | DotNet 63 Go 61 Python 61 Quarkus 61 Spring 61 | ok |
| Main sections | `21c-observability-correlation.png` (6b2db016) | DotNet 67 Go 65 Python 65 Quarkus 65 Spring 65 | ok |
| Main sections | `21c-observability-correlation.png` (b5658885) | Cpp 65 | ok |
| Main sections | `21d-observability-sampling.png` (010bc155) | Cpp 68 | ok |
| Main sections | `21d-observability-sampling.png` (139e850c) | DotNet 70 Go 68 Python 68 Quarkus 68 Spring 68 | ok |
| Main sections | `22-observability-trace.png` (16e5b505) | Cpp 67 | ok |
| Main sections | `22-observability-trace.png` (9325b031) | DotNet 69 Go 67 Python 67 Quarkus 67 Spring 67 | ok |
| Main sections | `23-anti-patterns-grid.png` (db3eaabc) | DotNet 93 Go 91 Python 91 Quarkus 91 Spring 91 | defect: box text broken mid-word |
| Main sections | `23-anti-patterns-grid.png` (e35ef8be) | Cpp 91 | defect: box text broken mid-word |
| Security (section 12) | `100-security-4cs.png` (55805502) | DotNet 74 Go 72 Python 72 Quarkus 72 Spring 72 | ok |
| Security (section 12) | `100-security-4cs.png` (b4801f82) | Cpp 72 | ok |
| Security (section 12) | `101-security-sidecar.png` (d7ce206e) | DotNet 77 Go 75 Python 75 Quarkus 75 Spring 75 | ok |
| Security (section 12) | `101-security-sidecar.png` (e8e5ddb3) | Cpp 75 | ok |
| Security (section 12) | `102-security-valet-key.png` (3ee84b4f) | DotNet 79 Go 77 Python 77 Quarkus 77 Spring 77 | ok |
| Security (section 12) | `102-security-valet-key.png` (be76388f) | Cpp 77 | ok |
| Security (section 12) | `103-security-zero-trust.png` (3550f9a2) | Cpp 80 | ok |
| Security (section 12) | `103-security-zero-trust.png` (e68ee70c) | DotNet 82 Go 80 Python 80 Quarkus 80 Spring 80 | ok |
| Security (section 12) | `104-security-policy-as-code.png` (b338dd3c) | DotNet 84 Go 82 Python 82 Quarkus 82 Spring 82 | ok |
| Security (section 12) | `104-security-policy-as-code.png` (e600c180) | Cpp 82 | ok |
| Security (section 12) | `105-security-bulkhead.png` (53a34471) | Cpp 84 | ok |
| Security (section 12) | `105-security-bulkhead.png` (91df0abf) | DotNet 86 Go 84 Python 84 Quarkus 84 Spring 84 | ok |
| Security (section 12) | `106-security-claim-check.png` (5719389f) | DotNet 88 Go 86 Python 86 Quarkus 86 Spring 86 | ok |
| Security (section 12) | `106-security-claim-check.png` (9556d595) | Cpp 86 | ok |
| Appendices A-I | `24-appA-paradigms.png` (28283e3b) | Cpp 99 | ok |
| Appendices A-I | `24-appA-paradigms.png` (b1b5f6bc) | DotNet 101 Go 99 Python 99 Quarkus 99 Spring 99 | ok |
| Appendices A-I | `25-appA-fetching.png` (8c7daf02) | DotNet 102 Go 100 Python 100 Quarkus 100 Spring 100 | ok |
| Appendices A-I | `25-appA-fetching.png` (ab61389d) | Cpp 100 | ok |
| Appendices A-I | `26-appA-transport.png` (1a9b3321) | DotNet 103 Go 101 Python 101 Quarkus 101 Spring 101 | ok |
| Appendices A-I | `26-appA-transport.png` (572614c5) | Cpp 101 | ok |
| Appendices A-I | `27-appB-rest-versioning.png` (21db182c) | DotNet 107 Go 105 Python 105 Quarkus 105 Spring 105 | ok |
| Appendices A-I | `27-appB-rest-versioning.png` (c56f5f4f) | Cpp 105 | ok |
| Appendices A-I | `28-appB-proto-evolution.png` (57f38e31) | Cpp 107 | ok |
| Appendices A-I | `28-appB-proto-evolution.png` (dc575449) | DotNet 109 Go 107 Python 107 Quarkus 107 Spring 107 | ok |
| Appendices A-I | `29-appB-graphql-evolution.png` (3684db60) | Cpp 109 | ok |
| Appendices A-I | `29-appB-graphql-evolution.png` (cb0641a1) | DotNet 111 Go 109 Python 109 Quarkus 109 Spring 109 | ok |
| Appendices A-I | `29-container-layers.png` (6cd65c1b) | DotNet 293 | stale: old container engine named; separate restore step |
| Appendices A-I | `29-dotnet-compilation.png` (f0d220cd) | DotNet 289 | defect: missing-glyph boxes |
| Appendices A-I | `29-kestrel-pipeline.png` (f5cec157) | DotNet 291 | refresh from site (consistency) |
| Appendices A-I | `30-appC-pinning.png` (5235efd4) | DotNet 116 Go 114 Python 114 Quarkus 114 Spring 114 | ok |
| Appendices A-I | `30-appC-pinning.png` (81a66219) | Cpp 114 | ok |
| Appendices A-I | `30-blazor-circuit.png` (aae8acc9) | DotNet 298 | ok |
| Appendices A-I | `30-signalr-backplane.png` (3b8986c8) | DotNet 300 | ok |
| Appendices A-I | `31-appC-backplane.png` (cc7153be) | Cpp 116 | ok |
| Appendices A-I | `31-appC-backplane.png` (fdfa545c) | DotNet 118 Go 116 Python 116 Quarkus 116 Spring 116 | ok |
| Appendices A-I | `32-appC-reconnect.png` (7ee3e7b0) | DotNet 120 Go 118 Python 118 Quarkus 118 Spring 118 | ok |
| Appendices A-I | `32-appC-reconnect.png` (a53c653c) | Cpp 118 | ok |
| Appendices A-I | `32b-appC-blazor-architectures.png` (86ed6728) | DotNet 122 | ok |
| Appendices A-I | `33-appD-state-options-cpp.png` (a4b0829c) | Cpp 121 | ok |
| Appendices A-I | `33-appD-state-options-dn.png` (b9f6e6e9) | DotNet 125 | ok |
| Appendices A-I | `33-appD-state-options-sb.png` (001c8b8b) | Spring 121 | replaced (decision 6): names Spring Statemachine |
| Appendices A-I | `33-appD-state-options.png` (2ba5a435) | Quarkus 121 | Python copy shown in the Go deck ('Where a Python saga keeps its state'); ok in Python |
| Appendices A-I | `33-appD-state-options.png` (c8676b1f) | Go 121 Python 121 | Python copy shown in the Go deck ('Where a Python saga keeps its state'); ok in Python |
| Appendices A-I | `34-appD-compensation.png` (110f25ac) | Cpp 123 | ok |
| Appendices A-I | `34-appD-compensation.png` (bfccddec) | DotNet 127 Go 123 Python 123 Quarkus 123 Spring 123 | ok |
| Appendices A-I | `35-appD-data-dependency.png` (5d511fb1) | Cpp 125 | ok |
| Appendices A-I | `35-appD-data-dependency.png` (a91b9510) | DotNet 129 Go 125 Python 125 Quarkus 125 Spring 125 | ok |
| Appendices A-I | `36-appE-error-shape.png` (3cfd9ad9) | DotNet 136 Go 128 Python 128 Quarkus 128 Spring 132 | ok |
| Appendices A-I | `36-appE-error-shape.png` (4bf7497a) | Cpp 128 | ok |
| Appendices A-I | `37-appE-rest-errors.png` (120560cd) | Cpp 129 | ok |
| Appendices A-I | `37-appE-rest-errors.png` (a30b87c1) | DotNet 137 Go 129 Python 129 Quarkus 129 Spring 133 | ok |
| Appendices A-I | `38-appE-grpc-errors.png` (d871dbc8) | Cpp 131 | ok |
| Appendices A-I | `38-appE-grpc-errors.png` (f8237add) | DotNet 139 Go 131 Python 131 Quarkus 131 Spring 135 | ok |
| Appendices A-I | `39-appE-kafka-errors.png` (3156a5c7) | Cpp 133 | ok |
| Appendices A-I | `39-appE-kafka-errors.png` (685beb18) | DotNet 141 Go 133 Python 133 Quarkus 133 Spring 137 | ok |
| Appendices A-I | `40-appE-graphql-errors.png` (0745909e) | Cpp 135 | ok |
| Appendices A-I | `40-appE-graphql-errors.png` (107b29df) | DotNet 143 Go 135 Python 135 Quarkus 135 Spring 139 | ok |
| Appendices A-I | `41-appE-retry-storm.png` (0093c188) | DotNet 145 Go 137 Python 137 Quarkus 137 Spring 141 | ok |
| Appendices A-I | `41-appE-retry-storm.png` (7b988b0f) | Cpp 137 | ok |
| Appendices A-I | `42-twelve-factor-map-cpp.png` (3a41b0f1) | Cpp 13 | ok |
| Appendices A-I | `42-twelve-factor-map-py.png` (77e98986) | Go 13 Python 13 | stale: Poetry (pip + requirements.txt); Python tooling in the Go deck |
| Appendices A-I | `42-twelve-factor-map-sb.png` (9b59087e) | Spring 13 | ok |
| Appendices A-I | `42-twelve-factor-map-sb.png` (cc145bf0) | DotNet 14 | ok |
| Appendices A-I | `43-twelve-factor-map-qk.png` (e789dd13) | Quarkus 13 | ok |
| Appendices A-I | `44-twelve-factor-list.png` (9df816db) | Cpp 12 | ok |
| Appendices A-I | `44-twelve-factor-list.png` (f76e7d67) | DotNet 13 Go 12 Python 12 Quarkus 12 Spring 12 | ok |
| Appendices A-I | `45-appF-ddd-strategic.png` (1589830f) | DotNet 149 Go 141 Python 141 Quarkus 141 Spring 145 | ok |
| Appendices A-I | `45-appF-ddd-strategic.png` (5901f132) | Cpp 141 | ok |
| Appendices A-I | `46-appF-context-map.png` (4e484825) | DotNet 151 Go 143 Python 143 Quarkus 143 Spring 147 | ok |
| Appendices A-I | `46-appF-context-map.png` (f6dbd6a7) | Cpp 143 | ok |
| Appendices A-I | `47-appF-hexagonal.png` (144edc2b) | Cpp 145 | ok |
| Appendices A-I | `47-appF-hexagonal.png` (321aefda) | DotNet 153 Go 145 Python 145 Quarkus 145 Spring 149 | ok |
| Appendices A-I | `48-appG-dimensions.png` (0edef599) | Cpp 151 | ok |
| Appendices A-I | `48-appG-dimensions.png` (badc8514) | DotNet 159 Go 151 Python 151 Quarkus 151 Spring 155 | ok |
| Appendices A-I | `49-appG-strength.png` (b5c7885c) | Cpp 153 | ok |
| Appendices A-I | `49-appG-strength.png` (bb132c93) | DotNet 161 Go 153 Python 153 Quarkus 153 Spring 157 | ok |
| Appendices A-I | `50-appG-balance.png` (56f5aa2c) | DotNet 163 Go 155 Python 155 Quarkus 155 Spring 159 | ok |
| Appendices A-I | `50-appG-balance.png` (5ccc809a) | Cpp 155 | ok |
| Appendices A-I | `51-appH-termination.png` (07f0dab6) | Cpp 161 | ok |
| Appendices A-I | `51-appH-termination.png` (0fc5cd54) | DotNet 169 Go 161 Python 161 Quarkus 161 Spring 165 | ok |
| Appendices A-I | `52-appH-workloads.png` (18f9e907) | DotNet 171 Go 163 Python 163 Quarkus 163 Spring 167 | ok |
| Appendices A-I | `52-appH-workloads.png` (615c462b) | Cpp 163 | ok |
| Appendices A-I | `53-appI-l4-vs-l7.png` (1d89d2be) | DotNet 178 Go 170 Python 170 Quarkus 170 Spring 174 | ok |
| Appendices A-I | `53-appI-l4-vs-l7.png` (6aa00289) | Cpp 170 | ok |
| Appendices A-I | `54-appI-stack-cpp.png` (cde1d928) | Cpp 172 | stale: modern-cpp-kafka |
| Appendices A-I | `54-appI-stack-py.png` (ed5dc6a5) | Go 172 Python 172 | wrong language in the Go deck (FastAPI + durable-rules); ok in Python |
| Appendices A-I | `54-appI-stack-qk.png` (d3e5a6ab) | Quarkus 172 | ok |
| Appendices A-I | `54-appI-stack-sb.png` (957a85d5) | DotNet 180 Spring 176 | wrong language in the .NET deck (Spring Boot + Camel + Drools); ok in Spring |
| Appendices A-I | `55-appI-journey.png` (aa7e6af7) | DotNet 181 Go 173 Python 173 Quarkus 173 Spring 177 | stale: 'each layer earns its place' (ban) |
| Appendices A-I | `55-appI-journey.png` (d6bd2e08) | Cpp 173 | stale: 'each layer earns its place' (ban) |
| Appendices A-I | `56-appI-sticky.png` (b0fed89a) | Cpp 179 | ok |
| Appendices A-I | `56-appI-sticky.png` (e370b70c) | DotNet 187 Go 179 Python 179 Quarkus 179 Spring 183 | ok |
| Appendices A-I | `57-appI-steering.png` (3b315a29) | DotNet 189 Go 181 Python 181 Quarkus 181 Spring 185 | ok |
| Appendices A-I | `57-appI-steering.png` (ce980f5a) | Cpp 181 | ok |
| Appendices A-I | `58-appI-camel-drools-sb.png` (1aadf761) | Spring 191 | ok |
| Appendices A-I | `58-appI-camel-drools.png` (196681c3) | Quarkus 187 | ok |
| Appendices A-I | `58-appI-masstransit-routingslip-dn.png` (089c9839) | DotNet 195 | stale: MassTransit |
| Appendices A-I | `59-appI-latency-cpp.png` (1dff3a8e) | Cpp 190 | stale: 'every hop must earn its place' (ban); rule-engine row per language |
| Appendices A-I | `59-appI-latency-py.png` (30a50bbf) | Go 190 Python 190 | stale: 'every hop must earn its place' (ban); rule-engine row per language |
| Appendices A-I | `59-appI-latency-sb.png` (6f0c88a1) | DotNet 198 Quarkus 190 Spring 194 | stale: 'every hop must earn its place' (ban); rule-engine row per language |
| Appendices A-I | `60-appI-east-west.png` (6dc23201) | Cpp 192 | stale: 'for free' (ban) |
| Appendices A-I | `60-appI-east-west.png` (8badba43) | DotNet 200 Go 192 Python 192 Quarkus 192 Spring 196 | stale: 'for free' (ban) |
| Appendices A-I | `61-appI-cpp-router.png` (59c9c14e) | Cpp 187 | stale: modern-cpp-kafka |
| Appendices A-I | `61-appI-python-router.png` (fc30e611) | Go 187 Python 187 | wrong language in the Go deck; ok in Python |
| Appendix D/I extras and J | `62-appD-temporal-dn.png` (37003d3c) | DotNet 131 | ok |
| Appendix D/I extras and J | `62-appD-temporal.png` (a8fd60c4) | Spring 127 | ok |
| Appendix D/I extras and J | `63-appD-stateless-dn.png` (66042487) | DotNet 133 | stale: 'MassTransit Sagas'; '@Transactional' |
| Appendix D/I extras and J | `63-appD-statemachine.png` (c362e9a3) | Spring 129 | replaced (decision 6): Spring Statemachine figure |
| Appendix D/I extras and J | `70-appJ-pinned-libraries-dn.png` (854b9f97) | DotNet 207 | stale: MassTransit row; 'Every entry above' |
| Appendix D/I extras and J | `71-appJ-pinned-platform-dn.png` (89cd4fd4) | DotNet 208 | stale: Redis license (Redis 8 is RSALv2/SSPLv1/AGPLv3) |
| Appendix D/I extras and J | `72-appJ-migration-reference-dn.png` (5d457c4d) | DotNet 209 | stale: MassTransit in three rows |
| Appendices K-L | `80-appK-monolith-deployment.png` (aef5a8ec) | Cpp 199 | ok |
| Appendices K-L | `80-appK-monolith-deployment.png` (cdee389b) | DotNet 213 Go 199 Python 199 Quarkus 199 Spring 203 | ok |
| Appendices K-L | `81-appK-modular-monolith.png` (7078c290) | DotNet 214 Go 200 Python 200 Quarkus 200 Spring 204 | ok |
| Appendices K-L | `81-appK-modular-monolith.png` (e970b151) | Cpp 200 | ok |
| Appendices K-L | `82-appK-modular-monolith-decomposed-db.png` (5244881e) | DotNet 215 Go 201 Python 201 Quarkus 201 Spring 205 | ok |
| Appendices K-L | `82-appK-modular-monolith-decomposed-db.png` (a1559049) | Cpp 201 | ok |
| Appendices K-L | `83-appK-strangler-identify-move-redirect.png` (80285771) | DotNet 216 Go 202 Python 202 Quarkus 202 Spring 206 | ok |
| Appendices K-L | `83-appK-strangler-identify-move-redirect.png` (f19a6072) | Cpp 202 | ok |
| Appendices K-L | `84-appK-strangler-proxy.png` (e5e2e76e) | Cpp 203 | ok |
| Appendices K-L | `84-appK-strangler-proxy.png` (f6e2aed6) | DotNet 217 Go 203 Python 203 Quarkus 203 Spring 207 | ok |
| Appendices K-L | `85-appK-strangler-proxy-redirection.png` (9081c110) | DotNet 218 Go 204 Python 204 Quarkus 204 Spring 208 | ok |
| Appendices K-L | `85-appK-strangler-proxy-redirection.png` (ab19e842) | Cpp 204 | ok |
| Appendices K-L | `86-appK-strangler-shared-database.png` (81c3d748) | Cpp 205 | stale: '(decomposed DB above)' (positional) |
| Appendices K-L | `86-appK-strangler-shared-database.png` (cd33b74a) | DotNet 219 Go 205 Python 205 Quarkus 205 Spring 209 | stale: '(decomposed DB above)' (positional) |
| Appendices K-L | `88-appK-decorating-collaborator.png` (7dc24571) | DotNet 221 Go 207 Python 207 Quarkus 207 Spring 211 | ok |
| Appendices K-L | `88-appK-decorating-collaborator.png` (c426476e) | Cpp 207 | ok |
| Appendices K-L | `90-appL-cache-aside.png` (28a938d5) | DotNet 226 Go 212 Python 212 Quarkus 212 Spring 216 | ok |
| Appendices K-L | `90-appL-cache-aside.png` (d28b7d7e) | Cpp 212 | ok |
| Appendices K-L | `91-appL-read-through.png` (1d537085) | DotNet 228 Go 214 Python 214 Quarkus 214 Spring 218 | ok |
| Appendices K-L | `91-appL-read-through.png` (b24babb5) | Cpp 214 | ok |
| Appendices K-L | `92-appL-write-through.png` (a9a9912c) | DotNet 230 Go 216 Python 216 Quarkus 216 Spring 220 | ok |
| Appendices K-L | `92-appL-write-through.png` (cc1a6713) | Cpp 216 | ok |
| Appendices K-L | `93-appL-write-around.png` (4794da2c) | DotNet 232 Go 218 Python 218 Quarkus 218 Spring 222 | ok |
| Appendices K-L | `93-appL-write-around.png` (7b8aa529) | Cpp 218 | ok |
| Appendices K-L | `94-appL-write-back.png` (08ff93f3) | Cpp 220 | ok |
| Appendices K-L | `94-appL-write-back.png` (7e2c5bfb) | DotNet 234 Go 220 Python 220 Quarkus 220 Spring 224 | ok |
| Appendices K-L | `95-appL-refresh-ahead.png` (e617fe98) | DotNet 236 Go 222 Python 222 Quarkus 222 Spring 226 | ok |
| Appendices K-L | `95-appL-refresh-ahead.png` (f088ddaa) | Cpp 222 | ok |
| Appendix M | `110-failure-taxonomy.png` (168bd1d1) | DotNet 242 Go 228 Python 228 Quarkus 228 Spring 232 | stale: 'the rest of this appendix' (ban) |
| Appendix M | `110-failure-taxonomy.png` (d03d5c63) | Cpp 228 | stale: 'the rest of this appendix' (ban) |
| Appendix M | `111-failure-network-partition.png` (c75254c9) | Cpp 229 | ok |
| Appendix M | `111-failure-network-partition.png` (f394f054) | DotNet 243 Go 229 Python 229 Quarkus 229 Spring 233 | ok |
| Appendix M | `112-failure-split-brain.png` (37f4880b) | Cpp 230 | ok |
| Appendix M | `112-failure-split-brain.png` (bb67f91e) | DotNet 244 Go 230 Python 230 Quarkus 230 Spring 234 | ok |
| Appendix M | `113-failure-partial.png` (89ba62a8) | DotNet 245 Go 231 Python 231 Quarkus 231 Spring 235 | ok |
| Appendix M | `113-failure-partial.png` (ccb596f1) | Cpp 231 | ok |
| Appendix M | `114-failure-gray.png` (385fd669) | Cpp 232 | ok |
| Appendix M | `114-failure-gray.png` (5de01d21) | DotNet 246 Go 232 Python 232 Quarkus 232 Spring 236 | ok |
| Appendix M | `115-failure-amplification.png` (2627a710) | DotNet 247 Go 233 Python 233 Quarkus 233 Spring 237 | ok |
| Appendix M | `115-failure-amplification.png` (54165994) | Cpp 233 | ok |
| Appendix M | `116-failure-cascading.png` (6327e354) | DotNet 248 Go 234 Python 234 Quarkus 234 Spring 238 | ok |
| Appendix M | `116-failure-cascading.png` (98afa202) | Cpp 234 | ok |
| Appendix M | `117-failure-circuit-breaker-cpp.png` (9bae1e7e) | Cpp 240 | ok |
| Appendix M | `117-failure-circuit-breaker.png` (c0d197f9) | DotNet 254 Go 240 Python 240 Quarkus 240 Spring 244 | Go deck: library list without sony/gobreaker; ok elsewhere |
| Appendix M | `118-failure-retry-backoff.png` (4d374ef8) | DotNet 252 Go 238 Python 238 Quarkus 238 Spring 242 | ok |
| Appendix M | `118-failure-retry-backoff.png` (6ae7a4fe) | Cpp 238 | ok |
| Appendix M | `119-failure-timeout-deadline.png` (eba21c5d) | DotNet 250 Go 236 Python 236 Quarkus 236 Spring 240 | ok |
| Appendix M | `119-failure-timeout-deadline.png` (fd475841) | Cpp 236 | ok |
| Appendix M | `120-failure-istio-resilience.png` (167305b9) | DotNet 258 Go 244 Python 244 Quarkus 244 Spring 248 | ok |
| Appendix M | `120-failure-istio-resilience.png` (1d341987) | Cpp 244 | ok |
| Appendix M | `121-failure-matrix.png` (2e8c357a) | DotNet 261 Go 247 Python 247 Quarkus 247 Spring 251 | ok |
| Appendix M | `121-failure-matrix.png` (36296bd8) | Cpp 247 | ok |
| Appendices N and O | `apxn-control-plane.png` (c89ef80f) | Cpp 257 DotNet 271 Go 257 Python 257 Quarkus 257 Spring 261 | ok |
| Appendices N and O | `apxn-deploy-release.png` (2aea96a8) | Cpp 250 DotNet 264 Go 250 Python 250 Quarkus 250 Spring 254 | ok |
| Appendices N and O | `apxn-eval-arch.png` (534117b1) | Cpp 252 DotNet 266 Go 252 Python 252 Quarkus 252 Spring 256 | ok |
| Appendices N and O | `apxn-flag-types.png` (fb1016ab) | Cpp 251 DotNet 265 Go 251 Python 251 Quarkus 251 Spring 255 | ok |
| Appendices N and O | `apxn-lifecycle.png` (4a00d8b2) | Cpp 258 DotNet 272 Go 258 Python 258 Quarkus 258 Spring 262 | ok |
| Appendices N and O | `apxn-rollout.png` (2e7ea1b9) | Cpp 255 DotNet 269 Go 255 Python 255 Quarkus 255 Spring 259 | ok |
| Appendices N and O | `apxo-collection-anatomy.png` (0641912f) | Cpp 263 DotNet 277 Go 263 Python 263 Quarkus 263 Spring 267 | ok |
| Appendices N and O | `apxo-data-driven.png` (8a98e8a5) | Cpp 268 DotNet 282 Go 268 Python 268 Quarkus 268 Spring 272 | ok |
| Appendices N and O | `apxo-newman-run.png` (0a5b3d1a) | Cpp 262 DotNet 276 Go 262 Python 262 Quarkus 262 Spring 266 | ok |
| Appendices N and O | `apxo-test-pyramid.png` (fefc34cd) | Cpp 271 DotNet 285 Go 271 Python 271 Quarkus 271 Spring 275 | ok |
| .NET Appendices P and Q (logo, panel) | `image.png` (8b8865f5) | DotNet 287 DotNet 297 | logo / section panel (not content) |
| .NET Appendices P and Q (logo, panel) | `image.png` (aedbd5df) | DotNet 288 DotNet 289 DotNet 290 DotNet 291 DotNet 292 DotNet 293 DotNet 294 DotNet 295 DotNet 296 DotNet 298 DotNet 299 DotNet 300 DotNet 301 DotNet 302 DotNet 303 | logo / section panel (not content) |
| .NET Appendices P and Q (logo, panel) | `image.png` (fef521f3) | DotNet 287 DotNet 297 | logo / section panel (not content) |

## Decision 7 (vendor names in figures, 2026-10-12)

All 257 distinct content images of the six language decks (post-edit copies) were read again for vendor names
(a Sonnet pass over about 100, the planner over the remaining 152 in contact sheets). Hits and fixes:

| Image (hash) | Used on | Text | Fix |
|---|---|---|---|
| valet-key concept (d2d27ea3eb, 82d4ae02a5) | Python, Quarkus, Spring, Go 77; .NET 79; C++ 77 | "Resource (S3, blob, file)", "Examples: S3 pre-signed URLs, Azure SAS tokens, GCS signed URLs, AWS STS AssumeRole" | `12-valet-key.png` (site figure, labels made neutral; site fix listed) |
| zero-trust (50677a2964, 2f9071c625) | Python, Quarkus, Spring, Go 80; .NET 82; C++ 80 | "Examples: Google IAP, Cloudflare Access, Pomerium, AWS Verified Access, …" | `12-zero-trust.png` (site figure, already neutral) |
| Appendix I layered stack (53094a2bb1, f948b26550, f2533f5626) | Python 172, Quarkus 172, Spring 176 | API Gateway row "Kong · Apigee · Istio gateway · Spring Cloud GW" | `22-l7-layers.png` (site figure, as Go, C++ and .NET already use) |
| .NET pinned toolkit table (authored) | .NET 207 | "not Azure SignalR Service", "no Azure-only dependencies" | `70-appJ-pinned-libraries-dn.png` re-rendered ("no managed SignalR service", "no cloud-only dependencies") |
| .NET migration reference (authored) | .NET 209 | "no Azure required" | `72-appJ-migration-reference-dn.png` re-rendered ("no managed cloud service required") |
| Blazor architectures (a51a3664a6) | .NET 122 | "… no Azure SignalR Service, no Azure App Service." | kept: Azure only in a negation, no source to redraw (listed as open in the report) |

No image names OpenShift, ACS, AWS SDKs or boto3 outside the removed Appendix S figures.
