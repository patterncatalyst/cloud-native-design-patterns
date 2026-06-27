---
title: ".NET 10 Toolkit & Migration Reference"
marker: "J"
label: "Appendix J"
order: 23
part: "Deep-dive appendices"
description: ".NET-only reference: the pinned .NET 10 library and platform bill of materials, a Windows-to-Kubernetes migration table, an honest list of ecosystem gaps, and a six-library recipe for a new cloud-native service."
duration: 18 minutes
---

> **This appendix is .NET-specific.** It exists only in the .NET edition of the source
> material; the Spring Boot, Quarkus, Python, and C++ editions skip it. Every other
> chapter in this book is multi-language — this one is the reference a team moving from
> Windows and .NET Framework keeps open in another window while they build.

This is the reference appendix: a consolidated bill of materials for the application
side, the same for the platform side, an expanded migration table with a one-line
rationale per row, a candid look at what .NET genuinely lacks, and a short recipe to
start a new service. It is built for the .NET-developers-moving-from-Windows audience,
and its through-line is that the library choices and the platform choices are entirely
separable — the cluster does not know or care that the Pods happen to run .NET.

## The pinned .NET 10 toolkit

Every library that appears anywhere in the .NET edition, grouped by concern. The license
column is the one to read closely: every entry is MIT, Apache 2.0, or BSD — no
commercial-only dependencies, and nothing that requires Azure or any other specific
cloud.

| Concern | Library | Purpose | License | NuGet |
|---|---|---|---|---|
| Runtime | .NET 10 | LTS through Nov 2028; cross-platform | MIT | (built in) |
| Hosting | ASP.NET Core 10 | Web host, minimal APIs, controllers, DI, config | MIT | (built in) |
| REST | Microsoft.AspNetCore.OpenApi | OpenAPI 3 spec generation from endpoints | MIT | Microsoft.AspNetCore.OpenApi |
| REST | FluentValidation | Expressive request validation | Apache 2.0 | FluentValidation |
| Versioning | Asp.Versioning | Media-type / header / URI versioning | Apache 2.0 | Asp.Versioning.Http |
| gRPC | Grpc.AspNetCore | Server + Grpc.Tools build-time codegen | Apache 2.0 | Grpc.AspNetCore |
| gRPC | Grpc.StatusProto | google.rpc.Status rich errors (ToRpcException) | Apache 2.0 | Grpc.StatusProto |
| GraphQL | HotChocolate | Code-first server, DataLoader, federation | MIT | HotChocolate.AspNetCore |
| Data · ORM | Entity Framework Core | Full-fat ORM; LINQ; migrations | MIT | Microsoft.EntityFrameworkCore |
| Data · micro | Dapper | Lightweight micro-ORM | Apache 2.0 | Dapper |
| Event store | Marten | Document + event sourcing on Postgres | MIT | Marten |
| Messaging | MassTransit | Bus abstraction, sagas, retries, outbox, RoutingSlip | Apache 2.0 | MassTransit |
| Messaging | Confluent.Kafka | Low-level Kafka client | Apache 2.0 | Confluent.Kafka |
| Streaming | Streamiz.Kafka.Net | .NET port of Kafka Streams | MIT | Streamiz.Kafka.Net |
| Workflow | Temporalio.Temporal | Temporal .NET SDK — durable execution | Apache 2.0 | Temporalio.Temporal |
| Workflow | Stateless | In-process state machine library | Apache 2.0 | Stateless |
| Rules | NRules | Rete-algorithm rules engine | MIT | NRules.Fluent |
| Rules · DSL | NRules.Language | External DSL for non-developer rule editing | MIT | NRules.Language |
| WebSockets | Microsoft.AspNetCore.SignalR | Hub abstraction; auto-reconnect; MessagePack | Apache 2.0 | (built in) |
| WebSockets | SignalR.StackExchangeRedis | Open-source Redis backplane (not Azure SignalR Service) | Apache 2.0 | Microsoft.AspNetCore.SignalR.StackExchangeRedis |
| UI · server | Blazor Server | BFF + WebSocket UI; SignalR-based | MIT | (built in) |
| UI · client | Blazor WebAssembly | .NET in the browser; static-file hosted | MIT | (built in) |
| Resilience | Polly + M.E.Resilience | Retry, circuit breaker, hedging, timeout, bulkhead | BSD-3 / MIT | Microsoft.Extensions.Resilience |
| Health | AspNetCore.HealthChecks | Postgres / Redis / Kafka / SQL Server probes (community) | MIT | AspNetCore.HealthChecks.* |
| Observability | OpenTelemetry .NET | Tracing, metrics, logs; ActivitySource is in the BCL | Apache 2.0 | OpenTelemetry.Extensions.Hosting |
| Reverse proxy | YARP | In-app reverse proxy / gateway library | MIT | Yarp.ReverseProxy |
| Mediator | Wolverine | Command / handler dispatch (MediatR OSS heir) | MIT | WolverineFx |
| Scheduling | Quartz.NET | Cron / cluster-aware job scheduling | Apache 2.0 | Quartz |
| Scheduling | DistributedLock | Distributed mutex over Postgres / Redis / SQL Server | MIT | DistributedLock.* |

