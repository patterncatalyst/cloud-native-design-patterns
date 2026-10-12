# Watch-tier ledger (decks after the S12 edits)

Every watch-tier line the scanner still reports in the post-edit text copies (all edit files applied to fresh copies of the committed decks, including the decision-7 amendment of 2026-10-12), with its reason code from the README policy. Ban tier is 0 in all eight decks. Counts are scanner lines (one per pattern per line).

| Deck | Kept watch lines | By reason |
|---|---|---|
| Designing-Cloud-Native-APIs-Python | 54 | literal-subject 26, machine-subject 7, notes-paragraph 15, planned-stage 2, quoted 2, survey-term 1, table-data 1 |
| Designing-Cloud-Native-APIs-Quarkus | 51 | literal-subject 26, machine-subject 7, notes-paragraph 12, planned-stage 2, quoted 2, survey-term 1, table-data 1 |
| Designing-Cloud-Native-APIs-Spring | 54 | literal-subject 26, machine-subject 7, notes-paragraph 15, planned-stage 2, quoted 2, survey-term 1, table-data 1 |
| Designing-Cloud-Native-APIs-DotNet | 63 | literal-subject 25, machine-subject 7, notes-paragraph 25, planned-stage 2, quoted 2, survey-term 1, table-data 1 |
| Designing-Cloud-Native-APIs-Go | 55 | literal-subject 26, machine-subject 7, notes-paragraph 16, planned-stage 2, quoted 2, survey-term 1, table-data 1 |
| Designing-Cloud-Native-APIs-Cpp | 45 | literal-subject 24, machine-subject 6, notes-paragraph 11, planned-stage 1, quoted 1, survey-term 1, table-data 1 |
| K8s-Environment-Access-Policies | 8 | notes-paragraph 8 |
| Network-Policy-Process-Advisory | 0 |  |

By pattern and reason (all decks):

| Pattern | Reason | Lines |
|---|---|---|
| deliberate (adjective) | planned-stage | 11 |
| em-dash pileup (3+ per line) | notes-paragraph | 102 |
| environment-specific noun | literal-subject | 153 |
| exclamation in prose | quoted | 11 |
| lie / lies / lying (person vs machine) | machine-subject | 13 |
| parallel-number title | table-data | 6 |
| quietly / silently | machine-subject | 28 |
| soft hype | survey-term | 6 |

Notes:

- `literal-subject`: the Appendix R slides and eyebrows (`APPENDIX R · MINIKUBE`), agenda and notes where minikube is the subject (no Appendix S slides after decision 7).
- `notes-paragraph`: notes paragraphs with three or more em dashes, each sentence holding at most one.
- `table-data`: recorded results and unit lists ("10 passed, 0 failed").
- `quoted`: the book title *Release It!*.
- The Network-Policy-Process-Advisory rework (decision 7) left no watch-tier line.

## Designing-Cloud-Native-APIs-Python

| Slide | Pattern | Reason | Text |
|---|---|---|---|
| ## [227] APPENDIX M · Distributed systems fail differently ( | lie / lies / lying (person vs machine) | machine-subject | - Some failures lie: a node passes its own health check while failing real traffic (gray failure). What the system believes about itself and |
| ## [248] APPENDIX M · Take-aways and references (sldId 503) | lie / lies / lying (person vs machine) | machine-subject | - Design for partial failure from the start: every remote call can succeed, fail, hang, or lie. Timeout everything; the default is often inf |
| ## [088] SECURITY · Choosing the right pattern (sldId 343) | deliberate (adjective) | planned-stage | > Close the section with the decision rules. The cost lines are there because every pattern is a trade. Sidecar costs a container per Pod (a |
| ## [205] APPENDIX K · STRANGLER FIG · With a shared database | deliberate (adjective) | planned-stage | ## [205] APPENDIX K · STRANGLER FIG · With a shared database — a deliberate intermediate state (sldId 460) |
| ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka | soft hype | survey-term | ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka, Pulsar, Flink, NiFi (sldId 294) |
| ## [108] APPENDIX B · VERSIONING · Evolving a .proto safely  | quietly / silently | machine-subject | > Walk the safe pattern. We removed an old 'notes' field, so we reserve both its tag number (4) and its name permanently: nobody can reuse t |
| ## [111] APPENDIX B · VERSIONING · Principles that cut acros | quietly / silently | machine-subject | - Never break silently: deprecate with a reason, a replacement and a sunset date; measure who's still on the old version. |
| ## [111] APPENDIX B · VERSIONING · Principles that cut acros | quietly / silently | machine-subject | > Step back to the universal principles, because the protocol-specific rules all rhyme. Additive change is safe; removal and mutation break  |
| ## [157] APPENDIX G · COUPLING · Coupling and our APIs (sldI | quietly / silently | machine-subject | - The registry is what keeps that contract coupling stable: compatibility rules stop a producer from silently raising the integration streng |
| ## [157] APPENDIX G · COUPLING · Coupling and our APIs (sldI | quietly / silently | machine-subject | > Bring it home to the talk's content. The reframe to offer: every protocol decision was secretly a coupling decision, and we kept choosing  |
| ## [028] DATA · CQRS — Command Query Responsibility Segregat | em-dash pileup (3+ per line) | notes-paragraph | > CQRS (Command Query Responsibility Segregation) is the pattern of using different models for writes and reads. The write side optimises fo |
| ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka | em-dash pileup (3+ per line) | notes-paragraph | > Each of the four tools does a different job. KAFKA is the SUBSTRATE — a partitioned, ordered, durable log. Consumers track their own offse |
| ## [061] OBSERVABILITY · The signals in depth — traces, metr | em-dash pileup (3+ per line) | notes-paragraph | > Expand the 'three pillars' framing into the five signals modern observability uses. Traces answer WHERE the time went and which hop failed |
| ## [063] OBSERVABILITY · Auto-injection vs. instrumentation  | em-dash pileup (3+ per line) | notes-paragraph | > This is the slide the user specifically asked for: distinguish auto-INJECTION from auto-INSTRUMENTATION from MANUAL instrumentation — thre |
| ## [065] OBSERVABILITY · How correlation works — context pro | em-dash pileup (3+ per line) | notes-paragraph | > Demystify the magic word 'correlation.' It is not a backend join — it's the trace context physically travelling WITH the request, in-band, |
| ## [069] OBSERVABILITY · Choosing a sampling strategy (sldId | em-dash pileup (3+ per line) | notes-paragraph | > The decision guide for sampling. Probabilistic is the simplest and the most common starting point — keep 10%, predictable volume. Rate-lim |
| ## [092] ANTI-PATTERNS · The heuristics that keep you out of | em-dash pileup (3+ per line) | notes-paragraph | > These are the five tests to apply in design and code review. (1) If two services must deploy together, they are one service: merge them or |
| ## [121] APPENDIX D · SAGAS · Where a Python saga keeps its  | em-dash pileup (3+ per line) | notes-paragraph | > First problem: the orchestrator must survive a crash mid-flow, so in-memory state is a non-starter — a pod restart would strand every in-f |
| ## [125] APPENDIX D · SAGAS · When step B needs data only st | em-dash pileup (3+ per line) | notes-paragraph | > This is the specific case you asked about, and a common source of bad designs. The orchestrator calls service A, then service B — but B ne |
| ## [150] APPENDIX G · COUPLING · Coupling is necessary — bal | em-dash pileup (3+ per line) | notes-paragraph | > Frame the appendix. The central, slightly contrarian idea: coupling is not a defect to be driven to zero — it's necessary, and the real sk |
| ## [153] APPENDIX G · COUPLING · Integration strength: a lad | em-dash pileup (3+ per line) | notes-paragraph | > Integration strength has four levels, worst to best. Intrusive coupling: one component reaches into another's private internals — the clas |
| ## [155] APPENDIX G · COUPLING · Balancing coupling: strengt | em-dash pileup (3+ per line) | notes-paragraph | > This brings strength and distance together into the design rule. Read the quadrants: high strength and close together is a cohesive module |
| ## [203] APPENDIX K · STRANGLER FIG · With a proxy — step ze | em-dash pileup (3+ per line) | notes-paragraph | > The pre-condition for incremental migration: clients hit the proxy, the proxy forwards to the monolith. Day zero, behaviour is unchanged.  |
| ## [219] APPENDIX L · WRITE-AROUND · Write-around in Python  | em-dash pileup (3+ per line) | notes-paragraph | > Two write variants and the standard cache-aside read for context. The pure write-around just inserts to the DB — the cache isn't touched a |
| ## [221] APPENDIX L · WRITE-BACK · Write-back with a backgro | em-dash pileup (3+ per line) | notes-paragraph | > Write-back has more moving parts than the other patterns; the slide shows the canonical shape. (1) Writes go to cache and add the key to a |
| ## [248] APPENDIX M · Take-aways and references (sldId 503) | exclamation in prose | quoted |   - References: Google SRE Book (chapters on Addressing Cascading Failures, Handling Overload); 'Release It!' (Nygard — circuit breaker, bul |
| ## [248] APPENDIX M · Take-aways and references (sldId 503) | exclamation in prose | quoted | > Close the appendix and, since it's the last appendix, effectively close the deck's technical content. The take-aways are the imperatives:  |
| ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536 | parallel-number title | table-data | - 10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0). |
| ## [001] CLOUD-NATIVE ARCHITECTURE · Designing Cloud-Native  | environment-specific noun | literal-subject | > Welcome and framing. This is a working architect's tour of designing cloud-native APIs — not a survey of buzzwords. Set expectations: we b |
| ## [002] AGENDA · Agenda (sldId 257) | environment-specific noun | literal-subject | - Appendix R · Example 05 on minikube |
| ## [002] AGENDA · Agenda (sldId 257) | environment-specific noun | literal-subject | > The appendices are reference material for the questions that come up: protocols, versioning, WebSockets, sagas, errors, DDD, coupling, shu |
| ## [003] OVERVIEW · What we'll build, and the order we'll bu | environment-specific noun | literal-subject | > Walk the arc quickly; don't dwell. The order follows dependency: principles first because they justify every later choice, then the synchr |
| ## [273] Example 05 on minikube (sldId 528) | environment-specific noun | literal-subject | ## [273] Example 05 on minikube (sldId 528) |
| ## [273] Example 05 on minikube (sldId 528) | environment-specific noun | literal-subject | > Appendix R takes Example 05, the event-driven fan-out, from docker compose to a single-node Kubernetes cluster on minikube, in all six lan |
| ## [274] APPENDIX R · MINIKUBE · From compose to a cluster ( | environment-specific noun | literal-subject | ## [274] APPENDIX R · MINIKUBE · From compose to a cluster (sldId 529) |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId 530) |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | - No kubectl port-forward, minikube tunnel or minikube service: forwarded connections drop. |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | minikube v1.39.0 · kubectl v1.36.5 · Helm v4.3.0 · Strimzi 1.2.0 |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > minikube runs the control plane and the workload in one container on Docker Engine, the same engine compose uses, with containerd as the c |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > Host access uses two NodePorts published on the loopback address when the profile is created. Port-forwarding, minikube tunnel and minikub |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > The kubectl context never changes: every command names --context cndp-k8s, minikube start runs with --keep-context, and setup-profile.sh r |
| ## [276] APPENDIX R · MINIKUBE · One node, two namespaces (s | environment-specific noun | literal-subject | ## [276] APPENDIX R · MINIKUBE · One node, two namespaces (sldId 531) |
| ## [276] APPENDIX R · MINIKUBE · One node, two namespaces (s | environment-specific noun | literal-subject | > From the host, curl and verify.sh reach order-service on 127.0.0.1:30080, a browser reaches Grafana on 127.0.0.1:30300, and kubectl exec r |
| ## [277] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldI | environment-specific noun | literal-subject | ## [277] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldId 532) |
| ## [277] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldI | environment-specific noun | literal-subject | - build: → docker build, then minikube image load; imagePullPolicy: Never. |
| ## [278] APPENDIX R · MINIKUBE · One overlay per language (s | environment-specific noun | literal-subject | ## [278] APPENDIX R · MINIKUBE · One overlay per language (sldId 533) |
| ## [279] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | ## [279] APPENDIX R · MINIKUBE · Images built on the host (sldId 534) |
| ## [279] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | docker build on the host, minikube image load into the node; pods never pull |
| ## [279] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | > The cluster does not build images. Each service is built on the host with docker build, which keeps the host's BuildKit caches (a cold C++ |
| ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) | environment-specific noun | literal-subject | ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) |
| ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) | environment-specific noun | literal-subject | [chip] bash · minikube |
| ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) | environment-specific noun | literal-subject | > What to show: the ten check marks and the Results line, then Grafana on 127.0.0.1:30300. Fallback: the recorded results that follow. teard |
| ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536 | environment-specific noun | literal-subject | ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536) |
| ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536 | environment-specific noun | literal-subject | - 10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0). |

