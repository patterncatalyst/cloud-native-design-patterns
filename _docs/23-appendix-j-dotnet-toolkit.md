---
title: ".NET 10 Toolkit & Migration Reference"
marker: "J"
label: "Appendix J"
order: 23
part: "Deep-dive appendices"
description: ".NET-only reference: the pinned .NET 10 library and platform bill of materials, a Windows-to-Kubernetes migration table, a list of ecosystem gaps, and a six-library recipe for a new cloud-native service."
duration: 18 minutes
---

> **This appendix is .NET-specific.** It exists only in the .NET edition of the source
> material; the Spring Boot, Quarkus, Python, and C++ editions skip it. Every other
> chapter in this book is multi-language: this one is the reference a team moving from
> Windows and .NET Framework keeps open in another window while they build.

This is the reference appendix: a consolidated bill of materials for the application
side, the same for the platform side, an expanded migration table with a one-line
rationale per row, a look at what .NET lacks, and a short recipe to
start a new service. It is built for the .NET-developers-moving-from-Windows audience,
and its through-line is that the library choices and the platform choices are entirely
separable: the cluster does not know or care that the Pods happen to run .NET.

## The pinned .NET 10 toolkit

Every library that appears anywhere in the .NET edition, grouped by concern. The license
column is the one to read closely: every entry is MIT, Apache 2.0, BSD or (for Redis) the AGPLv3 option, no
commercial-only dependencies, and nothing that requires a specific cloud.

| Concern | Library | Purpose | License | NuGet |
|---|---|---|---|---|
| Runtime | .NET 10 (10.0.12) | LTS through Nov 2028; cross-platform | MIT | (built in) |
| Hosting | ASP.NET Core 10 | Web host, minimal APIs, controllers, DI, config | MIT | (built in) |
| REST | Microsoft.AspNetCore.OpenApi | OpenAPI 3 spec generation from endpoints | MIT | Microsoft.AspNetCore.OpenApi |
| REST | FluentValidation | Expressive request validation | Apache 2.0 | FluentValidation |
| Versioning | Asp.Versioning | Media-type / header / URI versioning | MIT | Asp.Versioning.Http |
| gRPC | Grpc.AspNetCore | Server + Grpc.Tools build-time codegen | Apache 2.0 | Grpc.AspNetCore |
| gRPC | Grpc.StatusProto | google.rpc.Status rich errors (ToRpcException) | Apache 2.0 | Grpc.StatusProto |
| GraphQL | HotChocolate | Code-first server, DataLoader, federation | MIT | HotChocolate.AspNetCore |
| Data · ORM | Entity Framework Core | Full-fat ORM; LINQ; migrations | MIT | Microsoft.EntityFrameworkCore |
| Data · micro | Dapper | Lightweight micro-ORM | Apache 2.0 | Dapper |
| Event store | Marten | Document + event sourcing on Postgres | MIT | Marten |
| Messaging | Confluent.Kafka 2.16.0 | Kafka client: producers, consumer groups, explicit offset commits | Apache 2.0 | Confluent.Kafka |
| Streaming | Streamiz.Kafka.Net 1.8.2 | .NET port of Kafka Streams | MIT | Streamiz.Kafka.Net |
| Workflow | Temporalio | Temporal .NET SDK: durable execution | MIT | Temporalio |
| Workflow | Stateless | In-process state machine library | Apache 2.0 | Stateless |
| Rules | NRules | Rete-algorithm rules engine | MIT | NRules.Fluent |
| Rules · DSL | NRules.Language | External DSL for non-developer rule editing | MIT | NRules.Language |
| WebSockets | Microsoft.AspNetCore.SignalR | Hub abstraction; auto-reconnect; MessagePack | MIT | (built in) |
| WebSockets | SignalR.StackExchangeRedis | Open-source Redis backplane (no managed SignalR service) | MIT | Microsoft.AspNetCore.SignalR.StackExchangeRedis |
| UI · server | Blazor Server | BFF + WebSocket UI; SignalR-based | MIT | (built in) |
| UI · client | Blazor WebAssembly | .NET in the browser; static-file hosted | MIT | (built in) |
| Resilience | Polly + M.E.Resilience | Retry, circuit breaker, hedging, timeout, bulkhead | BSD-3 / MIT | Microsoft.Extensions.Resilience |
| Health | AspNetCore.HealthChecks | Postgres / Redis / Kafka / SQL Server probes (community) | Apache 2.0 | AspNetCore.HealthChecks.* |
| Observability | OpenTelemetry .NET | Tracing, metrics, logs; ActivitySource is in the BCL | Apache 2.0 | OpenTelemetry.Extensions.Hosting |
| Reverse proxy | YARP | In-app reverse proxy / gateway library | MIT | Yarp.ReverseProxy |
| Mediator | Wolverine | Command / handler dispatch (MediatR OSS heir) | MIT | WolverineFx |
| Scheduling | Quartz.NET | Cron / cluster-aware job scheduling | Apache 2.0 | Quartz |
| Scheduling | DistributedLock | Distributed mutex over Postgres / Redis / SQL Server | MIT | DistributedLock.* |