A few choices are worth calling out. `Microsoft.AspNetCore.OpenApi` and SignalR are built
into ASP.NET Core 10 — no extra package. **MassTransit** is the open-source heir to BizTalk
and NServiceBus, giving one programming model across Kafka, RabbitMQ, and Azure Service Bus.
**Streamiz.Kafka.Net** is a .NET port of Kafka Streams, which means windowed aggregations
without standing up a Flink cluster. **Temporalio.Temporal** pairs with the Temporal Server
in the platform stack for durable workflows; **Stateless** fills the lightweight in-process
state-machine slot; **NRules** is the Rete rules engine (a .NET-only library — it has no JVM
or C++ equivalent). And **Wolverine** is the modern OSS mediator to reach for now that
MediatR has moved to a commercial license.

## The pinned cloud-native platform stack

The other half of the bill of materials: the cluster-side components the Pods talk *to*.
None of them know the workload is .NET — the same stack serves Spring Boot, Quarkus, or
Python identically, which is the entire point. If you already run this platform under a
Java or Python application, .NET services drop in alongside without changing anything below
the application layer.

| Concern | Component | Purpose | License |
|---|---|---|---|
| Container orchestration | Kubernetes | Pods, Services, Deployments, ConfigMaps, Secrets | Apache 2.0 |
| Service mesh | Istio / Linkerd | mTLS, retries, traffic shaping, observability | Apache 2.0 |
| Autoscaling | KEDA | Event- and lag-driven scaling (incl. scale to zero) | Apache 2.0 |
| Messaging | Apache Kafka / Strimzi | Distributed log + Kubernetes-native operator | Apache 2.0 |
| Schema registry | Apicurio Registry | OpenAPI / .proto / Avro / JSON Schema, versioned | Apache 2.0 |
| Data catalog / lineage | OpenMetadata | Asset catalog, lineage, SLOs, ownership | Apache 2.0 |
| Tracing backend | Grafana Tempo | Trace storage + query, OTLP ingest | AGPL-3.0 |
| Metrics backend | Grafana Mimir / Prometheus | Long-term metrics, OTLP + Prom remote-write | AGPL / Apache |
| Logs backend | Grafana Loki | Label-indexed log store, low cardinality cost | AGPL-3.0 |
| Dashboards / alerts | Grafana | Unified panel for traces, metrics, logs | AGPL-3.0 |
| CDC | Debezium | Postgres / SQL Server WAL tailing → Kafka | Apache 2.0 |
| Relational DB | PostgreSQL | Primary OLTP store; CDC source | PostgreSQL |
| Key-value / cache | Redis (or Valkey) | SignalR backplane, distributed locks, caching | BSD-3 / BSD |
| Workflow server | Temporal Server | Durable-execution server (paired with .NET SDK) | MIT |
| Secrets | Kubernetes Secrets + external-secrets-operator | Secrets sync from your vault of choice | Apache 2.0 |
| Observability pipeline | OpenTelemetry Collector | OTLP ingest, processing, fan-out | Apache 2.0 |

The one license nuance to flag for your own legal review: the Grafana **LGTM** stack
(Tempo, Mimir, Loki, Grafana) is AGPL-3.0, which some organisations treat differently from
Apache/MIT. Everything else here is permissive. The bottom line is a standard CNCF-friendly
stack on which .NET 10 is simply one workload type.

## From Windows / .NET 4.x to Kubernetes / .NET 10

This is the expanded version of the bridge from the Cloud-Native Principles chapter —
twenty-two rows, four columns. Read the rightmost column, "what changes most," because that
is where the architectural shift actually lives. Almost every row preserves the *shape* of
the pattern: you still have request handlers, background workers, scheduled jobs,
distributed locks, health checks, configuration sources, and telemetry. What changes is who
owns the substrate — IIS owned the host, Kubernetes does now; the substrate becomes
open-source and cluster-native.

{% include excalidraw.html
   file="23-strangler-fig"
   alt="The strangler-fig migration approach. Clients hit one URL through a proxy routing layer — step zero is adding the proxy first. The proxy sends a widening 1% to 100% slice of traffic to a new service (the extracted slice) while everything else defaults to the shrinking monolith. Identify, move, redirect one bounded asset at a time, with the system live throughout; redirect is a proxy config change, not a client release, so every step is reversible."
   caption="Figure J.1 — Migrate incrementally with a strangler-fig proxy: redirect a widening slice to the new service while the monolith shrinks, system live throughout" %}