## Designing-Cloud-Native-APIs-Quarkus

| Slide | Pattern | Reason | Text |
|---|---|---|---|
| ## [227] APPENDIX M · Distributed systems fail differently ( | lie / lies / lying (person vs machine) | machine-subject | - Some failures lie: a node passes its own health check while failing real traffic (gray failure). What the system believes about itself and |
| ## [248] APPENDIX M · Take-aways and references (sldId 503) | lie / lies / lying (person vs machine) | machine-subject | - Design for partial failure from the start: every remote call can succeed, fail, hang, or lie. Timeout everything; the default is often inf |
| ## [088] SECURITY · Choosing the right pattern (sldId 343) | deliberate (adjective) | planned-stage | > Close the section with the decision rules. The cost lines are there because every pattern is a trade. Sidecar costs a container per Pod (a |
| ## [205] APPENDIX K · STRANGLER FIG · With a shared database | deliberate (adjective) | planned-stage | ## [205] APPENDIX K · STRANGLER FIG · With a shared database — a deliberate intermediate state (sldId 460) |
| ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka | soft hype | survey-term | ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka, Pulsar, Flink, NiFi (sldId 294) |
| ## [108] APPENDIX B · VERSIONING · Evolving a .proto safely  | quietly / silently | machine-subject | > Walk the safe pattern. We removed an old 'notes' field, so we reserve both its tag number (4) and its name permanently: nobody can reuse t |
| ## [111] APPENDIX B · VERSIONING · Principles that cut acros | quietly / silently | machine-subject | - Never break silently: deprecate with a reason, a replacement and a sunset date; measure who's still on the old version. |
| ## [111] APPENDIX B · VERSIONING · Principles that cut acros | quietly / silently | machine-subject | > Step back to the universal principles, because the protocol-specific rules all rhyme. Additive change is safe; removal and mutation break  |
| ## [157] APPENDIX G · COUPLING · Coupling and our APIs (sldI | quietly / silently | machine-subject | - The registry is what keeps that contract coupling stable: compatibility rules stop a producer from silently raising the integration streng |
| ## [157] APPENDIX G · COUPLING · Coupling and our APIs (sldI | quietly / silently | machine-subject | > Bring it home to the talk's content. The reframe to offer: every protocol decision was secretly a coupling decision, and we kept choosing  |
| ## [028] DATA · CQRS — Command Query Responsibility Segregat | em-dash pileup (3+ per line) | notes-paragraph | > CQRS (Command Query Responsibility Segregation) is the pattern of using different models for writes and reads. The write side optimises fo |
| ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka | em-dash pileup (3+ per line) | notes-paragraph | > Each of the four tools does a different job. KAFKA is the SUBSTRATE — a partitioned, ordered, durable log. Consumers track their own offse |
| ## [061] OBSERVABILITY · The signals in depth — traces, metr | em-dash pileup (3+ per line) | notes-paragraph | > Expand the 'three pillars' framing into the five signals modern observability uses. Traces answer WHERE the time went and which hop failed |
| ## [063] OBSERVABILITY · Auto-injection vs. instrumentation  | em-dash pileup (3+ per line) | notes-paragraph | > This is the slide the user specifically asked for: distinguish auto-INJECTION from auto-INSTRUMENTATION from MANUAL instrumentation — thre |
| ## [065] OBSERVABILITY · How correlation works — context pro | em-dash pileup (3+ per line) | notes-paragraph | > Demystify the magic word 'correlation.' It is not a backend join — it's the trace context physically travelling WITH the request, in-band, |
| ## [069] OBSERVABILITY · Choosing a sampling strategy (sldId | em-dash pileup (3+ per line) | notes-paragraph | > The decision guide for sampling. Probabilistic is the simplest and the most common starting point — keep 10%, predictable volume. Rate-lim |
| ## [092] ANTI-PATTERNS · The heuristics that keep you out of | em-dash pileup (3+ per line) | notes-paragraph | > These are the five tests to apply in design and code review. (1) If two services must deploy together, they are one service: merge them or |
| ## [121] APPENDIX D · SAGAS · Where a Quarkus saga keeps its | em-dash pileup (3+ per line) | notes-paragraph | > First problem: the orchestrator must survive a crash mid-flow, so in-memory state is a non-starter — a pod restart would strand every in-f |
| ## [125] APPENDIX D · SAGAS · When step B needs data only st | em-dash pileup (3+ per line) | notes-paragraph | > This is the specific case you asked about, and a common source of bad designs. The orchestrator calls service A, then service B — but B ne |
| ## [150] APPENDIX G · COUPLING · Coupling is necessary — bal | em-dash pileup (3+ per line) | notes-paragraph | > Frame the appendix. The central, slightly contrarian idea: coupling is not a defect to be driven to zero — it's necessary, and the real sk |
| ## [153] APPENDIX G · COUPLING · Integration strength: a lad | em-dash pileup (3+ per line) | notes-paragraph | > Integration strength has four levels, worst to best. Intrusive coupling: one component reaches into another's private internals — the clas |
| ## [155] APPENDIX G · COUPLING · Balancing coupling: strengt | em-dash pileup (3+ per line) | notes-paragraph | > This brings strength and distance together into the design rule. Read the quadrants: high strength and close together is a cohesive module |
| ## [248] APPENDIX M · Take-aways and references (sldId 503) | exclamation in prose | quoted |   - References: Google SRE Book (chapters on Addressing Cascading Failures, Handling Overload); 'Release It!' (Nygard — circuit breaker, bul |
| ## [248] APPENDIX M · Take-aways and references (sldId 503) | exclamation in prose | quoted | > Close the appendix and, since it's the last appendix, effectively close the deck's technical content. The take-aways are the imperatives:  |
| ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536 | parallel-number title | table-data | - 10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0). |
| ## [001] CLOUD-NATIVE ARCHITECTURE · Designing Cloud-Native  | environment-specific noun | literal-subject | > Welcome and framing. This is a working architect's tour of designing cloud-native APIs on Quarkus 3.40.1 (LTS, Java 25) — not a survey of  |
| ## [002] AGENDA · Agenda (sldId 257) | environment-specific noun | literal-subject | - Appendix R · Example 05 on minikube |
| ## [002] AGENDA · Agenda (sldId 257) | environment-specific noun | literal-subject | > The appendices are reference material for the questions that come up: protocols, versioning, WebSockets, sagas, errors, DDD, coupling, shu |
| ## [003] OVERVIEW · What we'll build, and the order we'll bu | environment-specific noun | literal-subject | > Walk the arc quickly; don't dwell. The order follows dependency: principles first because they justify every later choice, then the synchr |
| ## [273] Example 05 on minikube (sldId 528) | environment-specific noun | literal-subject | ## [273] Example 05 on minikube (sldId 528) |
| ## [273] Example 05 on minikube (sldId 528) | environment-specific noun | literal-subject | > Appendix R takes Example 05, the event-driven fan-out, from docker compose to a single-node Kubernetes cluster on minikube, in all six lan |
| ## [274] APPENDIX R · MINIKUBE · From compose to a cluster ( | environment-specific noun | literal-subject | ## [274] APPENDIX R · MINIKUBE · From compose to a cluster (sldId 529) |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId 530) |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | - No kubectl port-forward, minikube tunnel or minikube service: forwarded connections drop. |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | minikube v1.39.0 · kubectl v1.36.5 · Helm v4.3.0 · Strimzi 1.2.0 |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > minikube runs the control plane and the workload in one container on Docker Engine, the same engine compose uses, with containerd as the c |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > Host access uses two NodePorts published on the loopback address when the profile is created. Port-forwarding, minikube tunnel and minikub |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > The kubectl context never changes: every command names --context cndp-k8s, minikube start runs with --keep-context, and setup-profile.sh r |
| ## [276] APPENDIX R · MINIKUBE · One node, two namespaces (s | environment-specific noun | literal-subject | ## [276] APPENDIX R · MINIKUBE · One node, two namespaces (sldId 531) |
| ## [276] APPENDIX R · MINIKUBE · One node, two namespaces (s | environment-specific noun | literal-subject | > From the host, curl and verify.sh reach order-service on 127.0.0.1:30080, a browser reaches Grafana on 127.0.0.1:30300, and kubectl exec r |
| ## [277] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldI | environment-specific noun | literal-subject | ## [277] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldId 532) |
| ## [277] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldI | environment-specific noun | literal-subject | - build: → docker build, then minikube image load; imagePullPolicy: Never. |
| ## [278] APPENDIX R · MINIKUBE · One overlay per language (s | environment-specific noun | literal-subject | ## [278] APPENDIX R · MINIKUBE · One overlay per language (sldId 533) |
| ## [279] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | ## [279] APPENDIX R · MINIKUBE · Images built on the host (sldId 534) |
| ## [279] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | docker build on the host, minikube image load into the node; pods never pull |
| ## [279] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | > The cluster does not build images. Each service is built on the host with docker build, which keeps the host's BuildKit caches (a cold C++ |
| ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) | environment-specific noun | literal-subject | ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) |
| ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) | environment-specific noun | literal-subject | [chip] bash · minikube |
| ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) | environment-specific noun | literal-subject | > What to show: the ten check marks and the Results line, then Grafana on 127.0.0.1:30300. Fallback: the recorded results that follow. teard |
| ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536 | environment-specific noun | literal-subject | ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536) |
| ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536 | environment-specific noun | literal-subject | - 10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0). |