`Microsoft.AspNetCore.OpenApi` and SignalR are built
into ASP.NET Core 10, no extra package. **Confluent.Kafka** is the Kafka client the examples use directly: a bus abstraction such as MassTransit would hide the consumer-group, offset-commit, and partition semantics the chapters teach, and MassTransit v9 moved to a commercial license.
**Streamiz.Kafka.Net** is a .NET port of Kafka Streams, which means windowed aggregations
without standing up a Flink cluster. **Temporalio** (the Temporal .NET SDK) pairs with the Temporal Server
in the platform stack for durable workflows; **Stateless** fills the lightweight in-process
state-machine slot; **NRules** is the Rete rules engine (a .NET-only library with no JVM
or C++ equivalent). And **Wolverine** is the modern OSS mediator to reach for now that
MediatR has moved to a commercial license.

## The pinned cloud-native platform stack

The other half of the bill of materials: the cluster-side components the Pods talk *to*.
None of them know the workload is .NET: the same stack serves Spring Boot, Quarkus, or
Python identically, which is the entire point. If you already run this platform under a
Java or Python application, .NET services drop in alongside without changing anything under
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
| Key-value / cache | Redis 8 (or Valkey) | SignalR backplane, distributed locks, caching | Redis 8: RSALv2 / SSPLv1 / AGPLv3, the examples take AGPLv3; Valkey: BSD-3 |
| Workflow server | Temporal Server | Durable-execution server (paired with .NET SDK) | MIT |
| Secrets | Kubernetes Secrets + external-secrets-operator | Secrets sync from your vault of choice | Apache 2.0 |
| Observability pipeline | OpenTelemetry Collector | OTLP ingest, processing, fan-out | Apache 2.0 |

The one license nuance to flag for your own legal review: the Grafana **LGTM** stack
(Tempo, Mimir, Loki, Grafana) is AGPL-3.0, and so is Redis 8 under the option the examples
use (`redis:8.10.2-alpine`; RSALv2 and SSPLv1 are the other two choices and neither is open
source). Some organisations treat AGPL differently from Apache/MIT; where that rules Redis
out, Valkey (BSD-3, a Linux Foundation project forked from Redis 7.2) speaks the same
protocol and works with StackExchange.Redis unchanged. Everything else here is permissive. The bottom line is a standard CNCF-friendly
stack on which .NET 10 is one workload type.

## From Windows / .NET 4.x to Kubernetes / .NET 10

This is the expanded version of the bridge from the Cloud-Native Principles chapter:
twenty-two rows, four columns. Read the rightmost column, "what changes most," because that
is where the architectural shift lives. Almost every row preserves the *shape* of
the pattern: you still have request handlers, background workers, scheduled jobs,
distributed locks, health checks, configuration sources, and telemetry. What changes is who
owns the substrate: IIS owned the host, Kubernetes does now; the substrate becomes
open-source and cluster-native.