| Concern | Coming from (Windows / .NET 4.x) | Going to (.NET 10 / Kubernetes) | What changes most |
|---|---|---|---|
| Hosting | IIS app pool, web.config | ASP.NET Core 10 in container; appsettings.json + ConfigMap | Process is now stateless; cluster injects config; image is the unit |
| Lifecycle | App pool recycle on memory threshold | Kubernetes rolling deploy + graceful shutdown | SIGTERM is your shutdown signal; HostOptions.ShutdownTimeout is your budget |
| Service shape | WCF [ServiceContract] / [OperationContract] | ASP.NET Core minimal API, Grpc.AspNetCore service, HotChocolate type | Pick the protocol per call site, not per binding |
| Contracts | DataContract / .svc / WSDL | Microsoft.AspNetCore.OpenApi; Grpc.Tools; HotChocolate SDL | Contracts live in Apicurio; consumers code against the contract |
| Wire | NetTcpBinding (binary), BasicHttpBinding (SOAP) | gRPC over HTTP/2 (binary); REST / JSON | Binary on internal paths; REST at the edge |
| Distributed txn | COM+ / MSDTC two-phase commit | Saga + outbox (EF Core + Debezium / MassTransit outbox) | No two-phase commit across services; compensation replaces rollback |
| Messaging | MSMQ, SQL Server Service Broker | Apache Kafka (Strimzi) + MassTransit | Replayable log + consumer groups + dead-letter routing |
| Background work | Windows Service hosting a queue listener | BackgroundService in a Pod, scaled by KEDA | Long-running concerns ride the same Pod lifecycle as your web host |
| Scheduled work | Windows Scheduled Tasks | Kubernetes CronJob / KEDA Cron / Quartz.NET | Pick by scope: cluster-wide → CronJob; in-app → Quartz.NET |
| Config | web.config + Web.Release.config xforms | appsettings.json + env vars + ConfigMap | Config flows via the platform; the image never embeds env |
| Auth | Windows Auth, AD, NTLM, Kerberos | OIDC + mTLS via Istio + SPIFFE | Identity is workload-bound, not machine-bound |
| Telemetry | Windows Perf Counters + ETW + Event Log | OpenTelemetry .NET → OTLP → Tempo / Mimir / Loki | One model for traces, metrics, logs across all languages |
| Logs | log4net, NLog, EventLog | Microsoft.Extensions.Logging + Serilog → Loki | Structured JSON; never the local filesystem |
| Caching | ASP.NET Cache, AppFabric | Redis (open source) via StackExchange.Redis | Distributed cache lives outside the Pod |
| Sessions | ASP.NET Session State | Stateless services + Redis (or no sessions, use JWT) | 12-factor disposability; do not pin users to Pods |
| .NET Remoting | Remoting, MarshalByRefObject | gRPC over HTTP/2 / HTTP API | Wire boundary is explicit; serialization is contractual |
| Distributed transactions UI | BizTalk orchestration | Temporal .NET workflows / Stateless (lightweight) | Orchestration is plain C#; the engine handles durability |
| Routing logic | BizTalk pipelines + content-based routing | MassTransit RoutingSlip + NRules | EIP patterns in code; rules in their own .csproj |
| UI · LOB | ASP.NET Web Forms / MVC + jQuery | Blazor Server (SignalR) or Blazor WebAssembly (browser .NET) | Same C# both sides of the wire; no Azure required |
| Reverse proxy | ARR (IIS Application Request Routing) | YARP (in-app) / Istio Gateway (mesh edge) | Code-level routing or declarative platform routing |
| Resilience | Hand-coded try/retry loops, Polly v6 standalone | M.E.Resilience pipelines (built on Polly) | Composable: retry + circuit breaker + timeout + hedging |
| Health probes | ASP.NET app warmup, monitoring agents | M.E.Diagnostics.HealthChecks → /healthz/live + ready | Kubernetes is the monitoring agent |

Only two rows are genuine conceptual rewrites rather than substrate swaps. **COM+ / MSDTC
distributed transactions become sagas** — you write compensations explicitly because there
is no two-phase commit across services. And **BizTalk orchestration becomes a Temporal
workflow or a MassTransit + NRules routing pipeline** — orchestration is now C# code in your
repository, not a separately-authored artifact in a separate runtime. Everything else is the
platform owning more and your code owning less.

## What the .NET cloud-native story genuinely lacks

Every ecosystem has gaps; pretending .NET does not would erode trust. These are real, and
in each case there is a workable .NET path, a polyglot path, or a commercial path.