## Designing-Cloud-Native-APIs-Spring

| Slide | Pattern | Reason | Text |
|---|---|---|---|
| ## [231] APPENDIX M · Distributed systems fail differently ( | lie / lies / lying (person vs machine) | machine-subject | - Some failures lie: a node passes its own health check while failing real traffic (gray failure). What the system believes about itself and |
| ## [252] APPENDIX M · Take-aways and references (sldId 507) | lie / lies / lying (person vs machine) | machine-subject | - Design for partial failure from the start: every remote call can succeed, fail, hang, or lie. Timeout everything; the default is often inf |
| ## [088] SECURITY · Choosing the right pattern (sldId 343) | deliberate (adjective) | planned-stage | > Close the section with the decision rules. The cost lines are there because every pattern is a trade. Sidecar costs a container per Pod (a |
| ## [209] APPENDIX K · STRANGLER FIG · With a shared database | deliberate (adjective) | planned-stage | ## [209] APPENDIX K · STRANGLER FIG · With a shared database — a deliberate intermediate state (sldId 464) |
| ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka | soft hype | survey-term | ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka, Pulsar, Flink, NiFi (sldId 294) |
| ## [108] APPENDIX B · VERSIONING · Evolving a .proto safely  | quietly / silently | machine-subject | > Walk the safe pattern. We removed an old 'notes' field, so we reserve both its tag number (4) and its name permanently: nobody can reuse t |
| ## [111] APPENDIX B · VERSIONING · Principles that cut acros | quietly / silently | machine-subject | - Never break silently: deprecate with a reason, a replacement and a sunset date; measure who's still on the old version. |
| ## [111] APPENDIX B · VERSIONING · Principles that cut acros | quietly / silently | machine-subject | > Step back to the universal principles, because the protocol-specific rules all rhyme. Additive change is safe; removal and mutation break  |
| ## [161] APPENDIX G · COUPLING · Coupling and our APIs (sldI | quietly / silently | machine-subject | - The registry is what keeps that contract coupling stable: compatibility rules stop a producer from silently raising the integration streng |
| ## [161] APPENDIX G · COUPLING · Coupling and our APIs (sldI | quietly / silently | machine-subject | > Bring it home to the talk's content. The reframe to offer: every protocol decision was secretly a coupling decision, and we kept choosing  |
| ## [028] DATA · CQRS — Command Query Responsibility Segregat | em-dash pileup (3+ per line) | notes-paragraph | > CQRS (Command Query Responsibility Segregation) is the pattern of using different models for writes and reads. The write side optimises fo |
| ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka | em-dash pileup (3+ per line) | notes-paragraph | > Each of the four tools does a different job. KAFKA is the SUBSTRATE — a partitioned, ordered, durable log. Consumers track their own offse |
| ## [061] OBSERVABILITY · The signals in depth — traces, metr | em-dash pileup (3+ per line) | notes-paragraph | > Expand the 'three pillars' framing into the five signals modern observability uses. Traces answer WHERE the time went and which hop failed |
| ## [063] OBSERVABILITY · Auto-injection vs. instrumentation  | em-dash pileup (3+ per line) | notes-paragraph | > This is the slide the user specifically asked for: distinguish auto-INJECTION from auto-INSTRUMENTATION from MANUAL instrumentation — thre |
| ## [065] OBSERVABILITY · How correlation works — context pro | em-dash pileup (3+ per line) | notes-paragraph | > Demystify the magic word 'correlation.' It is not a backend join — it's the trace context physically travelling WITH the request, in-band, |
| ## [069] OBSERVABILITY · Choosing a sampling strategy (sldId | em-dash pileup (3+ per line) | notes-paragraph | > The decision guide for sampling. Probabilistic is the simplest and the most common starting point — keep 10%, predictable volume. Rate-lim |
| ## [092] ANTI-PATTERNS · The heuristics that keep you out of | em-dash pileup (3+ per line) | notes-paragraph | > These are the five tests to apply in design and code review. (1) If two services must deploy together, they are one service: merge them or |
| ## [121] APPENDIX D · SAGAS · Where a saga keeps its state ( | em-dash pileup (3+ per line) | notes-paragraph | > First problem: the orchestrator must survive a crash mid-flow, so in-memory state is a non-starter — a pod restart would strand every in-f |
| ## [125] APPENDIX D · SAGAS · When step B needs data only st | em-dash pileup (3+ per line) | notes-paragraph | > This is the specific case you asked about, and a common source of bad designs. The orchestrator calls service A, then service B — but B ne |
| ## [136] APPENDIX E · ERRORS · gRPC errors with rich status  | em-dash pileup (3+ per line) | notes-paragraph | > This is grpc-java's standard rich-error model via StatusProto — the same API surface whether you're on Spring Boot or any other JVM stack. |
| ## [140] APPENDIX E · ERRORS · GraphQL field errors with Spr | em-dash pileup (3+ per line) | notes-paragraph | > Throwing from a single field's resolver is exactly right: Spring for GraphQL's exception-resolution chain catches it, sets that field to n |
| ## [154] APPENDIX G · COUPLING · Coupling is necessary — bal | em-dash pileup (3+ per line) | notes-paragraph | > Frame the appendix. The central, slightly contrarian idea: coupling is not a defect to be driven to zero — it's necessary, and the real sk |
| ## [157] APPENDIX G · COUPLING · Integration strength: a lad | em-dash pileup (3+ per line) | notes-paragraph | > Integration strength has four levels, worst to best. Intrusive coupling: one component reaches into another's private internals — the clas |
| ## [159] APPENDIX G · COUPLING · Balancing coupling: strengt | em-dash pileup (3+ per line) | notes-paragraph | > This brings strength and distance together into the design rule. Read the quadrants: high strength and close together is a cohesive module |
| ## [201] APPENDIX I · L7 ROUTING · L7 routing checklist (sld | em-dash pileup (3+ per line) | notes-paragraph | > Leave the checklist up at the end. The first point is the most common organisational failure — a cluster ends up running three ingress con |
| ## [252] APPENDIX M · Take-aways and references (sldId 507) | exclamation in prose | quoted |   - References: Google SRE Book (chapters on Addressing Cascading Failures, Handling Overload); 'Release It!' (Nygard — circuit breaker, bul |
| ## [252] APPENDIX M · Take-aways and references (sldId 507) | exclamation in prose | quoted | > Close the appendix and, since it's the last appendix, effectively close the deck's technical content. The take-aways are the imperatives:  |
| ## [285] APPENDIX R · MINIKUBE · Recorded results (sldId 540 | parallel-number title | table-data | - 10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0). |
| ## [001] CLOUD-NATIVE ARCHITECTURE · Designing Cloud-Native  | environment-specific noun | literal-subject | > Welcome and framing. This is a working architect's tour of designing cloud-native APIs on Spring Boot 4.1.1. We build one realistic system |
| ## [002] AGENDA · Agenda (sldId 257) | environment-specific noun | literal-subject | - Appendix R · Example 05 on minikube |
| ## [002] AGENDA · Agenda (sldId 257) | environment-specific noun | literal-subject | > The appendices are reference material for the questions that come up: protocols, versioning, WebSockets, sagas, errors, DDD, coupling, shu |
| ## [003] OVERVIEW · What we'll build, and the order we'll bu | environment-specific noun | literal-subject | > Walk the arc quickly; don't dwell. The order follows dependency: principles first because they justify every later choice, then the synchr |
| ## [277] Example 05 on minikube (sldId 532) | environment-specific noun | literal-subject | ## [277] Example 05 on minikube (sldId 532) |
| ## [277] Example 05 on minikube (sldId 532) | environment-specific noun | literal-subject | > Appendix R takes Example 05, the event-driven fan-out, from docker compose to a single-node Kubernetes cluster on minikube, in all six lan |
| ## [278] APPENDIX R · MINIKUBE · From compose to a cluster ( | environment-specific noun | literal-subject | ## [278] APPENDIX R · MINIKUBE · From compose to a cluster (sldId 533) |
| ## [279] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | ## [279] APPENDIX R · MINIKUBE · The minikube runtime (sldId 534) |
| ## [279] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | - No kubectl port-forward, minikube tunnel or minikube service: forwarded connections drop. |
| ## [279] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | minikube v1.39.0 · kubectl v1.36.5 · Helm v4.3.0 · Strimzi 1.2.0 |
| ## [279] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > minikube runs the control plane and the workload in one container on Docker Engine, the same engine compose uses, with containerd as the c |
| ## [279] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > Host access uses two NodePorts published on the loopback address when the profile is created. Port-forwarding, minikube tunnel and minikub |
| ## [279] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > The kubectl context never changes: every command names --context cndp-k8s, minikube start runs with --keep-context, and setup-profile.sh r |
| ## [280] APPENDIX R · MINIKUBE · One node, two namespaces (s | environment-specific noun | literal-subject | ## [280] APPENDIX R · MINIKUBE · One node, two namespaces (sldId 535) |
| ## [280] APPENDIX R · MINIKUBE · One node, two namespaces (s | environment-specific noun | literal-subject | > From the host, curl and verify.sh reach order-service on 127.0.0.1:30080, a browser reaches Grafana on 127.0.0.1:30300, and kubectl exec r |
| ## [281] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldI | environment-specific noun | literal-subject | ## [281] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldId 536) |
| ## [281] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldI | environment-specific noun | literal-subject | - build: → docker build, then minikube image load; imagePullPolicy: Never. |
| ## [282] APPENDIX R · MINIKUBE · One overlay per language (s | environment-specific noun | literal-subject | ## [282] APPENDIX R · MINIKUBE · One overlay per language (sldId 537) |
| ## [283] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | ## [283] APPENDIX R · MINIKUBE · Images built on the host (sldId 538) |
| ## [283] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | docker build on the host, minikube image load into the node; pods never pull |
| ## [283] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | > The cluster does not build images. Each service is built on the host with docker build, which keeps the host's BuildKit caches (a cold C++ |
| ## [284] APPENDIX R · MINIKUBE · Run it (sldId 539) | environment-specific noun | literal-subject | ## [284] APPENDIX R · MINIKUBE · Run it (sldId 539) |
| ## [284] APPENDIX R · MINIKUBE · Run it (sldId 539) | environment-specific noun | literal-subject | [chip] bash · minikube |
| ## [284] APPENDIX R · MINIKUBE · Run it (sldId 539) | environment-specific noun | literal-subject | > What to show: the ten check marks and the Results line, then Grafana on 127.0.0.1:30300. Fallback: the recorded results that follow. teard |
| ## [285] APPENDIX R · MINIKUBE · Recorded results (sldId 540 | environment-specific noun | literal-subject | ## [285] APPENDIX R · MINIKUBE · Recorded results (sldId 540) |
| ## [285] APPENDIX R · MINIKUBE · Recorded results (sldId 540 | environment-specific noun | literal-subject | - 10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0). |

