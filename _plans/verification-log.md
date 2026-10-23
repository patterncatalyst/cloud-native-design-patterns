# Verification log

Per-chapter verification-status footers moved here from the chapter bodies. The
reader-facing chapters now carry a `## Build, run, observe` section (the former
"Cross-check it yourself" section, with the example's verify command) instead;
the run records stay here. The `plans` collection is `output: false`, so this
file is not published. Each entry is the footer text verbatim as it last stood.

## 00-setting-up.md
conceptual chapter; no runnable code. The patterns named here are defined and applied in their own chapters, where the code ships with a runnable example per language.

## 01-cloud-native-principles.md
verified; examples/01-cloud-native-principles/ passes 13/13 checks in each of the six languages on Docker Engine (2026-10-13) (health probes, config from environment, CRUD, readiness flip on dependency failure).

## 02-communications.md
verified; examples/02-communications/ passes 10/10 checks in each of the six languages on Docker Engine (2026-10-13) (REST create and validation (201, 422), cursor pagination, order confirmation and rejection driven by the gRPC stock reservation, a GraphQL orders query, and the order.placed Kafka topic).

## 03-composition.md
verified; examples/03-composition/ passes 8/8 checks in each of the six languages on Docker Engine (2026-10-13) (GraphQL gateway fan-out to the REST order API and the gRPC stock service, selective stock-field resolution, DataLoader batching of stock lookups into one gRPC call, single-order lookup).

## 04-data.md
verified; examples/04-data/ passes 8/8 checks in each of the six languages on Docker Engine (2026-10-13) (transactional write of order and outbox row, Debezium outbox connector running, relay of the outbox event to the order.placed Kafka topic with its payload).

## 05-event-driven.md
verified; examples/05-event-driven/ passes 10/10 checks in each of the six languages on Docker Engine (2026-10-13) and on minikube (2026-10-11, Appendix R), and 10/10 in five languages on OpenShift Local 4.22.14 (2026-10-11, Appendix S) (event publication to order.placed, fan-out to two independent consumer groups (shipping and notification), and idempotent consumers under a redelivered duplicate event).

## 06-stream-processing.md
verified; examples/06-stream-processing/ passes 11/11 checks in each of the six languages on Docker Engine (2026-10-13) (per-merchant revenue aggregation onto a derived Kafka topic, the stream-processor consumer group, consumer lag that builds while the processor is paused and drains on resume, and the burst appearing in the revenue stream).

## 07-workflows-and-jobs.md
conceptual chapter with an illustrative Kubernetes manifest; no per-language runnable example. The coordination patterns it names are made concrete in the saga appendix.

## 08-api-management.md
conceptual chapter: no per-language runnable code. The runtime-plane and contract-plane behaviours it describes are exercised in the security, registry, and Appendix B chapters.

## 09-api-registry.md
verified; examples/09-api-registry/ passes 8/8 checks on Docker Engine (2026-10-13) (schema registration, BACKWARD compatibility rule, rejection of a breaking change with 400, acceptance of an additive change, versioned retrieval). Language-agnostic (single Apicurio stack).

## 10-api-metadata.md
conceptual chapter: no per-language runnable code. The discovery, lineage, and trust capabilities it describes are exercised against a running OpenMetadata catalog in the example stack.

## 11-observability.md
verified; examples/11-observability/ passes 10/10 checks in each of the six languages on Docker Engine (2026-10-13) (trace propagation, metric export, structured log correlation, LGTM stack integration).

## 12-security.md
verified; examples/12-security/ passes 18/18 checks in each of the six languages on Docker Engine (2026-10-13) (sidecar identity trust (403 without X-Forwarded-Client-Cert, health-check bypass), propagation of the JWT subject claim, valet-key mint/verify/tamper rejection, per-tenant bulkhead state, a full tenant pool refusing the overflow with 429 while another tenant is still served, and conftest Rego policy evaluation of a good and a bad manifest. JWT signature validation, RBAC enforcement and rate limiting are not covered).

## 13-anti-patterns.md
conceptual chapter; no runnable code. Its heuristics are the review-time application of the patterns proven in the earlier chapters.

## 14-appendix-a-protocols.md
the gRPC stub call and server-streaming handler are shown in all six languages and mirror the patterns compiled and run in the Communications chapter; the comparison axes, streaming modes, and performance levers are conceptual. The protocol choices this appendix argues are exercised in Communications and Composition.

## 15-appendix-b-versioning.md
unverified: examples transcribed from the source decks; the REST, gRPC, and GraphQL compatibility behaviour and the Kafka schema.version header are exercised against the registry in the examples/09-api-registry/ runner.

## 16-appendix-c-websockets.md
verified; examples/16-websockets/ passes 6/6 checks in each of the six languages on Docker Engine (2026-10-13) (WebSocket connect, cross-pod delivery and broadcast over the Redis pub/sub backplane, monotonic sequence numbers).

## 17-appendix-d-sagas.md
verified; examples/17-sagas/ passes 11/11 checks in each of the six languages on Docker Engine (2026-10-13) (orchestrated saga happy path, compensation in reverse order on failure, skipped compensation for steps that never completed, resume of a RUNNING saga after an orchestrator restart).

## 18-appendix-e-errors.md
verified; examples/18-errors/ passes 13/13 checks in each of the six languages on Docker Engine (2026-10-13) (RFC 9457 problem details over REST for validation (422), stock conflict (409) and upstream unavailable (503), with error codes, traceId, retryable and retryAfter fields).

## 19-appendix-f-ddd-hexagonal.md
verified; examples/19-ddd-hexagonal/ passes 17/17 checks in each of the six languages on Docker Engine (2026-10-13) (source scans proving the domain layer imports no framework or persistence types, REST and CLI adapters driving the same use case, input validation, OrderPlaced event emission).

## 20-appendix-g-coupling.md
unverified. Conceptual appendix with no runnable example; its claims are model-level (Khononov's Balancing Coupling). Verification here means a design review confirms the three-dimension scoring matches how changes propagate in a real system.

## 21-appendix-h-shutdown.md
verified; examples/21-graceful-shutdown/ passes 17/17 checks in each of the six languages on Docker Engine (2026-10-13) (one SIGTERM, readiness flip to 503, the drain log lines, exit code 0 inside the grace period, a docker stop timing check, restart recovery, and orders persisting across the restart. In-flight request draining is not checked by the script).

## 22-appendix-i-l7-routing.md
verified; examples/22-l7-routing/ passes 15/15 checks in each of the six languages on Docker Engine (2026-10-13) (Envoy weighted traffic split, header-based routing override, in-app rule-driven routing, and changing routing rules without a redeploy. Canary promotion and circuit breaking are not covered).

## 23-appendix-j-dotnet-toolkit.md
package versions and licenses checked against nuget.org on 2026-10-10 (Confluent.Kafka 2.16.0 Apache-2.0; Streamiz.Kafka.Net 1.8.2 MIT; Temporalio, Asp.Versioning, Microsoft.Extensions.Resilience MIT; Polly 8 BSD-3-Clause). MassTransit v9 and MediatR are commercially licensed, which is why the examples use Confluent.Kafka directly and Wolverine is the OSS alternative. Three tables transcribed from the source deck; .NET 10 LTS support window through Nov 2028 per Microsoft policy. No per-language examples/ runner for this appendix.

## 24-appendix-k-monolith-to-microservices.md
verified; examples/24-monolith-to-microservices/ passes 19/19 checks in each of the six languages on Docker Engine (2026-10-13) (strangler fig router with per-tenant routing, reversible cutover, a decorating collaborator adding caching and Kafka event emission, and an untouched legacy service).

## 25-appendix-l-caching.md
verified; examples/25-caching/ passes 29/29 checks in each of the six languages on Docker Engine (2026-10-13) (cache-aside with invalidation on update, read-through, write-through, write-around, write-back with 202 and a flush retry across a Postgres outage, refresh-ahead, hot-set tracking, and degradation with Redis stopped and restarted).

## 26-appendix-m-failure-modes.md
verified; examples/26-failure-modes/ passes 22/22 checks in each of the six languages on Docker Engine (2026-10-13) (timeout, retry exhaustion, circuit breaker closed/open/recovered with fallback, deadline-budget propagation, bulkhead limit, a full bulkhead refusing the overflow with 429 and admitting again).

## 27-appendix-n-feature-flags.md
verified; examples/27-feature-flags/ passes 14/14 checks in each of the six languages on Docker Engine (2026-10-13) (plan-based targeting rules, sticky assignment and percentage rollout, kill switch, simple boolean flag, flag listing, and safe defaults while flagd is down).

## 28-appendix-o-newman.md
verified; examples/28-newman/ passes 11/11 checks on Docker Engine (2026-10-13) (a Newman collection run with status-code and state assertions (201, 422, 404, 204, cancel) and JUnit XML export). Language-agnostic (single stack).

## 29-appendix-p-dotnet-on-linux.md
unverified. The three diagrams (P.1 compilation pipeline, P.2 Kestrel pipeline, P.3 container layers) are structurally correct for the .NET 10 architecture, and the Containerfile pattern matches the verified examples. UBI image sizes (~780 MB SDK, ~170 MB runtime) are approximate and vary by .NET version. The NativeAOT section describes general-availability behaviour as of .NET 8+.

## 29-glossary.md
compiled from the book's own usage: every entry appears in the chapters or appendices. Expansions follow each technology's canonical naming; where a term is overloaded (ACL), the meaning used in this book is called out explicitly.

## 30-appendix-q-blazor-signalr.md
verified; examples/30-blazor-signalr/ passes 10/10 checks on Docker Engine (2026-10-13): health, order placement and listing, the dashboard page, the SignalR negotiate endpoint, a second dashboard instance, Redis backplane delivery in both directions between the two instances, orders listed across instances, and backplane delivery to a restarted instance. Blazor circuit reconnection is the framework default and is not covered by the script. .NET-only.

## 31-appendix-r-minikube.md
verified; examples/05-event-driven/k8s/ passes 10/10 checks in each of the six languages on minikube v1.39.0 (Docker driver, containerd, Kubernetes v1.36.5, Strimzi 1.2.0, 2026-10-13, on the code after the S13 and S14 refactors), using the same verify.sh as compose with RUNTIME=kubernetes. No pod restarted or was OOM-killed under the manifests' memory limits. The consumer scale-down and scale-up in the cross-check was run by hand and is not part of the script.

## 32-appendix-s-openshift-local.md
verified; examples/05-event-driven/openshift/ passes 10/10 checks in each of the five languages on OpenShift Local 4.22.14 (crc 2.64.0, Kubernetes v1.35.6, AMQ Streams amqstreams.v3.2.1-14, Kafka 4.2.0, 2026-10-13, on the code after the S13 and S14 refactors), using the same verify.sh as compose with RUNTIME=kubernetes over HTTPS. Every pod ran under restricted-v2, Tempo held a trace with all three services for each language, and teardown left the cluster empty and stopped. The SCC rejection of a fixed root user ID was not exercised.