- **No native DMN runtime.** .NET ships no open-source DMN (Decision Model and Notation)
  engine. If you need spreadsheet-style decision tables authored by non-developers, run
  Camunda or Kogito DMN as a separate service and call it over REST from the enrichment
  step. NRules covers the rule-*engine* slot but not the DMN authoring experience.
- **No Apache Camel-scale connector ecosystem.** Nothing in .NET matches Camel's 300-plus
  component connectors. MassTransit's RoutingSlip covers the EIP patterns well, but for
  long-tail integration — HL7 over MLLP, AS2, EDI, mainframe gateways — you may still run a
  Camel sidecar in a JVM Pod, or accept a commercial option like Boomi or MuleSoft if open
  source is not a hard constraint.
- **Thinner stream processing.** Streamiz.Kafka.Net is excellent but is a smaller project
  than Kafka Streams. If stream processing is central, Flink remains the heavyweight option,
  typically as a separate JVM service.
- **Deliberately simple DI.** Microsoft.Extensions.DependencyInjection is intentionally
  minimal. For property injection, decorators, or advanced lifetime scopes, Autofac or
  Lamar are drop-in replacements.
- **MediatR is no longer open source.** It moved to a commercial license, and Wolverine is
  the modern MIT-licensed equivalent — arguably a better design — for new projects.

The honest summary: the .NET cloud-native story is solid for well over 95% of line-of-business
and SaaS workloads. The remaining few percent — integration platforms with heavy mainframe,
EDI, or HL7 needs, or central heavy stream processing — is where you mix runtimes or accept a
different trade-off.

## The five-line recipe for a new service

The steps are deliberately ordered — instrument first, then choose a protocol surface, then
settle data ownership, then pick a workflow tier, then let the cluster do the heavy lifting:

1. **Instrument from line one.** `dotnet new web`; add `Microsoft.AspNetCore.OpenApi`,
   `AspNetCore.HealthChecks.NpgSql`, and `OpenTelemetry.Extensions.Hosting`. Map health
   checks at `/healthz/live` and `/healthz/ready`; expose `ActivitySource`-based telemetry
   immediately.
2. **Pick exactly the protocols you need.** Minimal APIs for REST at the edge,
   `Grpc.AspNetCore` for internal service-to-service, HotChocolate only if you genuinely
   need GraphQL aggregation. Do not surface all three by default.
3. **Settle data ownership.** EF Core for the OLTP store, with the outbox table in the same
   `DbContext` as your aggregates; Debezium to Kafka via Strimzi. Add MassTransit only when
   you actually need bus abstraction, or use `Confluent.Kafka` directly for tighter control.
4. **Choose a workflow tier.** Temporal .NET SDK when the saga is durable, long, or
   cross-service; Stateless when it is small and in-process. Persist *every* transition;
   never trust in-memory state to survive a Pod restart.
5. **Ship it on Kubernetes.** KEDA scaling on Kafka lag or HTTP RPS; Istio for mTLS and
   retries; OpenTelemetry exporting to LGTM. Use Asp.Versioning for media-type evolution
   rather than inventing your own scheme.

Six libraries get you most of the way: **ASP.NET Core, EF Core, MassTransit,
Temporalio.Temporal, OpenTelemetry, and Polly.** Add NRules, Streamiz, HotChocolate, or
SignalR per workload — only when the use case earns it.

### Cross-check it yourself

This appendix is reference material, so the check is that the recipe actually stands up.
Scaffold the six-library service and confirm the day-one wiring end to end: `dotnet new web`,
add the six packages, map `/healthz/live` and `/healthz/ready`, and start it. Hit both health
endpoints with curl and confirm `200`s with the expected probe payloads. Then issue one real
request and confirm a trace appears in Tempo — paste the trace id from the response (or the
log line) into Grafana and verify the span carries the service name and the
`ActivitySource`-based attributes. A new service that answers both probes and emits a
correlated trace on its first request has the spine of every pattern in this book working
before you have written any business logic.

---
*Verification status: unverified — the three tables were transcribed directly from the
source deck's rendered table images, so the rows match the deck, but several entries are
version- and license-sensitive and the sandbox is offline, so they were not re-checked
against upstream. Confirm online before publishing: (1) **MassTransit's license** — the deck
lists it as Apache 2.0 and the toolkit's "no commercial dependencies" claim depends on that;
if MassTransit has shifted to a commercial model it belongs in the honest-gaps section
alongside MediatR, and several migration rows would need a note. (2) MediatR's commercial
license and Wolverine as the OSS replacement. (3) The .NET 10 LTS support window (the deck
says through Nov 2028). (4) Exact NuGet package ids and current licenses for Temporalio,
Streamiz.Kafka.Net, Asp.Versioning, and Polly / Microsoft.Extensions.Resilience. There is no
per-language `examples/` runner for this appendix; the recipe's cross-check is the closest
thing to a runnable proof.*