## Designing-Cloud-Native-APIs-DotNet

| Slide | Pattern | Reason | Text |
|---|---|---|---|
| ## [241] APPENDIX M · Distributed systems fail differently ( | lie / lies / lying (person vs machine) | machine-subject | - Some failures lie: a node passes its own health check while failing real traffic (gray failure). What the system believes about itself and |
| ## [262] APPENDIX M · Take-aways and references (sldId 517) | lie / lies / lying (person vs machine) | machine-subject | - Design for partial failure from the start: every remote call can succeed, fail, hang, or lie. Timeout everything; the default is often inf |
| ## [090] SECURITY · Choosing the right pattern (sldId 345) | deliberate (adjective) | planned-stage | > Close the section with the decision rules. The cost lines are there because every pattern is a trade. Sidecar costs a container per Pod (a |
| ## [219] APPENDIX K · STRANGLER FIG · With a shared database | deliberate (adjective) | planned-stage | ## [219] APPENDIX K · STRANGLER FIG · With a shared database — a deliberate intermediate state (sldId 474) |
| ## [041] EVENT-DRIVEN · Event-driven tools landscape — Kafka | soft hype | survey-term | ## [041] EVENT-DRIVEN · Event-driven tools landscape — Kafka, Pulsar, Flink, NiFi (sldId 296) |
| ## [110] APPENDIX B · VERSIONING · Evolving a .proto safely  | quietly / silently | machine-subject | > Walk the safe pattern. We removed an old 'notes' field, so we reserve both its tag number (4) and its name permanently: nobody can reuse t |
| ## [113] APPENDIX B · VERSIONING · Principles that cut acros | quietly / silently | machine-subject | - Never break silently: deprecate with a reason, a replacement and a sunset date; measure who's still on the old version. |
| ## [113] APPENDIX B · VERSIONING · Principles that cut acros | quietly / silently | machine-subject | > Step back to the universal principles, because the protocol-specific rules all rhyme. Additive change is safe; removal and mutation break  |
| ## [165] APPENDIX G · COUPLING · Coupling and our APIs (sldI | quietly / silently | machine-subject | - The registry is what keeps that contract coupling stable: compatibility rules stop a producer from silently raising the integration streng |
| ## [165] APPENDIX G · COUPLING · Coupling and our APIs (sldI | quietly / silently | machine-subject | > Bring it home to the talk's content. The reframe to offer: every protocol decision was secretly a coupling decision, and we kept choosing  |
| ## [025] COMPOSITION · A composing resolver in HotChocolate  | em-dash pileup (3+ per line) | notes-paragraph | > The resolver makes federation concrete in HotChocolate. The top-level GetOrder Query calls order-service over REST; [ExtendObjectType<Orde |
| ## [030] DATA · CQRS — Command Query Responsibility Segregat | em-dash pileup (3+ per line) | notes-paragraph | > CQRS (Command Query Responsibility Segregation) is the pattern of using different models for writes and reads. The write side optimises fo |
| ## [034] DATA · The outbox write — one transaction, no lost  | em-dash pileup (3+ per line) | notes-paragraph | > For the WCF/COM+ audience this is THE most important pattern. You used to write code like 'TransactionScope: save order, write to MSMQ, co |
| ## [041] EVENT-DRIVEN · Event-driven tools landscape — Kafka | em-dash pileup (3+ per line) | notes-paragraph | > Each of the four tools does a different job. KAFKA is the SUBSTRATE — a partitioned, ordered, durable log. Consumers track their own offse |
| ## [063] OBSERVABILITY · The signals in depth — traces, metr | em-dash pileup (3+ per line) | notes-paragraph | > Expand the 'three pillars' framing into the five signals modern observability uses. Traces answer WHERE the time went and which hop failed |
| ## [065] OBSERVABILITY · Auto-injection vs. instrumentation  | em-dash pileup (3+ per line) | notes-paragraph | > This is the slide the user specifically asked for: distinguish auto-INJECTION from auto-INSTRUMENTATION from MANUAL instrumentation — thre |
| ## [067] OBSERVABILITY · How correlation works — context pro | em-dash pileup (3+ per line) | notes-paragraph | > Demystify the magic word 'correlation.' It is not a backend join — it's the trace context physically travelling WITH the request, in-band, |
| ## [071] OBSERVABILITY · Choosing a sampling strategy (sldId | em-dash pileup (3+ per line) | notes-paragraph | > The decision guide for sampling. Probabilistic is the simplest and the most common starting point — keep 10%, predictable volume. Rate-lim |
| ## [094] ANTI-PATTERNS · The heuristics that keep you out of | em-dash pileup (3+ per line) | notes-paragraph | > These are the five tests to apply in design and code review. (1) If two services must deploy together, they are one service: merge them or |
| ## [125] APPENDIX D · SAGAS · Where a saga keeps its state ( | em-dash pileup (3+ per line) | notes-paragraph | > First problem: the orchestrator must survive a crash mid-flow, so in-memory state is a non-starter — a Pod restart would strand every in-f |
| ## [126] APPENDIX D · SAGAS · A persisted saga state machine | em-dash pileup (3+ per line) | notes-paragraph | > This is the DB-backed option made concrete with EF Core — the one I'd reach for first when the saga is bounded and I want to own the trans |
| ## [129] APPENDIX D · SAGAS · When step B needs data only st | em-dash pileup (3+ per line) | notes-paragraph | > This is the specific case you asked about, and a common source of bad designs. The orchestrator calls service A, then service B — but B ne |
| ## [133] APPENDIX D · SAGAS · Stateless: lighter, in-process | em-dash pileup (3+ per line) | notes-paragraph | > Walk the picture. The top row is the saga as a state machine: Created → Paid → Reserved → Shipped → Done, with each transition triggered b |
| ## [138] APPENDIX E · ERRORS · REST errors with ASP.NET Core | em-dash pileup (3+ per line) | notes-paragraph | > ASP.NET Core has had ProblemDetails (RFC 9457) built into Microsoft.AspNetCore.Mvc since .NET 6 — the wire format, the media type (applica |
| ## [140] APPENDIX E · ERRORS · gRPC errors with rich status  | em-dash pileup (3+ per line) | notes-paragraph | > This is grpc-dotnet's standard rich-error model — the same wire shape as every other gRPC stack because google.rpc.Status is the cross-lan |
| ## [144] APPENDIX E · ERRORS · GraphQL field errors with Hot | em-dash pileup (3+ per line) | notes-paragraph | > Throwing from a single field's resolver is exactly right: HotChocolate's exception-resolution chain catches it, sets that field to null, a |
| ## [154] APPENDIX F · HEXAGONAL · Ports & adapters in code ( | em-dash pileup (3+ per line) | notes-paragraph | > Walk the three blocks. Ports: the domain declares plain C# interfaces, a repository and an event publisher, and depends on nothing else (n |
| ## [158] APPENDIX G · COUPLING · Coupling is necessary — bal | em-dash pileup (3+ per line) | notes-paragraph | > Frame the appendix. The central, slightly contrarian idea: coupling is not a defect to be driven to zero — it's necessary, and the real sk |
| ## [161] APPENDIX G · COUPLING · Integration strength: a lad | em-dash pileup (3+ per line) | notes-paragraph | > Integration strength has four levels, worst to best. Intrusive coupling: one component reaches into another's private internals — the clas |
| ## [163] APPENDIX G · COUPLING · Balancing coupling: strengt | em-dash pileup (3+ per line) | notes-paragraph | > This brings strength and distance together into the design rule. Read the quadrants: high strength and close together is a cohesive module |
| ## [172] APPENDIX H · SHUTDOWN · Graceful shutdown in ASP.NE | em-dash pileup (3+ per line) | notes-paragraph | > ASP.NET Core has clean graceful shutdown built in. When Kubernetes sends SIGTERM, the .NET host signals IHostApplicationLifetime.Applicati |
| ## [205] APPENDIX I · L7 ROUTING · L7 routing checklist (sld | em-dash pileup (3+ per line) | notes-paragraph | > Leave the checklist up at the end. The first point is the most common organisational failure — a cluster ends up running three ingress con |
| ## [220] APPENDIX K · ROUTING · Content-based routing during | em-dash pileup (3+ per line) | notes-paragraph | > The .NET shape. Three named HttpClients registered via IHttpClientFactory — the canonical pattern for managed HttpClient lifetimes in ASP. |
| ## [231] APPENDIX L · WRITE-THROUGH · Write-through in ASP.N | em-dash pileup (3+ per line) | notes-paragraph | > Two write-through flavours. The first uses IDistributedCache directly: save EF Core changes, then SetStringAsync to update the cache with  |
| ## [235] APPENDIX L · WRITE-BACK · Write-back with Backgroun | em-dash pileup (3+ per line) | notes-paragraph | > Write-back in .NET. The handler writes to a Redis hash (the metric fields) and adds the key to a 'dirty set' — the dirty set tells the flu |
| ## [262] APPENDIX M · Take-aways and references (sldId 517) | exclamation in prose | quoted |   - References: Google SRE Book (chapters on Addressing Cascading Failures, Handling Overload); 'Release It!' (Nygard — circuit breaker, bul |
| ## [262] APPENDIX M · Take-aways and references (sldId 517) | exclamation in prose | quoted | > Close the appendix and, since it's the last appendix, effectively close the deck's technical content. The take-aways are the imperatives:  |
| ## [312] APPENDIX R · MINIKUBE · Recorded results (sldId 567 | parallel-number title | table-data | - 10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0). |
| ## [002] AGENDA · Agenda (sldId 257) | environment-specific noun | literal-subject | - Appendices P–R · .NET on Linux, Blazor, minikube |
| ## [002] AGENDA · Agenda (sldId 257) | environment-specific noun | literal-subject | > The appendices are reference material for the questions that come up: protocols, versioning, WebSockets, sagas, errors, DDD, coupling, shu |
| ## [003] OVERVIEW · What we'll build, and the order we'll bu | environment-specific noun | literal-subject | > Walk the arc quickly; don't dwell. The order follows dependency: principles first because they justify every later choice, then the synchr |
| ## [304] Example 05 on minikube (sldId 559) | environment-specific noun | literal-subject | ## [304] Example 05 on minikube (sldId 559) |
| ## [304] Example 05 on minikube (sldId 559) | environment-specific noun | literal-subject | > Appendix R takes Example 05, the event-driven fan-out, from docker compose to a single-node Kubernetes cluster on minikube, in all six lan |
| ## [305] APPENDIX R · MINIKUBE · From compose to a cluster ( | environment-specific noun | literal-subject | ## [305] APPENDIX R · MINIKUBE · From compose to a cluster (sldId 560) |
| ## [306] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | ## [306] APPENDIX R · MINIKUBE · The minikube runtime (sldId 561) |
| ## [306] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | - No kubectl port-forward, minikube tunnel or minikube service: forwarded connections drop. |
| ## [306] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | minikube v1.39.0 · kubectl v1.36.5 · Helm v4.3.0 · Strimzi 1.2.0 |
| ## [306] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > minikube runs the control plane and the workload in one container on Docker Engine, the same engine compose uses, with containerd as the c |
| ## [306] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > Host access uses two NodePorts published on the loopback address when the profile is created. Port-forwarding, minikube tunnel and minikub |
| ## [306] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > The kubectl context never changes: every command names --context cndp-k8s, minikube start runs with --keep-context, and setup-profile.sh r |
| ## [307] APPENDIX R · MINIKUBE · One node, two namespaces (s | environment-specific noun | literal-subject | ## [307] APPENDIX R · MINIKUBE · One node, two namespaces (sldId 562) |
| ## [307] APPENDIX R · MINIKUBE · One node, two namespaces (s | environment-specific noun | literal-subject | > From the host, curl and verify.sh reach order-service on 127.0.0.1:30080, a browser reaches Grafana on 127.0.0.1:30300, and kubectl exec r |
| ## [308] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldI | environment-specific noun | literal-subject | ## [308] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldId 563) |
| ## [308] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldI | environment-specific noun | literal-subject | - build: → docker build, then minikube image load; imagePullPolicy: Never. |
| ## [309] APPENDIX R · MINIKUBE · One overlay per language (s | environment-specific noun | literal-subject | ## [309] APPENDIX R · MINIKUBE · One overlay per language (sldId 564) |
| ## [310] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | ## [310] APPENDIX R · MINIKUBE · Images built on the host (sldId 565) |
| ## [310] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | docker build on the host, minikube image load into the node; pods never pull |
| ## [310] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | > The cluster does not build images. Each service is built on the host with docker build, which keeps the host's BuildKit caches (a cold C++ |
| ## [311] APPENDIX R · MINIKUBE · Run it (sldId 566) | environment-specific noun | literal-subject | ## [311] APPENDIX R · MINIKUBE · Run it (sldId 566) |
| ## [311] APPENDIX R · MINIKUBE · Run it (sldId 566) | environment-specific noun | literal-subject | [chip] bash · minikube |
| ## [311] APPENDIX R · MINIKUBE · Run it (sldId 566) | environment-specific noun | literal-subject | > What to show: the ten check marks and the Results line, then Grafana on 127.0.0.1:30300. Fallback: the recorded results that follow. teard |
| ## [312] APPENDIX R · MINIKUBE · Recorded results (sldId 567 | environment-specific noun | literal-subject | ## [312] APPENDIX R · MINIKUBE · Recorded results (sldId 567) |
| ## [312] APPENDIX R · MINIKUBE · Recorded results (sldId 567 | environment-specific noun | literal-subject | - 10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0). |