{% include excalidraw.html
   file="23-strangler-fig"
   alt="The strangler-fig migration approach. Clients hit one URL through a proxy routing layer: step zero is adding the proxy first. The proxy sends a widening 1% to 100% slice of traffic to a new service (the extracted slice) while everything else defaults to the shrinking monolith. Identify, move, redirect one bounded asset at a time, with the system live throughout; redirect is a proxy config change, not a client release, so every step is reversible."
   caption="Figure J.1: Migrate incrementally with a strangler-fig proxy: redirect a widening slice to the new service while the monolith shrinks, system live throughout" %}

| Concern | Coming from (Windows / .NET 4.x) | Going to (.NET 10 / Kubernetes) | What changes most |
|---|---|---|---|
| Hosting | IIS app pool, web.config | ASP.NET Core 10 in container; appsettings.json + ConfigMap | Process is now stateless; cluster injects config; image is the unit |
| Lifecycle | App pool recycle on memory threshold | Kubernetes rolling deploy + graceful shutdown | SIGTERM is your shutdown signal; HostOptions.ShutdownTimeout is your budget |
| Service shape | WCF [ServiceContract] / [OperationContract] | ASP.NET Core minimal API, Grpc.AspNetCore service, HotChocolate type | Pick the protocol per call site, not per binding |
| Contracts | DataContract / .svc / WSDL | Microsoft.AspNetCore.OpenApi; Grpc.Tools; HotChocolate SDL | Contracts live in Apicurio; consumers code against the contract |
| Wire | NetTcpBinding (binary), BasicHttpBinding (SOAP) | gRPC over HTTP/2 (binary); REST / JSON | Binary on internal paths; REST at the edge |
| Distributed txn | COM+ / MSDTC two-phase commit | Saga + outbox (EF Core + Debezium) | No two-phase commit across services; compensation replaces rollback |
| Messaging | MSMQ, SQL Server Service Broker | Apache Kafka (Strimzi) + Confluent.Kafka | Replayable log + consumer groups + dead-letter routing |
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
| Routing logic | BizTalk pipelines + content-based routing | NRules + Confluent.Kafka producers | EIP patterns in code; rules in their own .csproj |
| UI · LOB | ASP.NET Web Forms / MVC + jQuery | Blazor Server (SignalR) or Blazor WebAssembly (browser .NET) | Same C# both sides of the wire; no managed cloud service required |
| Reverse proxy | ARR (IIS Application Request Routing) | YARP (in-app) / Istio Gateway (mesh edge) | Code-level routing or declarative platform routing |
| Resilience | Hand-coded try/retry loops, Polly v6 standalone | M.E.Resilience pipelines (built on Polly) | Composable: retry + circuit breaker + timeout + hedging |
| Health probes | ASP.NET app warmup, monitoring agents | M.E.Diagnostics.HealthChecks → /healthz/live + ready | Kubernetes is the monitoring agent |

Only two rows are conceptual rewrites rather than substrate swaps. **COM+ / MSDTC
distributed transactions become sagas**: you write compensations explicitly because there
is no two-phase commit across services. And **BizTalk orchestration becomes a Temporal
workflow or an NRules routing pipeline**: orchestration is now C# code in your
repository, not a separately-authored artifact in a separate runtime. Everything else is the
platform owning more and your code owning less.

## What the .NET cloud-native story lacks

Every ecosystem has gaps; pretending .NET does not would erode trust. These are real, and
in each case there is a workable .NET path or an open-source polyglot path.

- **No native DMN runtime.** .NET ships no open-source DMN (Decision Model and Notation)
  engine. If you need spreadsheet-style decision tables authored by non-developers, run
  the Apache KIE DMN engine (Kogito, Apache 2.0) as a separate service and call it over REST
  from the enrichment step. NRules covers the rule-*engine* slot but not the DMN authoring experience.
- **No Apache Camel-scale connector ecosystem.** Nothing in .NET matches Camel's 300-plus
  component connectors. Routing code over plain Kafka producers covers the EIP patterns well, but for
  long-tail integration (HL7 over MLLP, AS2, EDI, mainframe gateways), you may still run a
  Camel sidecar in a JVM Pod (Apache Camel, Apache 2.0) next to the .NET services.