## Designing-Cloud-Native-APIs-Go

| Slide | Pattern | Reason | Text |
|---|---|---|---|
| ## [227] APPENDIX M · Distributed systems fail differently ( | lie / lies / lying (person vs machine) | machine-subject | - Some failures lie: a node passes its own health check while failing real traffic (gray failure). What the system believes about itself and |
| ## [248] APPENDIX M · Take-aways and references (sldId 503) | lie / lies / lying (person vs machine) | machine-subject | - Design for partial failure from the start: every remote call can succeed, fail, hang, or lie. Timeout everything; the default is often inf |
| ## [088] SECURITY · Choosing the right pattern (sldId 343) | deliberate (adjective) | planned-stage | > Close the section with the decision rules. The cost lines are there because every pattern is a trade. Sidecar costs a container per Pod (a |
| ## [205] APPENDIX K · STRANGLER FIG · With a shared database | deliberate (adjective) | planned-stage | ## [205] APPENDIX K · STRANGLER FIG · With a shared database — a deliberate intermediate state (sldId 460) |
| ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka | soft hype | survey-term | ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka, Pulsar, Flink, NiFi (sldId 294) |
| ## [108] APPENDIX B · VERSIONING · Evolving a .proto safely  | quietly / silently | machine-subject | > Walk the safe pattern. We removed an old 'notes' field, so we reserve both its tag number (4) and its name permanently: nobody can reuse t |
| ## [111] APPENDIX B · VERSIONING · Principles that cut acros | quietly / silently | machine-subject | - Never break silently: deprecate with a reason, a replacement and a sunset date; measure who's still on the old version. |
| ## [111] APPENDIX B · VERSIONING · Principles that cut acros | quietly / silently | machine-subject | > Step back to the universal principles, because the protocol-specific rules all rhyme. Additive change is safe; removal and mutation break  |
| ## [157] APPENDIX G · COUPLING · Coupling and our APIs (sldI | quietly / silently | machine-subject | - The registry is what keeps that contract coupling stable: compatibility rules stop a producer from silently raising the integration streng |
| ## [157] APPENDIX G · COUPLING · Coupling and our APIs (sldI | quietly / silently | machine-subject | > Bring it home to the talk's content. The reframe to offer: every protocol decision was secretly a coupling decision, and we kept choosing  |
| ## [028] DATA · CQRS — Command Query Responsibility Segregat | em-dash pileup (3+ per line) | notes-paragraph | > CQRS (Command Query Responsibility Segregation) is the pattern of using different models for writes and reads. The write side optimises fo |
| ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka | em-dash pileup (3+ per line) | notes-paragraph | > Each of the four tools does a different job. KAFKA is the SUBSTRATE — a partitioned, ordered, durable log. Consumers track their own offse |
| ## [061] OBSERVABILITY · The signals in depth — traces, metr | em-dash pileup (3+ per line) | notes-paragraph | > Expand the 'three pillars' framing into the five signals modern observability uses. Traces answer WHERE the time went and which hop failed |
| ## [063] OBSERVABILITY · Auto-injection vs. instrumentation  | em-dash pileup (3+ per line) | notes-paragraph | > This is the slide the user specifically asked for: distinguish auto-INJECTION from auto-INSTRUMENTATION from MANUAL instrumentation — thre |
| ## [065] OBSERVABILITY · How correlation works — context pro | em-dash pileup (3+ per line) | notes-paragraph | > Demystify the magic word 'correlation.' It is not a backend join — it's the trace context physically travelling WITH the request, in-band, |
| ## [069] OBSERVABILITY · Choosing a sampling strategy (sldId | em-dash pileup (3+ per line) | notes-paragraph | > The decision guide for sampling. Probabilistic is the simplest and the most common starting point — keep 10%, predictable volume. Rate-lim |
| ## [092] ANTI-PATTERNS · The heuristics that keep you out of | em-dash pileup (3+ per line) | notes-paragraph | > These are the five tests to apply in design and code review. (1) If two services must deploy together, they are one service: merge them or |
| ## [121] APPENDIX D · SAGAS · Where a Go saga keeps its stat | em-dash pileup (3+ per line) | notes-paragraph | > First problem: the orchestrator must survive a crash mid-flow, so in-memory state is a non-starter — a pod restart would strand every in-f |
| ## [125] APPENDIX D · SAGAS · When step B needs data only st | em-dash pileup (3+ per line) | notes-paragraph | > This is the specific case you asked about, and a common source of bad designs. The orchestrator calls service A, then service B — but B ne |
| ## [150] APPENDIX G · COUPLING · Coupling is necessary — bal | em-dash pileup (3+ per line) | notes-paragraph | > Frame the appendix. The central, slightly contrarian idea: coupling is not a defect to be driven to zero — it's necessary, and the real sk |
| ## [153] APPENDIX G · COUPLING · Integration strength: a lad | em-dash pileup (3+ per line) | notes-paragraph | > Integration strength has four levels, worst to best. Intrusive coupling: one component reaches into another's private internals — the clas |
| ## [155] APPENDIX G · COUPLING · Balancing coupling: strengt | em-dash pileup (3+ per line) | notes-paragraph | > This brings strength and distance together into the design rule. Read the quadrants: high strength and close together is a cohesive module |
| ## [203] APPENDIX K · STRANGLER FIG · With a proxy — step ze | em-dash pileup (3+ per line) | notes-paragraph | > The pre-condition for incremental migration: clients hit the proxy, the proxy forwards to the monolith. Day zero, behaviour is unchanged.  |
| ## [215] APPENDIX L · READ-THROUGH · Read-through in Go: a g | em-dash pileup (3+ per line) | notes-paragraph | > The wrapper is small but the discipline is significant. Callers can't accidentally bypass the cache or forget to populate it — they call p |
| ## [219] APPENDIX L · WRITE-AROUND · Write-around in Go (sld | em-dash pileup (3+ per line) | notes-paragraph | > Two write variants and the standard cache-aside read for context. The pure write-around just inserts to the DB — the cache isn't touched a |
| ## [221] APPENDIX L · WRITE-BACK · Write-back with a backgro | em-dash pileup (3+ per line) | notes-paragraph | > Write-back has more moving parts than the other patterns; the slide shows the canonical shape. (1) Writes go to cache and add the key to a |
| ## [248] APPENDIX M · Take-aways and references (sldId 503) | exclamation in prose | quoted |   - References: Google SRE Book (chapters on Addressing Cascading Failures, Handling Overload); 'Release It!' (Nygard — circuit breaker, bul |
| ## [248] APPENDIX M · Take-aways and references (sldId 503) | exclamation in prose | quoted | > Close the appendix and, since it's the last appendix, effectively close the deck's technical content. The take-aways are the imperatives:  |
| ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536 | parallel-number title | table-data | - 10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0). |
| ## [001] CLOUD-NATIVE ARCHITECTURE · Designing Cloud-Native  | environment-specific noun | literal-subject | > Welcome and framing. This is a working architect's tour of designing cloud-native APIs — not a survey of buzzwords. Set expectations: we b |
| ## [002] AGENDA · Agenda (sldId 257) | environment-specific noun | literal-subject | - Appendix R · Example 05 on minikube |
| ## [002] AGENDA · Agenda (sldId 257) | environment-specific noun | literal-subject | > The appendices are reference material for the questions that come up: protocols, versioning, WebSockets, sagas, errors, DDD, coupling, shu |
| ## [003] OVERVIEW · What we'll build, and the order we'll bu | environment-specific noun | literal-subject | > Walk the arc quickly; don't dwell. The order follows dependency: principles first because they justify every later choice, then the synchr |
| ## [273] Example 05 on minikube (sldId 528) | environment-specific noun | literal-subject | ## [273] Example 05 on minikube (sldId 528) |
| ## [273] Example 05 on minikube (sldId 528) | environment-specific noun | literal-subject | > Appendix R takes Example 05, the event-driven fan-out, from docker compose to a single-node Kubernetes cluster on minikube, in all six lan |
| ## [274] APPENDIX R · MINIKUBE · From compose to a cluster ( | environment-specific noun | literal-subject | ## [274] APPENDIX R · MINIKUBE · From compose to a cluster (sldId 529) |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId 530) |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | - No kubectl port-forward, minikube tunnel or minikube service: forwarded connections drop. |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | minikube v1.39.0 · kubectl v1.36.5 · Helm v4.3.0 · Strimzi 1.2.0 |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > minikube runs the control plane and the workload in one container on Docker Engine, the same engine compose uses, with containerd as the c |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > Host access uses two NodePorts published on the loopback address when the profile is created. Port-forwarding, minikube tunnel and minikub |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > The kubectl context never changes: every command names --context cndp-k8s, minikube start runs with --keep-context, and setup-profile.sh r |
| ## [276] APPENDIX R · MINIKUBE · One node, two namespaces (s | environment-specific noun | literal-subject | ## [276] APPENDIX R · MINIKUBE · One node, two namespaces (sldId 531) |
| ## [276] APPENDIX R · MINIKUBE · One node, two namespaces (s | environment-specific noun | literal-subject | > From the host, curl and verify.sh reach order-service on 127.0.0.1:30080, a browser reaches Grafana on 127.0.0.1:30300, and kubectl exec r |
| ## [277] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldI | environment-specific noun | literal-subject | ## [277] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldId 532) |
| ## [277] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldI | environment-specific noun | literal-subject | - build: → docker build, then minikube image load; imagePullPolicy: Never. |
| ## [278] APPENDIX R · MINIKUBE · One overlay per language (s | environment-specific noun | literal-subject | ## [278] APPENDIX R · MINIKUBE · One overlay per language (sldId 533) |
| ## [279] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | ## [279] APPENDIX R · MINIKUBE · Images built on the host (sldId 534) |
| ## [279] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | docker build on the host, minikube image load into the node; pods never pull |
| ## [279] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | > The cluster does not build images. Each service is built on the host with docker build, which keeps the host's BuildKit caches (a cold C++ |
| ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) | environment-specific noun | literal-subject | ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) |
| ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) | environment-specific noun | literal-subject | [chip] bash · minikube |
| ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) | environment-specific noun | literal-subject | > What to show: the ten check marks and the Results line, then Grafana on 127.0.0.1:30300. Fallback: the recorded results that follow. teard |
| ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536 | environment-specific noun | literal-subject | ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536) |
| ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536 | environment-specific noun | literal-subject | - 10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0). |

## Designing-Cloud-Native-APIs-Cpp

| Slide | Pattern | Reason | Text |
|---|---|---|---|
| ## [227] APPENDIX M · Distributed systems fail differently ( | lie / lies / lying (person vs machine) | machine-subject | - Some failures lie: a node passes its own health check while failing real traffic (gray failure). What the system believes about itself and |
| ## [232] APPENDIX M · COMPONENT · Gray failure (sldId 487) | lie / lies / lying (person vs machine) | machine-subject | > Gray failure is the failure that lies. The /healthz endpoint returns 200; real traffic is timing out. The node passes its own check; clien |
| ## [248] APPENDIX M · Take-aways and references (sldId 503) | lie / lies / lying (person vs machine) | machine-subject | - Design for partial failure from the start: every remote call can succeed, fail, hang, or lie. Timeout everything; the default is often inf |
| ## [205] APPENDIX K · STRANGLER FIG · With a shared database | deliberate (adjective) | planned-stage | ## [205] APPENDIX K · STRANGLER FIG · With a shared database — a deliberate intermediate state (sldId 460) |
| ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka | soft hype | survey-term | ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka, Pulsar, Flink, NiFi (sldId 294) |
| ## [037] EVENT-DRIVEN · Schemas are the contract — the regis | quietly / silently | machine-subject | > Schema registry (Apicurio) is non-optional for production event-driven systems. Without it, a producer can ship a breaking schema change a |
| ## [111] APPENDIX B · VERSIONING · Principles that cut acros | quietly / silently | machine-subject | - Never break silently: deprecate with a reason, a replacement and a sunset date; measure who's still on the old version. |
| ## [020] COMMUNICATIONS · The mesh handles the wire, not you | em-dash pileup (3+ per line) | notes-paragraph | > The Istio sidecar handles wire concerns: mTLS, bounded retries with backoff, timeouts, outlier detection, hop-level telemetry. The C++ tem |
| ## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka | em-dash pileup (3+ per line) | notes-paragraph | > Three layers of the event-driven stack: (1) substrate — Kafka (Strimzi on Kubernetes) and Pulsar are the durable log. Pick Kafka by defaul |
| ## [049] WORKFLOWS AND JOBS · Jobs, CronJobs and queue worke | em-dash pileup (3+ per line) | notes-paragraph | > Three Kubernetes-native patterns for non-request work. (1) Job: a one-shot batch — run a data migration, a backfill, a nightly export. The |
| ## [066] OBSERVABILITY · Baggage in practice — carry request | em-dash pileup (3+ per line) | notes-paragraph | > Baggage is a separate concern from trace context — they ride together but carry different data. Trace context (traceparent) tells you 'thi |
| ## [108] APPENDIX B · VERSIONING · Evolving a .proto safely  | em-dash pileup (3+ per line) | notes-paragraph | > The four rules of safe proto evolution, in one example: (1) add new fields at new tag numbers (currency=5, state=6). (2) Use `reserved` fo |
| ## [121] APPENDIX D · SAGAS · Where a C++ saga keeps its sta | em-dash pileup (3+ per line) | notes-paragraph | > Three options for saga state durability. (1) Database row — one row per saga, row-locked for the duration of advance(); cheapest for short |
| ## [128] APPENDIX E · ERRORS · One error model, four wire fo | em-dash pileup (3+ per line) | notes-paragraph | > Five facts that every error needs to carry, regardless of protocol: (1) a STABLE machine code (STOCK_UNAVAILABLE) — never a string the cli |
| ## [131] APPENDIX E · ERRORS · gRPC: status codes + rich det | em-dash pileup (3+ per line) | notes-paragraph | > gRPC's error model is two layers: (1) one of ~16 canonical codes (OK, CANCELLED, UNAVAILABLE, NOT_FOUND, etc.) — a small enum, well-define |
| ## [137] APPENDIX E · ERRORS · How a retry storm forms — and | em-dash pileup (3+ per line) | notes-paragraph | > The retry storm is the classic distributed-systems amplification failure. A downstream service slows down; clients retry; the retries add  |
| ## [151] APPENDIX G · COUPLING · Coupling has three dimensio | em-dash pileup (3+ per line) | notes-paragraph | > Three dimensions, each measurable. STRENGTH: how intensely are the two things coupled — shared memory? shared schema? shared events? share |
| ## [202] APPENDIX K · STRANGLER FIG · Identify → move → redi | em-dash pileup (3+ per line) | notes-paragraph | > Martin Fowler's strangler fig pattern is the safest large-migration approach known. Three steps per slice: (1) IDENTIFY the seam — what is |
| ## [248] APPENDIX M · Take-aways and references (sldId 503) | exclamation in prose | quoted | - References: Google SRE Book (chapters on Addressing Cascading Failures, Handling Overload); 'Release It!' (Nygard — circuit breaker, bulkh |
| ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536 | parallel-number title | table-data | - 10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0). |
| ## [002] AGENDA · Agenda (sldId 257) | environment-specific noun | literal-subject | - Appendix R · Example 05 on minikube |
| ## [002] AGENDA · Agenda (sldId 257) | environment-specific noun | literal-subject | > Appendix R runs Example 05 on minikube with the same verify.sh as compose. |
| ## [273] Example 05 on minikube (sldId 528) | environment-specific noun | literal-subject | ## [273] Example 05 on minikube (sldId 528) |
| ## [273] Example 05 on minikube (sldId 528) | environment-specific noun | literal-subject | > Appendix R takes Example 05, the event-driven fan-out, from docker compose to a single-node Kubernetes cluster on minikube, in all six lan |
| ## [274] APPENDIX R · MINIKUBE · From compose to a cluster ( | environment-specific noun | literal-subject | ## [274] APPENDIX R · MINIKUBE · From compose to a cluster (sldId 529) |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId 530) |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | - No kubectl port-forward, minikube tunnel or minikube service: forwarded connections drop. |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | minikube v1.39.0 · kubectl v1.36.5 · Helm v4.3.0 · Strimzi 1.2.0 |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > minikube runs the control plane and the workload in one container on Docker Engine, the same engine compose uses, with containerd as the c |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > Host access uses two NodePorts published on the loopback address when the profile is created. Port-forwarding, minikube tunnel and minikub |
| ## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId | environment-specific noun | literal-subject | > The kubectl context never changes: every command names --context cndp-k8s, minikube start runs with --keep-context, and setup-profile.sh r |
| ## [276] APPENDIX R · MINIKUBE · One node, two namespaces (s | environment-specific noun | literal-subject | ## [276] APPENDIX R · MINIKUBE · One node, two namespaces (sldId 531) |
| ## [276] APPENDIX R · MINIKUBE · One node, two namespaces (s | environment-specific noun | literal-subject | > From the host, curl and verify.sh reach order-service on 127.0.0.1:30080, a browser reaches Grafana on 127.0.0.1:30300, and kubectl exec r |
| ## [277] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldI | environment-specific noun | literal-subject | ## [277] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldId 532) |
| ## [277] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldI | environment-specific noun | literal-subject | - build: → docker build, then minikube image load; imagePullPolicy: Never. |
| ## [278] APPENDIX R · MINIKUBE · One overlay per language (s | environment-specific noun | literal-subject | ## [278] APPENDIX R · MINIKUBE · One overlay per language (sldId 533) |
| ## [279] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | ## [279] APPENDIX R · MINIKUBE · Images built on the host (sldId 534) |
| ## [279] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | docker build on the host, minikube image load into the node; pods never pull |
| ## [279] APPENDIX R · MINIKUBE · Images built on the host (s | environment-specific noun | literal-subject | > The cluster does not build images. Each service is built on the host with docker build, which keeps the host's BuildKit caches (a cold C++ |
| ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) | environment-specific noun | literal-subject | ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) |
| ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) | environment-specific noun | literal-subject | [chip] bash · minikube |
| ## [280] APPENDIX R · MINIKUBE · Run it (sldId 535) | environment-specific noun | literal-subject | > What to show: the ten check marks and the Results line, then Grafana on 127.0.0.1:30300. Fallback: the recorded results that follow. teard |
| ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536 | environment-specific noun | literal-subject | ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536) |
| ## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536 | environment-specific noun | literal-subject | - 10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0). |
| ## [107] APPENDIX B · VERSIONING · gRPC / protobuf: what is  | quietly / silently | machine-subject | > protobuf's contract is the field numbers, not the field names. This means renaming a field is safe on the wire (old serialised bytes still |