- **Thinner stream processing.** Streamiz.Kafka.Net is excellent but is a smaller project
  than Kafka Streams. If stream processing is central, Flink remains the heavyweight option,
  typically as a separate JVM service.
- **Minimal built-in DI.** Microsoft.Extensions.DependencyInjection covers constructor
  injection only. For property injection, decorators, or advanced lifetime scopes, Autofac
  or Lamar are drop-in replacements.
- **MassTransit v9 is commercial.** The previously open-source service bus moved to a
  commercial license, so this book uses Confluent.Kafka directly for Kafka messaging and
  Wolverine (MIT) where a framework bus is wanted.
- **MediatR is no longer open source.** It moved to a commercial license, and Wolverine is
  the modern MIT-licensed equivalent, and a better design, for new projects.

The .NET cloud-native story is solid for well over 95% of line-of-business
and SaaS workloads. The remaining few percent (integration platforms with heavy mainframe,
EDI, or HL7 needs, or central heavy stream processing) is where you mix runtimes or accept a
different trade-off.

## The five-line recipe for a new service

The order matters: instrument first, then choose a protocol surface, then
settle data ownership, then pick a workflow tier, then let the cluster do the heavy lifting:

1. **Instrument from line one.** `dotnet new web`; add `Microsoft.AspNetCore.OpenApi`,
   `AspNetCore.HealthChecks.NpgSql`, and `OpenTelemetry.Extensions.Hosting`. Map health
   checks at `/healthz/live` and `/healthz/ready`; expose `ActivitySource`-based telemetry
   immediately.
2. **Pick exactly the protocols you need.** Minimal APIs for REST at the edge,
   `Grpc.AspNetCore` for internal service-to-service, HotChocolate only if you
   need GraphQL aggregation. Do not surface all three by default.
3. **Settle data ownership.** EF Core for the OLTP store, with the outbox table in the same
   `DbContext` as your aggregates; Debezium to Kafka via Strimzi. Add a bus framework only when
   you need bus abstraction, or use `Confluent.Kafka` directly for tighter control.
4. **Choose a workflow tier.** Temporal .NET SDK when the saga is durable, long, or
   cross-service; Stateless when it is small and in-process. Persist *every* transition;
   never trust in-memory state to survive a Pod restart.
5. **Ship it on Kubernetes.** KEDA scaling on Kafka lag or HTTP RPS; Istio for mTLS and
   retries; OpenTelemetry exporting to LGTM. Use Asp.Versioning for media-type evolution
   rather than inventing your own scheme.

Six libraries get you most of the way: **ASP.NET Core, EF Core, Confluent.Kafka,
Temporalio, OpenTelemetry, and Polly.** Add NRules, Streamiz, HotChocolate, or
SignalR per workload, only when the use case earns it.

### Cross-check it yourself

This appendix is reference material, so the check is that the recipe stands up.
Scaffold the six-library service and confirm the day-one wiring end to end: `dotnet new web`,
add the six packages, map `/healthz/live` and `/healthz/ready`, and start it. Hit both health
endpoints with curl and confirm `200`s with the expected probe payloads. Then issue one real
request and confirm a trace appears in Tempo: paste the trace id from the response (or the
log line) into Grafana and verify the span carries the service name and the
`ActivitySource`-based attributes. A new service that answers both probes and emits a
correlated trace on its first request has the spine of every pattern in this book working
before you have written any business logic.

---
*Verification status: package versions and licenses were checked against nuget.org on
2026-10-10 (Confluent.Kafka 2.16.0, Apache-2.0; Streamiz.Kafka.Net 1.8.2, MIT; Temporalio,
Asp.Versioning and Microsoft.Extensions.Resilience, MIT; Polly 8, BSD-3-Clause). MassTransit
v9 and MediatR are commercially licensed, which is why the examples use Confluent.Kafka
directly and Wolverine is the OSS alternative. The three tables
were transcribed from the source deck, so the rows match the deck; the .NET 10 LTS support
window (through Nov 2028) follows Microsoft's published policy. There is no per-language
`examples/` runner for this appendix; the recipe's cross-check is the closest thing to a
runnable proof.*