## K8s-Environment-Access-Policies

| Slide | Pattern | Reason | Text |
|---|---|---|---|
| ## [003] THREE ENVIRONMENTS · Risk profiles by environment ( | em-dash pileup (3+ per line) | notes-paragraph | > Walk through the three environments as a risk gradient. Dev is where developers experiment, iterate, and break things — full self-service  |
| ## [005] RBAC · MATRIX · Environment-specific RBAC matrix (s | em-dash pileup (3+ per line) | notes-paragraph | > Walk the RBAC matrix column by column. In dev, developers get full CRUD on pods, deployments, services, ConfigMaps, Secrets, and NetworkPo |
| ## [006] NETWORKPOLICY · ZERO TRUST · Default-deny NetworkPo | em-dash pileup (3+ per line) | notes-paragraph | > This is the single highest-impact security measure you can apply to a Kubernetes namespace. Without any NetworkPolicy, Kubernetes allows a |
| ## [007] NETWORKPOLICY · BY ENVIRONMENT · NetworkPolicy by e | em-dash pileup (3+ per line) | notes-paragraph | > The same default-deny baseline applies everywhere, but the allow rules differ by environment. In dev, allow all intra-namespace traffic so |
| ## [012] L7 ROUTING · SAFE ROLLOUTS · Traffic steering for s | em-dash pileup (3+ per line) | notes-paragraph | > L7 routing enables environment-safe deployments without modifying RBAC or network policies. Walk through four patterns: Canary deploys rou |
| ## [013] NAMESPACE ISOLATION · Namespace isolation architect | em-dash pileup (3+ per line) | notes-paragraph | > A well-governed namespace is a blast-radius boundary with four controls stacked. RBAC determines who can act in this namespace via RoleBin |
| ## [015] AUDIT & COMPLIANCE · Audit & compliance (sldId 270) | em-dash pileup (3+ per line) | notes-paragraph | > Governance requires more than access control — it requires proof that the controls are working. Walk through four audit dimensions. API se |
| ## [017] SUMMARY · Recommendations (sldId 272) | em-dash pileup (3+ per line) | notes-paragraph | > Close with the priority-ordered checklist. First, apply default-deny NetworkPolicy in every namespace — it is the single highest-impact se |
