# Designing-Cloud-Native-APIs-DotNet

Source: Designing-Cloud-Native-APIs-DotNet.pptx · 312 slides

## [001] CLOUD-NATIVE ARCHITECTURE · Designing Cloud-Native APIs (sldId 256)

From principles to a running system on Kubernetes — communication, composition, data, events, and the platform that governs them.

Robert Sedor

Chief Architect, Application Development

> Welcome and framing. This is a working architect's tour of designing cloud-native APIs on .NET 10 — not a survey of buzzwords. The audience: .NET developers who lived on .NET Framework 4.x, IIS, WCF and COM+ and now need to ship on Kubernetes. We'll bridge that world to this one at every step, not pretend the old world didn't exist. Set expectations: we build one realistic system (five services and a gateway) and re-examine it from twelve angles, then deep-dive appendices on protocol internals, versioning, WebSockets (including Blazor's place in this story), and saga mechanics. Mention the running stack up front: .NET 10 (LTS through 2028, MIT) with ASP.NET Core for REST, Grpc.AspNetCore for gRPC, HotChocolate for GraphQL, Confluent.Kafka 2.16.0 for events, Streamiz.Kafka.Net 1.8.2 for stream processing, Temporal .NET SDK for durable workflows (Stateless for the lightweight alternative), SignalR for WebSockets, OpenTelemetry .NET for observability — every library MIT or Apache 2.0. On Kubernetes with Kafka (Strimzi), Istio and KEDA. The platform around the code (Strimzi, Apicurio, OpenMetadata, the LGTM stack) is the same for every language; .NET 10 is how we write the services.

## [002] AGENDA · Agenda (sldId 257)

- Setting up · Patterns in the age of AI
- 01 · Cloud-Native Principles
- 02 · Communications
- 03 · Composition
- 04 · Data
- 05 · Event-Driven
- 06 · Stream Processing
- 07 · Workflows & Jobs
- 08 · API Management
- 09 · API Registry
- 10 · API Metadata
- 11 · Observability
- 12 · Security
- 13 · Anti-Patterns
- Appendices A–D · Protocols, Versioning, WebSockets, Sagas
- Appendices E–I · Errors, DDD, Coupling, Shutdown, L7 Routing
- Appendices J–L · .NET 10 Toolkit, Monolith → Microservices, Caching
- Appendices M–O · Failure modes, Feature Flags, API Testing
- Appendices P–R · .NET on Linux, Blazor, minikube
- Glossary of acronyms

p. 1

> The agenda: a short setup, thirteen sections, and the deep-dive appendices. The setup motivates why patterns matter in the age of AI. Sections 1 to 6 build the system from principles up through data and streaming; sections 7 to 13 cover the operational platform around it (workflows, management, registry, metadata, observability), then security, and close on anti-patterns.
>
> The appendices are reference material for the questions that come up: protocols, versioning, WebSockets, sagas, errors, DDD, coupling, shutdown, L7 routing, monolith-to-microservices decomposition, caching, failure modes, feature flags and API testing, plus the .NET toolkit, .NET on Linux and Blazor Server. Appendix R runs Example 05 on minikube with the same verify.sh as compose. A glossary of acronyms closes the deck.
>
> Tell the audience which sections you will cover given the session length. The overview that follows reframes the agenda as the narrative arc: what we build and in what order.

## [003] OVERVIEW · What we'll build, and the order we'll build it (sldId 258)

- Foundations — cloud-native principles and the canonical system we carry throughout
- Communications — REST, gRPC, GraphQL, and synchronous vs. asynchronous
- Composition & Data — gateways, federation, database-per-service, outbox, sagas
- Event-driven & Stream processing — the log, schemas, derived streams, KEDA scaling
- Workflows & Jobs — orchestration, choreography, batch and scheduled work
- The API platform — gateway, registry (Apicurio), metadata (OpenMetadata), observability
- Anti-patterns — and the heuristics that keep you out of them

p. 2

> Walk the arc quickly; don't dwell. The order follows dependency: principles first because they justify every later choice, then the synchronous surface (comms, composition), then data ownership, then the asynchronous backbone (events, streams), then the operational concerns (workflows, the platform planes), and finally anti-patterns as a reflective close. Tell people the deep-dive appendices A to R (protocols, versioning, WebSockets, sagas, errors, caching, failure modes, feature flags, API testing, minikube) are there to jump to. For a 90-minute talk, cover the main twelve; for the full three hours, work through the appendices too.

## [004] SETTING UP · Why patterns matter more in the age of AI (sldId 259)

- AI tooling (Claude, Claude Code, frontier models) turns intent into code at a rate that was not possible before. The bottleneck shifted: it's no longer typing, it's knowing what to ask for and what to accept.
- Patterns are your vocabulary at three layers: design patterns (factory, strategy, observer), architecture patterns (hexagonal, microservices, event-driven), system design patterns (sagas, caching, strangler fig — the scope of this deck).
- Without that vocabulary you can't specify precisely, can't evaluate what comes back, can't tell good code from plausible-looking code, or notice when an anti-pattern is dressed as a solution. The AI is fluent; you still need to be literate.
- All architecture is the least-worst decision — every choice trades something away.
- All management is risk management — you manage the distribution of failures, not their existence.
- There is no such thing as a free lunch — every pattern has a cost; ask whether you can afford it.
- There is no problem which cannot be made worse — the wrong fix amplifies the original pain.

p. 3

> Open the deck by naming the elephant. AI coding tools (Claude, Claude Code, Cursor, Copilot, every frontier model) are now in production engineering workflows. They produce code fluently. From a one-sentence prompt they will produce a microservices decomposition, a saga, a cache layer, a strangler fig wrapper, a CQRS write side: plausible enough to compile, deploy and run. The risk is also new: a developer who doesn't have the vocabulary to evaluate what comes back is rolling dice in production. The patterns in this deck are not nostalgic computer-science trivia; they are the literacy that lets you direct AI tooling instead of being directed by it. Walk the three layers of patterns briefly: design patterns are code-level vocabulary (Gang of Four); architecture patterns describe how applications fit together (hexagonal, microservices, BFF, event-driven); system design patterns, the focus of this deck, span services, data and runtime (sagas, caching, the strangler fig, outbox, decomposition, L7 routing). The four maxims are the philosophical spine. ‘Least-worst decision’: every architecture choice is a set of trades (latency for throughput, consistency for availability, simplicity for flexibility), and the job is not to find the optionless option but to make the trades visible and explicit. ‘Risk management’: you manage the distribution of failures, not their existence. ‘No free lunch’: every pattern (cache, saga, eventing, decomposition) has a cost — a stale read window, a compensation path, a coordination tax, an operational complexity. The question is whether you are buying the right thing for what you are paying. ‘No problem cannot be made worse’ is the warning corollary: a confidently-wrong intervention amplifies the original pain, and AI tooling makes confident interventions fast and cheap. The closing line is the audience take-home: AI is the amplifier; the patterns are the literacy that decides which direction it amplifies.

## [005] SETTING UP · Three layers of patterns literacy (sldId 260)

p. 4

> The visual companion to the three layers of patterns literacy. Three stacked boxes: design patterns at the bottom (Gang of Four: factory, strategy, observer, decorator, repository, etc.); architecture patterns in the middle (hexagonal, microservices, modular monolith, BFF, federation, pipes-and-filters, event-driven, layered); and at the top, system design patterns, the scope of this deck (sagas, caching, the strangler fig, outbox, event sourcing, CQRS, decomposition, back-pressure, bulkhead, L7 routing, rule-based dispatch). The arrows up the middle show how each lower layer informs the next: you can't reason about a saga (system layer) without knowing what a state machine and a compensation are (architecture / design layer); you can't reason about content-based routing without understanding the strategy pattern. The blue caption in the middle is the through-line: knowing this vocabulary is what lets you ask AI tooling for the right thing, recognise what it produces, and judge why it is or isn't fit. The four maxims at the bottom in red are the philosophical anchors for every section: each concrete choice in the deck is an exercise in those four principles. Make the audience comfortable with the maxims, especially the last one (no problem cannot be made worse) — it's the warning at the heart of using AI tooling well.

## [006] THE RUNNING EXAMPLE · One system, carried end to end (sldId 261)

We will design every concern against these five services and a gateway — the same example, re-examined from each angle.

p. 5

> This is the single most important slide to anchor on — every later example refers back to it. Walk each service: order-service owns the order lifecycle and exposes REST at the edge; inventory, payment and shipping are internal, reached by gRPC and contributing to GraphQL reads; notification-service is Kafka-only, consuming order.placed. The graphql-gateway composes reads across them. Emphasize that each service exposes only the protocols that fit its role — not a uniform surface. Promise the audience we'll return to this picture a dozen times.

## [007] Cloud-Native Principles (sldId 262)

01

Properties first, tools second.

> Transition into section one. The core message: cloud-native is not a stack you buy, it is a set of runtime properties your service must exhibit. Tools (Kubernetes, Istio, KEDA) exist to make those properties cheap to obtain — but if your service isn't written to lean on them, no platform can rescue it. Before the pillars themselves, one slide for the audience: a Rosetta-stone from the Windows world (IIS, WCF, COM+, MSMQ) to the Kubernetes world. Almost every pattern you knew has a direct cloud-native analog — the platform owns more, your code owns less.

## [008] CLOUD-NATIVE PRINCIPLES · From the Windows world to Kubernetes (sldId 263)

Almost every pattern you knew, from IIS and WCF to COM+ and MSMQ, maps onto a Kubernetes-native equivalent. Mostly a re-skin, not a rewrite of the concepts.

p. 6

> This slide is the orientation gift to the audience. Most of you spent years on .NET Framework 4.x, hosting in IIS, talking via WCF, doing distributed transactions with MSDTC and COM+, queuing with MSMQ or SQL Server Service Broker, and configuring everything through web.config. Cloud-native is a re-platforming of those patterns, not a rejection: Kubernetes owns the host and the messaging substrate, and your code owns less infrastructure plumbing. Walk the audience through 4-5 rows they'll recognise: app pool → Pod, app pool recycle → graceful shutdown + rolling deploy, WCF service → gRPC or ASP.NET Core, COM+ distributed transactions → saga + outbox (which we'll cover deeply in Appendix D), MSMQ → Kafka. The line under the table is the architectural shift to make explicit: you stop owning the host and start owning the code, because the platform now provides the host as a primitive. These six pillars are the rubric Kubernetes enforces on you when you make that switch.

## [009] CLOUD-NATIVE PRINCIPLES · Cloud-native is a set of runtime properties (sldId 264)

If your API isn't disposable, observable, resilient, elastic, automatable and loosely coupled, the platform can't help it.

p. 7

> Six pillars. Spend a sentence on each: disposable (12-factor, fast start, clean stop, no local state), observable (traces/metrics/logs, health probes), resilient (timeouts, retries, circuit breakers, graceful degradation), elastic (scale to load and to zero), automatable (declarative config, GitOps, self-healing), loosely coupled (contracts not calls, async where it fits). The pillars are the rubric for the whole talk: every design decision in it either earns or spends one of these properties. Tie back to the Windows-to-Kubernetes bridge: IIS gave you some of these (process recycle, health monitoring) but on a single Windows host; Kubernetes gives you all six, across many hosts, declaratively.

## [010] CLOUD-NATIVE PRINCIPLES · The platform makes the properties the default (sldId 265)

- Kubernetes gives you the disposable process model: liveness/readiness probes, rolling deploys, self-healing.
- KEDA (and the http-add-on) make elasticity real — scale on lag or RPS, all the way to zero.
- Istio supplies resilience and security at the wire: timeouts, retries, circuit breaking, mTLS.
- OpenTelemetry + Tempo / Mimir / Prometheus / Grafana / Kiali make every request observable.
- Your job is to write services that lean on these — not to reimplement them per service.

p. 8

> The punchline is the bold line: your job is to lean on the platform, not reimplement it. Concretely — don't write your own retry library when Istio does it at the wire; don't build a bespoke autoscaler when KEDA scales on lag and RPS; don't hand-roll metrics plumbing when OpenTelemetry plus the LGTM stack gives it to you. Every line of resilience code you write per service is a line you maintain forever and that drifts between teams. The platform makes the good behaviour the default.

## [011] CLOUD-NATIVE PRINCIPLES · Design-first: the contract precedes the code (sldId 266)

- Agree the interface before implementing it — OpenAPI for REST, .proto for gRPC, AsyncAPI for events.
- The contract is a versioned artifact in the registry, gated in CI, owned by the producing domain.
- Consumers code against the contract and generated stubs, never against your database or internals.
- This is what makes services independently deployable — the promise the contract encodes is the boundary.
  - Tooling: the dotnet CLI and NuGet (central package management via Directory.Packages.props) for reproducible builds; Microsoft.AspNetCore.OpenApi (or Swashbuckle) emits the OpenAPI spec; buf / protoc with Grpc.Tools for gRPC; HotChocolate exports the GraphQL SDL.

p. 9

> Design-first is the cultural prerequisite for everything that follows. The contract (OpenAPI, .proto, AsyncAPI) is agreed and registered before code is written, owned by the producing domain, and gated in CI. Consumers code against the contract and generated stubs, never against your database. Make the point that this is what delivers independent deployability: the promise the contract encodes is the service boundary. If you skip this, you get distributed coupling that's worse than a monolith because it fails over the network. In the .NET world the contract artifacts come naturally: Microsoft.AspNetCore.OpenApi (built into .NET 9+) emits the REST spec from your controller and minimal-API endpoints, Grpc.Tools compiles the .proto into both server bases and client stubs at build time, and HotChocolate generates the GraphQL SDL from your code-first types (or loads .graphql files if you prefer schema-first) — all checked into the registry.

## [012] CLOUD-NATIVE PRINCIPLES · The twelve-factor app, revisited (sldId 267)

- The twelve-factor app (2011) is the original recipe for software that's disposable, scalable and portable — the discipline beneath the runtime properties we just saw.
- It predates Kubernetes but maps onto it almost one-to-one: most factors are now things the platform provides, not code you write.
- So read the factors by ownership — a few you still author (config from the environment, statelessness, clean start/stop, logs as streams) and the rest the platform hands you (scaling, build/release/run, attached backing services).
- In a microservices, event-driven system they get richer: “backing services” means Postgres, Kafka and the schema registry as swappable URLs; “logs” becomes correlated traces, metrics and logs.
- Treat it as a pre-flight check: “will this survive the platform?” The twelve factors are listed and mapped to where each lives in our architecture.

p. 10

> Frame the twelve-factor app for the audience: it's the 2011 Heroku methodology that first codified what we now call cloud-native, and it's worth revisiting because it predates Kubernetes yet maps onto it almost perfectly. The key reframing here is ownership: don't recite the list; split it into the few factors you still write (config from the environment, stateless processes, fast clean startup and shutdown, logs as event streams) versus the many the platform now provides by default (build/release/run via images and GitOps, concurrency via KEDA, attached backing services). In a microservices/event-driven world several factors deepen: backing services now includes Kafka and the registry, and 'logs' has become full observability. End by teeing up the list and the mapping diagrams.

## [013] CLOUD-NATIVE PRINCIPLES · What the twelve factors are (sldId 268)

The original 2011 checklist — most are now platform concerns; only a few are yours to write.

p. 11

> A lot of people nod along to ‘twelve-factor’ without being able to name the twelve, so here they are at a glance, one line each. Don't read them aloud — let people scan. Two takeaways to say: first, this 2011 list predicted cloud-native a decade early; second, many factors are now handled by the platform (build/release/run, concurrency, disposability, port binding, backing services) versus the few you still actively write (config from the environment, statelessness, logs as streams). That sets up the map of each factor onto our architecture.

## [014] CLOUD-NATIVE PRINCIPLES · Twelve factors, mapped to our system (sldId 269)

Most factors are now platform defaults you adopt; a few are discipline you still write.

p. 12

> This is the payoff: not the traditional twelve-factor table, but a map of where each factor lives in the system we're building. Read it left to right: the twelve factors cluster into five things they ask of you, and each maps to a concrete piece of our stack and the section that covers it. Build & ship (codebase, dependencies, build/release/run, parity) becomes one repo, one image per release, the same image everywhere (§1). Configure becomes environment config (§1). Run on the platform (stateless processes, concurrency, disposability, port binding) becomes stateless pods, KEDA scaling, fast start/stop, and services behind Istio (§1, 2, 6). Attach resources becomes Postgres, Kafka and Apicurio as swappable URLs (§4–5). Operate (logs, admin processes) becomes OpenTelemetry into the LGTM stack and admin work as Jobs/CronJobs (§7, 11). The caption is the message: most of these are now defaults you adopt, not code you write — which is exactly what 'cloud-native' buys you.

## [015] CLOUD-NATIVE PRINCIPLES · A 12-factor ASP.NET Core service, ready for the platform (sldId 270)

[chip] csharp · .NET 10 + ASP.NET Core + EF Core health checks

```csharp
// Program.cs (excerpt), examples/01-cloud-native-principles/dotnet
builder.Services.AddDbContext<OrdersContext>(o => o.UseNpgsql(connString)); // factor III
builder.Services.AddHealthChecks()
    .AddDbContextCheck<OrdersContext>("database", tags: ["ready"]);  // readiness: can connect
var app = builder.Build();
app.MapHealthChecks("/healthz", new HealthCheckOptions               // liveness: process up
{
    Predicate = _ => false,                                           // no dependency checks
    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = "ok" }),
});
app.MapHealthChecks("/readyz", new HealthCheckOptions                // readiness: 200 or 503
{
    Predicate = r => r.Tags.Contains("ready"),
    ResponseWriter = (ctx, report) =>
    {
        var up = report.Status == HealthStatus.Healthy;               // down: out of rotation
        return ctx.Response.WriteAsJsonAsync(new { status = up ? "ready" : "down",
            checks = new { database = up ? "ok" : "unreachable" } });
    },
});
```

Probes, env-config and a thin Program.cs are the price of admission for a Kubernetes Deployment. Same liveness/readiness split a WCF host had — just owned by the cluster now.

p. 13

> Walk the code: ASP.NET Core 10 uses minimal hosting (Program.cs as a top-level script). Config flows from appsettings.json overridden by environment variables (factor III): ConnectionStrings__Default reaches GetConnectionString("Default"), the cloud-native equivalent of web.config transforms, except that the cluster injects the values through ConfigMaps and Secrets instead of an MSDeploy package. The two probes come from AddHealthChecks and MapHealthChecks in Example 01: /healthz is liveness (am I alive? if not, restart me, and Kubernetes kills the Pod) and runs no dependency check; /readyz is readiness (can I serve? if not, take me out of rotation but don't kill me): its check is AddDbContextCheck, which asks the EF Core context whether it can reach Postgres, and when that fails the endpoint answers 503 with status down, which removes the Pod from the Service endpoints. The probe reads the status code, not the body: Kubernetes treats any answer from 200 to 399 as ready. Getting these wrong is a top cause of cascading restarts, the same way wrong IIS app-pool ping settings used to crash apps under load. A ResponseWriter keeps the bodies identical in every language, so each stack serves the same paths and JSON; the package is Microsoft.Extensions.Diagnostics.HealthChecks.EntityFrameworkCore. The .NET runtime side: the service ships as a Linux container image built from a UBI Containerfile, not an MSI deployed to IIS.

## [016] Communications (sldId 271)

02

Match the interaction style to the call.

> Section two. The thesis: there is no single right protocol — there is a right protocol per interaction. Resist the urge to standardize on one wire for everything. The section gives a decision rule and then shows each protocol in code against the running system.

## [017] COMMUNICATIONS · Pick the protocol for the interaction (sldId 272)

REST for reach, gRPC for internal speed, GraphQL for client-driven reads, async for decoupled facts.

p. 14

> Four interaction styles, four defaults. REST for the public/edge surface where reach and caching matter; gRPC for internal service-to-service where latency and streaming matter; GraphQL for client-driven reads that compose many sources in one round trip; async events for decoupled facts that fan out. Most real systems use all four — the skill is matching each call to the right one. Note the sync/async chips at the bottom. This slide is the map for the whole section.

## [018] COMMUNICATIONS · REST at the edge with ASP.NET Core (sldId 273)

[chip] csharp · .NET 10 + ASP.NET Core minimal APIs

```csharp
// Program.cs — minimal API style; FluentValidation for input contracts
var orders = app.MapGroup("/orders");     // Microsoft.AspNetCore.OpenApi documents it
orders.MapPost("/", async (
        [FromBody] OrderIn body,
        IValidator<OrderIn> validator,            // FluentValidation
        IOrderService svc,
        IEventPublisher events) =>
{
    var result = await validator.ValidateAsync(body);
    if (!result.IsValid) return Results.ValidationProblem(result.ToDictionary());
    var order = await svc.CreateAsync(body);
    await events.PublishAsync("order.placed", order);       // made safe by the outbox
    return Results.Created($"/orders/{order.Id}", order);   // 201, not 200
});
orders.MapGet("/", (string? after, int limit, IOrderService svc) =>
    svc.Page(after, limit));                       // cursor pagination, not offset
// request record: immutable, validated (types follow the top-level statements)
public record OrderIn(
    [Required, StringLength(64)] string Sku,
    [Range(1, 1_000)]            int    Quantity);
```

Resource-shaped URLs, FluentValidation contracts, correct status codes, cursor pagination — the WCF endpoint replacement for the outside world.

p. 15

> This is the edge surface. For WCF refugees the mental shift: a Controller or minimal-API endpoint replaces an OperationContract; DataContract becomes a C# record with validation attributes; the binding (BasicHttp, NetTcp, MSMQ) becomes 'pick the right protocol per call' — here REST, gRPC and Kafka coexist instead of one endpoint multi-bound. Point out four things teams routinely get wrong: (1) resource-shaped URLs (nouns, not verbs), not /GetOrder?id=123 like an .asmx service; (2) request contracts validated declaratively, with records carrying [Required] and [Range] or FluentValidation rules, so bad input never reaches your logic; (3) correct status codes: Results.Created (201) on create, Results.ValidationProblem (RFC 9457) for validation failures, not 200 with success=false in the body; (4) cursor pagination, not offset, because offset breaks under concurrent writes and gets slow at depth. Microsoft.AspNetCore.OpenApi (built in since .NET 9) emits the OpenAPI spec automatically — the equivalent of WCF's WSDL but generated at build time, versioned in the registry, and gated in CI. NSwag and Swashbuckle (both MIT) are the alternatives if you need richer customisation.

## [019] COMMUNICATIONS · gRPC for internal service-to-service calls (sldId 274)

[chip] protobuf + csharp · .NET 10 + Grpc.AspNetCore

```protobuf+csharp
// inventory.proto — the contract, registered in Apicurio
syntax = "proto3";
service Inventory {
  rpc ReserveStock (ReserveRequest) returns (ReserveReply);
}
message ReserveRequest { string sku = 1; int32 quantity = 2; }
message ReserveReply   { bool reserved = 1; int32 remaining = 2; }
// Grpc.AspNetCore + Grpc.Tools compiles .proto to C# at build time
// (the cloud-native replacement for WCF NetTcpBinding service contracts)
public class InventoryService : Inventory.InventoryBase  // generated base
{
    private readonly IStockRepository _stock;
    public InventoryService(IStockRepository stock) => _stock = stock;
    public override async Task<ReserveReply> ReserveStock(
        ReserveRequest req, ServerCallContext ctx)
    {
        var r = await _stock.ReserveAsync(req.Sku, req.Quantity);
        return new ReserveReply { Reserved = r.Ok, Remaining = r.Remaining };
    }
}
// Program.cs
builder.Services.AddGrpc();                          // server registration
app.MapGrpcService<InventoryService>();              // expose the service
```

Schema-first, binary, multiplexed over HTTP/2 — the WCF NetTcpBinding replacement for chatty internal paths. Test with ghz.

p. 16

> gRPC for the internal paths. For WCF refugees this is the most familiar protocol in cloud-native: the .proto file is the service contract, exactly like a WCF [ServiceContract] interface, and the wire format is binary like NetTcpBinding. The Grpc.Tools NuGet package compiles the .proto with protoc at build time, generating both the C# message classes (similar to DataContracts) and an Inventory.InventoryBase abstract class — you derive from it and override the operations. Highlight that the field numbers (=1, =2) are the wire contract — we return to exactly why in Appendix B. Streaming RPCs (server, client, bidirectional) are first-class through IAsyncEnumerable<T>. The right default for chatty service-to-service calls where you control both ends, and the natural migration target for internal WCF endpoints. Load-test it with ghz. (Optional: mention that for browser clients, gRPC-Web via Grpc.AspNetCore.Web exposes the same service over HTTP/1.1 with limitations.)

## [020] COMMUNICATIONS · Synchronous coupling vs. asynchronous facts (sldId 275)

A synchronous call shares fate; an event shares a fact. Reach for async wherever immediacy isn't required.

p. 17

> The central trade-off of the whole talk in one picture. Top row: a synchronous call couples caller to callee in time and availability — if payment-service is down, the order request fails too, and availability multiplies downward across a chain. Bottom row: emitting order.placed as a fact lets the order succeed immediately; consumers catch up from the log if they were down. The rule: reach for async wherever immediacy isn't strictly required. This sets up the entire event-driven section later.

## [021] COMMUNICATIONS · The mesh handles the wire, not your code (sldId 276)

Istio sidecars give you mTLS, retries, timeouts and telemetry — uniformly, without per-service code.

p. 18

> Service mesh in one picture. Your app speaks plain HTTP or gRPC to localhost; the Istio sidecar (Envoy) intercepts and adds mTLS, retries, timeouts and telemetry on the wire — uniformly, for every service, with zero application code. istiod is the control plane distributing policy and identity (SPIFFE). The key insight ties back to principles: resilience and security become platform defaults, not per-service reimplementations. The configuration itself is an Istio VirtualService.

## [022] COMMUNICATIONS · Resilience as configuration, not per-call code (sldId 277)

[chip] yaml · istio

```yaml
# Istio: bounded retries and timeout for inventory-service
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: inventory }
spec:
  hosts: [inventory]
  http:
    - timeout: 2s
      retries:
          attempts: 2                 # bounded — never an unbounded retry storm
          perTryTimeout: 800ms
          retryOn: connect-failure,unavailable
      route:
        - destination: { host: inventory }
```

Bounded retries with backoff live in the mesh. Unbounded client retries are how an incident becomes an outage.

p. 19

> Resilience as configuration. This VirtualService gives inventory a 2-second timeout, two retry attempts with an 800ms per-try timeout, retrying only on connect-failure and unavailable. The critical word is bounded — attempts: 2, not infinite. Tell the war story: unbounded client-side retries are how a brief blip becomes a full outage, because every caller piles on the struggling service (a retry storm). Putting this in the mesh means it's consistent across every service and tunable without redeploying code.

## [023] Composition (sldId 278)

03

Aggregate at the edge, not inside services.

> Section three. The question: when a client needs data from several services, where does the joining happen? The answer that keeps services decoupled: at the edge, in a gateway or BFF — never by services calling each other in deep chains. That chaining is how you accidentally rebuild a monolith over the network.

## [024] COMPOSITION · One query, many services (sldId 279)

The gateway presents one schema and fans out to REST and gRPC back-ends, then joins and shapes the result.

p. 20

> GraphQL federation against the running system. The gateway presents one schema to clients and fans out to REST and gRPC back-ends, then joins and shapes the result. The client makes one round trip and asks for exactly the fields it needs. The services stay unaware of each other; the gateway owns the composition. Contrast this with services calling services, which we'll warn against on the patterns slide. The resolver code shows how the gateway composes the calls.

## [025] COMPOSITION · A composing resolver in HotChocolate (sldId 280)

[chip] csharp · .NET 10 + HotChocolate

```csharp
// HotChocolate (MIT, by ChilliCream) — the dominant open-source GraphQL server
// for .NET. Code-first or schema-first. Built-in DataLoader for N+1.
public class Query                                   // the gateway's schema
{
    public async Task<Order?> GetOrder(string id,    // REST call to order-service
        [Service] IOrderClient orders) =>
        await orders.GetAsync(id);
}
[ExtendObjectType<Order>]                            // adds fields to Order type
public class OrderExtensions
{
    // batched per-request to kill N+1: one gRPC call for N orders
    public async Task<int> GetStock(
        [Parent] Order order,
        IInventoryStockDataLoader loader) =>         // generated DataLoader
        await loader.LoadAsync(order.Sku);
}
// Program.cs registration
builder.Services
    .AddGraphQLServer()
    .AddQueryType<Query>()
    .AddTypeExtension<OrderExtensions>()
    .AddDataLoader<IInventoryStockDataLoader, InventoryStockDataLoader>();
app.MapGraphQL();                                    // POST /graphql + IDE
```

The gateway owns aggregation; each field resolves against the owning service. DataLoader batches N orders into one gRPC call.

p. 21

> The resolver makes federation concrete in HotChocolate. The top-level GetOrder Query calls order-service over REST; [ExtendObjectType<Order>] adds a stock field that resolves against inventory-service over gRPC. Each field resolves against its owning service — the gateway is just the composition layer. Mention the N+1 risk: naive per-field resolution can explode into many back-end calls — HotChocolate's DataLoader (in fact the same DataLoader pattern Facebook open-sourced for JavaScript) batches N orders into one upstream call automatically; the IInventoryStockDataLoader interface is generated by source-generators from your loader implementation. HotChocolate ships first-class Apollo Federation support if you go that route. The schema is exposed at POST /graphql plus an in-browser GraphQL IDE (Banana Cake Pop / Nitro) at /graphql in development. Where this lands for a .NET-from-Windows audience: think of it as the long-overdue replacement for SOAP composition or for hand-rolled aggregation endpoints — one wire, one schema, many backends.

## [026] COMPOSITION · Three ways to compose — and where each belongs (sldId 281)

Push aggregation to a gateway or BFF. Chaining calls inside services rebuilds the monolith over the network.

p. 22

> Three composition patterns: an API gateway (one composed schema for everyone), a backend-for-frontend (a tailored aggregate per client type — web vs mobile), and GraphQL federation (a distributed graph). All three push aggregation outward to the edge. The anti-pattern to call out explicitly: service-to-service call chains, where order calls inventory calls pricing calls… — synchronous, deeply coupled, and impossible to reason about. That rebuilds the monolith with network latency between the pieces.

## [027] COMPOSITION · Blazor Server as a line-of-business BFF (sldId 282)

- Blazor Server is inherently BFF-shaped: a server-side .NET process holds the UI's view-model and pushes UI diffs to the browser over a SignalR channel — the client is thin.
- Inside that server-side process you can aggregate from REST, gRPC and Kafka back-ends with normal .NET code (typed HttpClient, gRPC client, Confluent.Kafka consumer) — no client-side fan-out, no CORS dance, no token-passing through the browser.
- Runs on Kubernetes as a regular ASP.NET Core Pod, with no managed hosting and no managed SignalR service. The SignalR backplane is open-source Redis (we cover the pinning + backplane story in Appendix C).
- When to choose it: internal LOB apps, admin consoles, dashboards — where you want server-rendered state, server-side auth, and a single trust boundary. Pair with Blazor WebAssembly for the offline / high-interactivity client surface (Appendix C).
- When not to choose it: SEO-critical public sites (use static rendering or SSR), or anything that must work without a persistent connection. Every Blazor Server interaction is a SignalR round-trip and inherits the WebSocket scaling concerns in Appendix C.

p. 23

> The slide makes the BFF pattern from the previous diagram concrete in the .NET world. Blazor Server is more than a UI framework: architecturally it is a backend-for-frontend. The server-side process maintains the user's session-scoped component tree and pushes UI updates (Render Tree Diffs) to a thin JavaScript client over SignalR. That means everything happens server-side: authentication is server-side cookie-based, calls to inventory and pricing are server-to-server (typed HttpClient or gRPC stub), and the browser never sees a back-end URL or token. For LOB and admin tooling this collapses three problems at once (composition, auth boundary, real-time updates) into one server-side process. The Kubernetes posture is straightforward: containerized ASP.NET Core, plus Redis as the SignalR backplane (covered in Appendix C). What it avoids: a managed SignalR service and managed app hosting (Kubernetes is the deployment target); Blazor WASM is hosted as static files inside an nginx Pod or the ASP.NET Core process itself. The trade-off in the bold line is the real one: every interaction is a round-trip, every component instance is a per-user session living in a Pod, and scaling the Blazor Server pool has the same head-of-line / pinning / connection-count concerns we cover in Appendix C — don't pick it for traffic shapes where those bite. For high-interactivity client-side execution use Blazor WebAssembly, also covered in Appendix C.

## [028] Data (sldId 283)

04

Own your data; share it through contracts.

> Section four, and the hardest discipline to hold. The rule: each service owns its data and shares it only through APIs and events — never through a shared database or by reaching into another service's tables. This is what makes independent deployment and independent scaling real. The slides cover ownership, the dual-write trap, and the saga.

## [029] DATA · A database per service (sldId 284)

Each service owns its schema and storage engine; no other service touches its tables directly.

p. 24

> Database-per-service. Each service owns its schema and even its storage engine — order and payment on Postgres, something else on a document store if that fits. No other service touches those tables directly; the only doors in are the API and the events. The hard part is social, not technical: someone will always want to 'just join across two services' databases' for a report. That shortcut is the single most common way microservice independence dies. Reporting needs go through the metadata/lineage layer or a dedicated read model, not direct table access.

## [030] DATA · CQRS — Command Query Responsibility Segregation (sldId 285)

Separate the write model from the read model. They have different shapes, scales and even different stores.

p. 25

> CQRS (Command Query Responsibility Segregation) is the pattern of using different models for writes and reads. The write side optimises for invariants and consistency: a normalised schema in a transactional store (Postgres, MySQL). The read side optimises for query shape: denormalised wide tables, an Elasticsearch index, a Mongo document, or whatever fits the question being asked. The two are linked by a stream of events: either domain events emitted by the write side, or the database commit log itself via CDC, the log-tailing pattern. The cost: eventual consistency, a small lag between the write committing and the read model catching up. The benefit: each side can scale, schema-evolve and even be stored independently. Use this pattern when reads and writes have different shapes and access patterns. Avoid it when a single store handles both; CQRS adds operational complexity that isn't free. The classic motivating case: a service that takes thousands of writes per second but is read by analytics, dashboards and search — the write model serves the writes, the read model serves the rest. CQRS pairs naturally with event sourcing on the write side and event streaming for projections; the Event-Driven section draws both distinctions.

## [031] DATA · CQRS in practice (sldId 286)

[chip] csharp · ASP.NET Core 10 + EF Core + Confluent.Kafka

```csharp
// Write side — the command handler commits, then emits the fact
[ApiController, Route("orders")]
public class OrderWriteController(WriteDb writes, IProducer<string, string> producer)
    : ControllerBase
{
    [HttpPost]
    public async Task<ActionResult<Order>> Create(OrderIn body, CancellationToken ct)
    {
        var order = new Order(body);
        writes.Orders.Add(order);
        await writes.SaveChangesAsync(ct);                        // write model
        await producer.ProduceAsync("order.placed", new Message<string, string>
            { Key = order.Id, Value = JsonSerializer.Serialize(order) }, ct);
        return Ok(order);                        // the outbox makes this crash-safe
    }
}
// Read side — a different, denormalised store (OrderReadController(ReadDb reads))
[HttpGet("{id}/summary")]
public async Task<ActionResult<OrderSummary>> Summary(string id, CancellationToken ct) =>
    await reads.OrderSummaries.FindAsync([id], ct) is { } s ? Ok(s) : NotFound();
// Projection — a BackgroundService on Confluent.Kafka, idempotent upsert
var cr = consumer.Consume(stoppingToken);   // in ExecuteAsync
var summary = OrderSummary.From(JsonSerializer.Deserialize<Order>(cr.Message.Value)!);
await reads.UpsertAsync(summary, stoppingToken);                        // keyed by order id
consumer.Commit(cr);                                          // ack after the write
```

p. 26

> The .NET shape with primary constructors. OrderWriteController handles writes through WriteDb, an EF Core context on the write database, then produces order.placed with Confluent.Kafka, keyed by the order id. The read side queries ReadDb, a separate context on a denormalised store: another Postgres, or a search index.
>
> The projection is a BackgroundService that runs a Confluent.Kafka consumer loop; the host cancels its stoppingToken on shutdown. It deserializes each event, upserts the summary row keyed by the order id, and commits the offset only after the write, so a crash means redelivery and the upsert keeps the replay idempotent.
>
> Producing right after SaveChangesAsync is a dual write; in production the outbox from the Data section closes that gap. Each side scales on its own load: the write side on commands, the read side on queries.

## [032] DATA · Log tailing — the database commit log is the event stream (sldId 287)

Debezium tails the WAL and publishes every committed row as a Kafka event. No dual-write.

p. 27

> The mechanism that makes CQRS projections and the outbox pattern work: Change Data Capture, or CDC. The application writes ordinary SQL. The database commits and the change lands in the write-ahead log (WAL on Postgres, redo log on Oracle, binlog on MySQL, transaction log on SQL Server). Debezium, an Apache 2.0 open-source project running as a set of Kafka Connect connectors, tails that log via the database's native replication protocol (logical replication slots on Postgres, etc.), translates row-level deltas into Kafka events, and publishes them with commit ordering preserved. The application doesn't know Debezium exists. There is no dual-write — the commit is the single source of truth, and the event is a strictly downstream consequence. This is why log tailing matters before the outbox: the outbox is a targeted use of CDC for a specific case (publishing events that aren't naturally row-level), and CQRS projections are the other big use. Debezium supports Postgres, MySQL, MariaDB, SQL Server, Oracle, MongoDB, Db2, Cassandra, and Vitess out of the box. Run mode: deploy as Kafka Connect workers, or use Debezium Server (standalone) if you don't want a Kafka Connect cluster. WAL = Write-Ahead Log: the database's commit-ordered durable log that already exists for replication and crash recovery; Debezium just subscribes to it.

## [033] DATA · Dual-write is unsafe — use the outbox (sldId 288)

Write state and the outbox row in one transaction; CDC relays the committed fact to Kafka.

p. 28

> This is the slide that prevents a class of production bugs. The dual-write problem: if you write to your database and then publish to Kafka as two separate operations, a crash between them leaves you inconsistent — the order exists but the event was never sent, or vice versa. The fix is the transactional outbox: write the state change and an outbox row in one local transaction, then a change-data-capture tool (Debezium) tails the database log and relays the committed row to Kafka. The database commit is the single source of truth. The outbox write itself is one database transaction, shown in code.

## [034] DATA · The outbox write — one transaction, no lost events (sldId 289)

[chip] csharp · EF Core + Debezium CDC

```csharp
// POST /orders (excerpt), examples/04-data/dotnet: EF Core + Debezium CDC, the .NET outbox.
// For WCF/COM+ refugees: this replaces the MSDTC two-phase commit you used
// to make 'save the order and queue the event' atomic across databases.
app.MapPost("/orders", async (OrderRequest request, OrdersContext db) =>
{
    var order = new Order { Id = Guid.NewGuid().ToString(), Sku = request.Sku,
                            Quantity = request.Quantity, Status = "confirmed" };
    var dto = OrderDto.From(order);
    db.Orders.Add(order);                         // state change
    db.Outbox.Add(new OutboxEvent                 // same SaveChanges: outbox row
    {
        AggregateId = order.Id,
        EventType = "order.placed",
        Payload = JsonSerializer.SerializeToElement(dto, JsonSerializerOptions.Web),
    });
    await db.SaveChangesAsync();                  // one local txn; Debezium tails the WAL
    return Results.Json(dto, statusCode: StatusCodes.Status201Created);
});
// No Kafka call on the request path: if the broker is down, the order still
// commits and the event ships when the Debezium connector catches up.
// Wolverine (MIT) ships an EF Core transactional outbox if you prefer a framework.
```

One local DB commit replaces MSDTC. Debezium tails the write-ahead log and turns the outbox row into a guaranteed, ordered Kafka event.

p. 29

> For the WCF/COM+ audience this is the most important pattern. You used to write code like 'TransactionScope: save order, write to MSMQ, commit' — and MSDTC made it atomic across the SQL Server and MSMQ resource managers. Kubernetes has no MSDTC. You don't want one (two-phase commits across services don't scale and create coupling). Instead: write the state change and an outbox row in one local database transaction — atomic by definition because it's a single resource manager. There's no Kafka call inside the request path — if Kafka is down, the order still commits, and the event ships later when Debezium tails the Postgres WAL (or SQL Server CDC) and relays the outbox row in commit order. This decouples your request latency and availability from Kafka's, which COM+ never could. Two ways to wire it up in .NET: write the OutboxEvent entity manually as shown, where one SaveChangesAsync commits the order and the outbox row in a single transaction (Postgres/SQL Server + the Debezium Outbox Event Router single-message transform handles the unwrap on the connector side); or use a framework outbox such as Wolverine's (MIT) EF Core integration, which gives the same guarantees with framework-managed plumbing. Either way: this same commit-together discipline reappears in the saga appendix.

## [035] DATA · Consistency without distributed transactions: the saga (sldId 290)

A chain of local transactions; failures trigger compensating actions, never a cross-service rollback.

p. 30

> The saga is how you get consistency across services without a distributed transaction (there is no two-phase commit here, and you don't want one). It's a sequence of local transactions, each emitting the event that triggers the next: order created, payment taken, stock reserved, shipment booked. When a step fails (payment fails), you don't roll back; you run compensating actions for the steps that already committed (cancel the order). Flag that Appendix D goes deep on saga state, compensation and a tricky data-dependency case, for anyone who wants the mechanics.

## [036] Event-Driven (sldId 291)

05

Emit facts; let consumers decide.

> Section five — the asynchronous backbone we kept pointing at. The mental shift: a producer emits a fact about something that happened (order.placed) and does not know or care who consumes it. Consumers decide what to do. This inverts the dependency direction, and it is what decouples services in time and ownership.

## [037] EVENT-DRIVEN · The event backbone — one fact, many reactions (sldId 292)

order.placed fans out to consumers the producer never names. Add a consumer without touching the producer.

p. 31

> order.placed fans out to payment, shipping and notification — and the producer names none of them. The power move: you can add a new consumer (say, a fraud-check service) without touching or redeploying the producer. Contrast with the synchronous world, where adding a dependency means changing the caller. This is the open/closed principle at the architecture level. Kafka (run by Strimzi on Kubernetes) is the backbone; Pulsar is an alternative with similar semantics.

## [038] EVENT-DRIVEN · Producing and consuming with Confluent.Kafka (sldId 293)

[chip] csharp · .NET 10 + Confluent.Kafka 2.16.0

```csharp
// Confluent.Kafka 2.16.0 — the low-level Kafka client (Apache 2.0).
// Auto-commit off, commit after the work: at-least-once processing.
// producer — order-service emits the fact
var producer = new ProducerBuilder<Null, string>(
    new ProducerConfig { BootstrapServers = kafkaBootstrap }).Build();
await producer.ProduceAsync("order.placed",
    new Message<Null, string> { Value = json });     // awaits the broker ack
// consumer — ShipmentWorker : BackgroundService; the host cancels stoppingToken on SIGTERM
using var consumer = new ConsumerBuilder<Ignore, string>(new ConsumerConfig
{
    BootstrapServers = config.GetValue("KAFKA_BOOTSTRAP", "kafka:9094"),
    GroupId          = "shipping-group",
    AutoOffsetReset  = AutoOffsetReset.Earliest,
    EnableAutoCommit = false,
}).Build();
consumer.Subscribe("order.placed");
while (!stoppingToken.IsCancellationRequested)
{
    var cr = consumer.Consume(stoppingToken);
    await HandleAsync(cr.Message.Value);   // exists? skip; unique index on order_id backs it
    consumer.Commit(cr);                   // ack after — at-least-once
}
```

Confluent.Kafka keeps the Kafka semantics visible: keys, partitions, offsets. Commit after the work; handlers are idempotent.

p. 32

> Confluent.Kafka is the .NET Kafka client for every Kafka path in this deck, pinned at 2.16.0. MassTransit was dropped: its abstraction hides the Kafka semantics this section teaches (keys, partitions, consumer groups, offsets), and version 9 moved to a commercial license.
>
> The producer emits order.placed and awaits the broker's delivery report. The consumer joins notification-group, starts from the earliest offset, and runs with auto-commit off.
>
> Two points to drill home. First, the offset is committed only after the work succeeds; a crash before the commit means redelivery, so delivery is at-least-once and handlers must be idempotent (dedupe by order id or an idempotency key). Exactly-once is mostly at-least-once plus idempotency. Second, the loop is yours: retries, dead-letter topics and shutdown are explicit code, shown in Appendix E and Appendix H. In the running example each consumer is a BackgroundService in a Worker SDK host: the host cancels its stoppingToken on SIGTERM, and the handler looks the order up before inserting, with the unique index on order_id as the backstop, so a redelivered record is processed once. Apicurio holds the schemas.

## [039] EVENT-DRIVEN · Schemas are the contract — the registry enforces them (sldId 294)

Apicurio holds versioned schemas; compatibility is checked at publish time so breaking changes are rejected early.

p. 33

> Events need contracts as much as REST and gRPC do, or more, because consumers are anonymous and you can't call them to coordinate. The schema (Avro, Protobuf or JSON Schema) lives in Apicurio. Producers and consumers fetch it; compatibility is checked at publish time so a breaking change is rejected before it ever reaches the topic. This is what makes adding a consumer safe. We come back to event versioning rules in Appendix B.

## [040] EVENT-DRIVEN · Event sourcing vs. event streaming (sldId 295)

Two patterns, often confused. Sourcing: the events are the state. Streaming: events are the transport.

p. 34

> The vocabulary clarification most teams need before they go further with events. Event sourcing means events are the database — there is no 'current state' row anywhere; current state is computed by folding the entire event history. Adding a credit to an account isn't UPDATE balance SET balance = balance + 100; it's INSERT INTO events VALUES ('credit', 100), and reading the balance means summing every event for that account (with snapshots for performance). Strong fit for audit-heavy systems (banking, healthcare records, regulatory), temporal queries ("what was the balance on March 3rd?"), and any domain where the history is itself a primary asset. Tools: Marten (Postgres-backed, .NET), EventStoreDB, Axon (JVM). Event streaming means events are how facts move between services — each service still keeps its current state in a normal database, but emits events ("order.placed", "payment.processed") that other services subscribe to. The event is a transport mechanism, not a storage mechanism. Strong fit for integration, fan-out, decoupling. Tools: Kafka, Pulsar, NATS JetStream. These are not mutually exclusive. A common combination is full CQRS: the write side is event-sourced (so you have an audit trail of state changes), and the read-side projections are fed by streaming those events to consumers that build denormalised views. The acid test: is the event itself the source of truth (sourcing), or is it a propagated fact about a change that happened in a store (streaming)? In most enterprise architectures, streaming is far more common than sourcing; sourcing fits domains where audit and replay are core.

## [041] EVENT-DRIVEN · Event-driven tools landscape — Kafka, Pulsar, Flink, NiFi (sldId 296)

Different jobs, often together: substrate (Kafka, Pulsar), compute (Flink), movement (NiFi, Debezium).

p. 35

> Each of the four tools does a different job. Kafka is the substrate: a partitioned, ordered, durable log. Consumers track their own offsets and can replay. It's the de facto event spine for cloud-native architectures; Strimzi runs it natively on Kubernetes. Pulsar is also substrate, in the same broad category as Kafka but with native pub/sub plus queue semantics in the same product, tiered storage that pushes cold data to cheap object stores automatically, and multi-tenancy built into the broker. Pulsar has a Kafka-protocol shim so consumers can speak Kafka while writing to Pulsar. Flink is compute: not a transport layer, but a stateful stream-processing engine. Flink sits on top of Kafka or Pulsar, consumes streams, applies operators (windowed aggregations, joins, filters, stateful transformations) with exactly-once semantics via checkpointing, and produces new streams. Alternatives: Kafka Streams (lighter, JVM-only, embedded library), Spark Structured Streaming (heavier, batch-mindset). NiFi is movement: a visual dataflow / ETL tool with 200+ source-and-sink connectors and back-pressure built in. Think of it as the answer to 'I need to get data from SFTP to Kafka to an object store with these transforms in the middle' — you draw the flow in the UI rather than writing a pipeline. Debezium (covered in the Data section) is the CDC variant of movement. Together they compose: typical pipeline is source DB → Debezium or NiFi → Kafka or Pulsar → Flink for windowed aggregations → sink. The mistake is treating these as competitors. They complement each other; pick by the question your team is asking: durably hold events (substrate), compute over them (Flink), move them around (NiFi/Debezium).

## [042] EVENT-DRIVEN · The log is the source of truth (sldId 297)

Consumers track their own offset; replay is just rewinding. Kafka (Strimzi) and Pulsar are logs, not queues.

p. 36

> The mental model correction most people need: Kafka is a log, not a queue. Messages are retained after they are read, and each consumer group tracks its own offset. That means replay is just rewinding an offset: a new consumer can process all of history, and a buggy consumer can be fixed and replayed. This is the foundation for event sourcing and for rebuilding stream-processing state, the subject of stream processing. Strimzi runs Kafka on Kubernetes; Pulsar offers similar log semantics with tiered storage.

## [043] Stream Processing (sldId 298)

06

Streams in, derived streams out.

> Section six builds directly on the log. Once events are a durable, replayable stream, you can compute over them continuously (filtering, joining, windowing, aggregating) and emit new derived streams. This is where real-time analytics, materialized views and complex event reactions live.

## [044] STREAM PROCESSING · Derive new streams from streams (sldId 299)

A streaming app is a topology of sources, stateful processors and sinks — joins, windows and aggregates.

p. 37

> A stream-processing app is a topology: sources (input topics), stateful processors (filter, join, window, aggregate) and sinks (output topics or stores). The output of one topology is just another stream that other services consume. Emphasize stateful — unlike a simple consumer, these processors keep local state (running totals, window buffers) that must survive restarts. That state-management problem is what the next code slide and KEDA slide address.

## [045] STREAM PROCESSING · A windowed aggregation with Streamiz.Kafka.Net (sldId 300)

[chip] csharp · Streamiz.Kafka.Net 1.8.2

```csharp
// StreamProcessor/RevenueStream.cs (excerpt), a BackgroundService — Streamiz.Kafka.Net 1.8.2
var config = new StreamConfig<StringSerDes, StringSerDes>
{
    ApplicationId    = "stream-processor",    // also the consumer group
    BootstrapServers = kafkaBootstrap,
    StateDir         = "/tmp/kafka-streams",  // local RocksDB, changelog-backed
};
var builder = new StreamBuilder();
builder.Stream<string, string>("order.placed")
    .Map((_, json, _) => Rekey(json))                     // key by merchant_id
    .Filter((merchant, _, _) => merchant.Length > 0)
    .GroupByKey()
    .WindowedBy(TumblingWindowOptions.Of(TimeSpan.FromSeconds(windowSeconds), TimeSpan.Zero))
    .Aggregate(() => new Acc(),
        (merchant, amount, acc) => Add(merchant, acc, amount),   // exact decimal total
        RocksDbWindows.As<string, Acc>("revenue-store")
            .WithKeySerdes(new StringSerDes())
            .WithValueSerdes(new JsonSerDes<Acc>()))
    .ToStream()
    // .Map(...): window_start, merchant_id, order_count, revenue rounded half-up
    .To<StringSerDes, StringSerDes>("revenue.by-merchant");
await new KafkaStream(builder.Build(), config).StartAsync(stoppingToken);
```

Local RocksDB + a Kafka changelog topic gives fault-tolerant aggregation — no JVM, no separate Flink cluster, just C# in a Pod.

p. 38

> Streamiz.Kafka.Net 1.8.2 (MIT) is a .NET implementation of the Kafka Streams model: the same topology, state-store and changelog design, in native C#, with no JVM in the container.
>
> The processor in the running example is a BackgroundService in a Worker SDK host; it keys each order by merchant, groups by key, and aggregates into tumbling windows (WINDOW_SECONDS, 10 s in the example) held in a RocksDB window store backed by a Kafka changelog topic. If the Pod dies, the state rebuilds by replaying the changelog. The aggregate keeps an exact decimal total and skips records whose amount does not parse; the output rounds half-up to two places, the same contract as the Spring Boot and Quarkus Kafka Streams processors.
>
> ApplicationId is also the consumer group, so KEDA can scale the processor on its lag. For this audience it replaces SQL Server Service Broker activation procedures or a hand-rolled Windows Service draining MSMQ. Alternatives if Streamiz doesn't fit: Apache Flink as a separate service fed by Kafka, Akka.NET Streams for in-process reactive streams, or Orleans Streams on the virtual-actor model.

## [046] STREAM PROCESSING · KEDA scales workers on the signal that matters (sldId 301)

Scale Kafka workers on consumer lag and HTTP services on request rate — both down to zero when idle.

p. 39

> KEDA closes the elasticity loop. The right scaling signal for an event consumer is consumer lag, how far behind the log it is, not CPU. KEDA reads that lag and scales workers up, and down to zero when there's no lag. For synchronous HTTP services, the KEDA http-add-on scales on request concurrency/rate. One mechanism, two signals. Scale-to-zero is a real cost lever for spiky workloads. The KEDA configuration covers both: lag for events and RPS for HTTP.

## [047] STREAM PROCESSING · Scale on lag (events) and on RPS (HTTP) (sldId 302)

[chip] yaml · KEDA

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata: { name: payment-consumer }
spec:
  scaleTargetRef: { name: payment-consumer }
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
    - type: kafka
      metadata: { bootstrapServers: "cndp-kafka-bootstrap:9092", topic: order.placed,
                  consumerGroup: payment, lagThreshold: "100" }
---
# HTTP: scale the ASP.NET Core service on concurrent requests (KEDA http-add-on)
apiVersion: http.keda.sh/v1alpha1
kind: HTTPScaledObject
metadata: { name: order-service }
spec:
  hosts: [orders.example.com]
  scaleTargetRef: { name: order-service, service: order-service, port: 8080 }
  replicas: { min: 0, max: 30 }
```

One mechanism, two signals: queue depth for async workers, concurrency for synchronous APIs.

p. 40

> Two manifests, one idea. The ScaledObject scales payment-consumer on Kafka lag for the order.placed topic, with minReplicaCount: 0 — true scale to zero when the topic is quiet, springing back when lag builds. The HTTPScaledObject does the same for the synchronous order-service based on request load via the http-add-on. The lagThreshold of 100 is the tuning knob: how many messages of backlog before adding a worker. Point out that scale-to-zero plus a cold-start budget is the trade-off to discuss with the audience for latency-sensitive paths.

## [048] Workflows and Jobs (sldId 303)

07

Not every unit of work is a request.

> Section seven. A lot of real work is not a synchronous request at all: it's a multi-step business process, or batch and scheduled work. Two topics: how to coordinate multi-step flows (orchestration vs choreography) and where long-running and periodic work belongs on Kubernetes. For orchestration in this stack we feature the Temporal .NET SDK for durable execution as the primary approach, with the Stateless library as a lighter-weight in-process alternative for state-driven flows. Dapr Workflows gets a brief mention for environments that prefer the sidecar pattern. Appendix D shows the primary pair (Temporal .NET + Stateless), side by side, against the saga from the data section.

## [049] WORKFLOWS AND JOBS · Orchestration vs. choreography (sldId 304)

A coordinator that commands keeps the flow in one place; events that trigger each other decouple but hide the flow.

p. 41

> The two ways to coordinate a multi-step process. Orchestration: a central coordinator explicitly commands each service in turn, so the flow is visible and observable, but the coordinator can become a god-service. Choreography: each service reacts to the previous one's event with no central brain — maximally decoupled, but the end-to-end flow is emergent and hard to see. Neither is universally right; choose by the selection criteria in the comparison. This connects straight to the saga discussion and Appendix D.

## [050] WORKFLOWS AND JOBS · Choosing between the two (sldId 305)

Orchestration

- One coordinator owns the saga and its state
- Flow is explicit and centrally observable
- One place to reason about, change and audit
- Risk: the orchestrator becomes a god-service
- Good for complex, long-lived business processes

Choreography

- Each service reacts to the previous event
- Maximally decoupled; no central bottleneck
- Flow is emergent — harder to see end-to-end
- Risk: nobody owns the overall process
- Good for simple, additive event reactions

p. 42

> The decision heuristic: use orchestration for complex, long-lived business processes where you need auditability and a clear owner (order fulfillment, loan approval). Use choreography for simple, additive reactions where decoupling matters more than visibility (send a welcome email when a user signs up). The failure modes are mirror images: orchestration risks a god-service; choreography risks nobody owning the process and no one able to answer 'where is order 42 stuck?'. Observability (section 11) is what makes choreography survivable.

## [051] WORKFLOWS AND JOBS · Jobs, CronJobs and queue workers (sldId 306)

Long, batch or periodic work belongs in Jobs/CronJobs or a scaled queue worker — never on the request path.

p. 43

> Where non-request work lives on Kubernetes. A Job runs a task to completion (a data migration, a nightly export). A CronJob schedules Jobs (the reconciliation that runs at 2am). A queue worker continuously drains a topic and is scaled by KEDA on lag. The anti-pattern: doing long or heavy work inside an HTTP handler, blocking the request and timing out the client. The rule of thumb on screen — long, batch or periodic work never belongs on the request path. Hand it to a Job or a worker and return immediately, ideally with a status URL the client can poll. In-app, BackgroundService with PeriodicTimer (or Quartz.NET for cron expressions, with DistributedLock for cluster-aware locking) covers recurring work in the same process; Kubernetes Jobs and CronJobs own the heavier or isolated batch runs; and KEDA's Cron scaler is the declarative way to wake a worker on a schedule — typically how Windows Scheduled Tasks become cloud-native.

## [052] API Management (sldId 307)

08

Treat the API surface as a platform.

> Section eight zooms out from individual services to the API surface as a whole. Management is four cooperating concerns, not a product you buy: runtime control (gateway and mesh), contracts (registry), discovery (metadata), and signals (observability). The next three sections each take one of these in depth.

## [053] API MANAGEMENT · Four cooperating planes (sldId 308)

Gateway and mesh at runtime; registry for contracts; metadata for discovery; observability for signals.

p. 44

> The four planes, and they map exactly to the rest of the platform sections. Runtime plane: the gateway and Istio mesh handle traffic, auth, rate-limiting and resilience. Contract plane: the registry (section 9) holds every API and event schema, versioned and gated. Discovery plane: metadata/catalog (section 10) lets people find and trust APIs. Signal plane: observability (section 11) tells you what is happening. The point: these are distinct responsibilities with distinct owners, not one monolithic 'API gateway product' that tries to do everything.

## [054] API MANAGEMENT · Versioning and evolution are part of management (sldId 309)

- Evolve additively — new optional fields and endpoints; never repurpose or remove without a new version.
- Carry a major version in the path (/v2) or media type; deprecate with headers and a sunset date.
- The registry's compatibility rules (BACKWARD / FORWARD / FULL) enforce this mechanically at publish time.
- Run old and new side by side; migrate consumers off the old contract before you retire it.
- Lifecycle: design → register → publish → consume → deprecate → retire — each step has an owner and a gate.

p. 45

> Versioning is a management concern, not an afterthought. The core discipline: evolve additively; add optional fields and new endpoints, never repurpose a field or remove one without a deprecation period. When you must break, carry a major version (in the path or media type) and run old and new side by side with a published sunset date, migrating consumers off before retiring. The registry's compatibility rules enforce the additive discipline mechanically at publish time. The bold lifecycle line is the takeaway: every contract moves design → register → publish → consume → deprecate → retire, and each transition has an owner and a gate. Appendix B drills into how REST, gRPC and GraphQL each handle this differently.

## [055] API Registry (sldId 310)

09

One versioned home for every contract.

> Section nine. If contracts are the boundary, they need one authoritative home. The registry is where every OpenAPI spec, .proto, AsyncAPI doc and event schema lives — versioned, compatibility-checked, and gated in CI. This is the difference between 'we have contracts somewhere in git' and 'contracts are enforced before code ships'.

## [056] API REGISTRY · Apicurio: contracts, versioned and gated (sldId 311)

OpenAPI, AsyncAPI, proto and Avro/JSON schemas live in one registry with compatibility rules and CI gating.

p. 46

> Apicurio is the concrete registry in this stack. Every contract type lands here: REST OpenAPI, GraphQL SDL, gRPC .proto, and event schemas (Avro/JSON). Each artifact has versions and a compatibility rule (BACKWARD, FORWARD, FULL). At publish time the registry checks the new version against the rule and rejects incompatible changes. Producers register; consumers fetch and generate stubs. The serde libraries for Kafka pull schemas from here by ID at runtime. A CI gate turns this into an automatic guardrail.

## [057] API REGISTRY · Gate breaking changes in CI (sldId 312)

[chip] yaml · CI + Apicurio v3 REST

```yaml
# No Maven plugin for .NET: gate breaking changes through the Apicurio v3 REST API.
# dryRun=true runs the COMPATIBILITY rule server-side and stores nothing.
# .github/workflows/contracts.yml (runs on every PR; no app build needed)
jobs:
  schema-compat:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Gate the new Avro schema against the registry rule
        env:
          REGISTRY: http://apicurio.registry.svc/apis/registry/v3
        run: |
          body=$(jq -n --rawfile s src/Schemas/order-placed.avsc \
            '{content: {content: $s, contentType: "application/json"}}')
          code=$(curl -s -o resp.json -w '%{http_code}' -X POST \
            "$REGISTRY/groups/orders/artifacts/order-placed/versions?dryRun=true" \
            -H 'Content-Type: application/json' -d "$body")
          # 400 with RuleViolationException: the COMPATIBILITY rule rejected it
          [ "$code" = "200" ] || { echo 'Breaking schema change'; cat resp.json; exit 1; }
```

The dry-run fails the build on an incompatible change — the contract is enforced before code ships, not after.

p. 47

> This is the guardrail that makes the whole contract story real, done the .NET way. A CI step posts the new schema to the Apicurio Registry v3 REST API as a dry-run create-version, which runs the artifact's compatibility rule server-side without persisting it — and fails the build (and the merge) if it's incompatible. The point to make: the contract is enforced before code ships, not discovered broken in production by a downstream team. The rule (e.g. BACKWARD — new consumers can read old data) is set once per artifact and enforced automatically forever; a separate (non-dry-run) POST publishes the version on the main branch after merge. Tie it back: this is design-first from section 1, now mechanized in the build.

## [058] API Metadata (sldId 313)

10

If they can't find it, it doesn't exist.

> Section ten. A contract that's enforced but undiscoverable is half useless. Metadata is the discovery and trust layer: a searchable catalog of every API, topic and table, with ownership, lineage and quality signals. If a consumer can't find your API and trust it, they'll build their own or screen-scrape — and your boundary erodes.

## [059] API METADATA · Discovery, lineage and ownership (sldId 314)

OpenMetadata ingests from services, the registry and Kafka to build a searchable catalog with lineage.

p. 48

> OpenMetadata is the catalog in this stack. It ingests from many sources (OpenAPI specs, the Apicurio registry, Kafka topics, Postgres schemas) and builds one searchable catalog. The differentiator over a wiki is automated lineage: it knows that this topic feeds that table feeds this API, so it can answer 'if I change this field, who breaks?' before you change it. Ingestion is a scheduled connector, so the catalog stays current without manual upkeep. What consumers get from the catalog is the point of running it.

## [060] API METADATA · What the catalog gives every consumer (sldId 315)

- Discovery — search across APIs, topics and tables; find the owning team and how to get access.
- Trust — published SLOs, data-quality test results, freshness, and a tier/criticality rating.
- Lineage — column- and topic-level lineage answers 'if I change this, who breaks?' before you change it.
- Ownership & governance — tags, classifications (PII), and accountable owners attached to every asset.
  - Ingestion runs as a scheduled connector against OpenAPI specs, the registry, Kafka and Postgres.

p. 49

> Four concrete payoffs for consumers. Discovery: search across APIs, topics and tables, and find the owning team and how to get access — no more asking around in Slack. Trust: published SLOs, data-quality results, freshness and a criticality tier tell you whether to depend on it. Lineage: column- and topic-level impact analysis answers the change-safety question proactively. Ownership and governance: tags, PII classifications and accountable owners on every asset — which is also what your compliance team needs. The throughline of sections 9–10: a contract is only as good as your ability to find it, trust it, and know who owns it.

## [061] Observability (sldId 316)

11

Instrument once; correlate everything.

> Section eleven, and the one that makes everything else operable. In a distributed system you cannot debug by reading one log file — a single user action touches five services. Observability is how you reconstruct that story. The key word is correlate: traces, metrics and logs become useful together only when they share a trace_id so you can pivot between them.

## [062] OBSERVABILITY · Three signals, one correlated story (sldId 317)

OpenTelemetry emits traces, metrics and logs; the LGTM-style stack stores them and Grafana joins them.

p. 50

> Three signals, each answering a different question. Traces: where did the time go and which service failed in this one request? Metrics: what are the aggregate rates, errors and latencies over time? Logs: what exactly happened in this component? OpenTelemetry is the vendor-neutral way to emit all three from your code. The LGTM-style stack stores them (Tempo for traces, Mimir/Prometheus for metrics, Loki for logs), and Grafana joins them. The magic is the shared trace_id linking a metric spike to the exact traces and logs behind it. The instrumentation comes first, then the trace.

## [063] OBSERVABILITY · The signals in depth — traces, metrics, logs, baggage, profiles (sldId 318)

Three classic pillars plus two that matter more every year. OpenTelemetry emits all five; one trace_id correlates them.

p. 51

> Expand the 'three pillars' framing into the five signals modern observability uses. Traces answer where the time went and which hop failed in one request. Metrics answer the trend question — aggregate rates, errors, latencies over time (the RED method: Rate, Errors, Duration; the USE method: Utilisation, Saturation, Errors). Logs answer what exactly happened in one component. Baggage is the signal most people miss — it's key-value context (tenant_id, user_tier, feature_flag) that propagates along the whole trace, so a value set at the edge is readable in a Kafka consumer three hops downstream. Profiles are the newest signal — continuous CPU / memory / lock sampling per service, answering which function is burning the CPU (Pyroscope, Parca, Grafana Phlare). The correlation bar at the bottom is the whole point: traces, metrics, logs, baggage and profiles all share trace_id + span_id + resource attributes (service.name, k8s.pod.name, deployment.version), so you can pivot — a metric spike leads to an exemplar trace, which leads to its logs, which leads to its CPU profile. OpenTelemetry is the vendor-neutral SDK and wire format for all five; traces/metrics/logs are GA, baggage is stable, profiling is the newest (the OTel profiling signal reached the ecosystem in 2024).

## [064] OBSERVABILITY · What each signal answers — and when to reach for it (sldId 319)

- Traces — 'where did the time go in this request, which hop failed?' Reach for it when debugging latency or a specific failed request. Stored in Tempo / Jaeger.
- Metrics — 'what is the aggregate rate / error / latency trend, is it getting worse?' Reach for it for dashboards, alerting, capacity. RED (Rate, Errors, Duration) for request-driven services; USE (Utilisation, Saturation, Errors) for resources. Stored in Prometheus / Mimir.
- Logs — 'what exactly happened in this component at this instant?' Reach for it for detail the trace doesn't carry. Structured (JSON), keyed by trace_id. Stored in Loki / ELK.
- Baggage — 'carry a value (tenant_id, user_tier) along the whole request so downstream services and their telemetry can use it.' Set once at the edge, readable everywhere downstream. W3C Baggage spec.
- Profiles — 'which function is burning CPU / allocating memory / holding locks, continuously, in production?' Reach for it for the latency the trace shows but doesn't explain. Pyroscope / Parca.
  - The discipline: emit traces + metrics + logs always; add baggage when downstream needs request-scoped context; add profiling when you have CPU/memory mysteries a trace can't resolve.

p. 52

> Walk each signal and the question it answers — the framing 'what question does this answer' is more useful to an engineer than 'what is this signal.' Traces are per-request; metrics are aggregate; logs are detail. The two newer ones deserve emphasis. Baggage is underused: most teams propagate trace context but never realise they can also propagate their own key-values (tenant, user tier, AB-test cohort) along the same mechanism, and then filter traces and logs by tenant. Profiling is the frontier: continuous profilers (Pyroscope, Parca, Grafana Phlare) run in production at low overhead and answer the 'the trace says this span took 200ms but why' question by showing the actual call stack burning the CPU. The sub-bullet is the practical guidance on which to adopt when.

## [065] OBSERVABILITY · Auto-injection vs. instrumentation — three distinct things (sldId 320)

- Manual instrumentation — you write the spans. activitySource.StartActivity(...), activity.SetTag(...), activity.AddEvent(...). Needed for business operations the libraries can't know about ('reserve_stock', 'score_fraud'). The most signal per line, the most effort.
- Auto-instrumentation — a library / agent wraps known frameworks for you. HTTP servers and clients, gRPC, JDBC / database drivers, Kafka, Redis — each becomes spans with zero code change. Covers the plumbing; misses your domain.
- Auto-injection — the platform puts the auto-instrumentation agent into the pod for you. The OpenTelemetry Operator watches for an annotation (instrumentation.opentelemetry.io/inject) and mutates the pod at admission — no agent in your image, no Dockerfile change, no redeploy of the app to add tracing.
- How they layer: auto-injection delivers the agent → the agent provides auto-instrumentation of frameworks → you add manual spans for business logic on top. All three coexist in the same trace.
  - Trade-off: auto-instrumentation is convenient but can be noisy (every framework call becomes a span) and slightly slower. Manual is precise but is work you own. Most teams: auto for the plumbing, manual for the domain, injection to roll it out fleet-wide.

p. 53

> Auto-injection, auto-instrumentation and manual instrumentation are three things people conflate. Manual: you call the tracer API yourself; necessary for domain operations. Auto-instrumentation: the OTel instrumentation libraries (or a language agent) wrap known frameworks: your HTTP handler, your DB driver, your Kafka client all emit spans without you touching them. Auto-injection: a Kubernetes-level mechanism; the OpenTelemetry Operator sees a pod annotation and injects the language agent + config as an init container / env vars at admission time, so you don't even put the agent in your image. Per-language specifics: Python: 'opentelemetry-instrument' wrapper or the operator injects it; instrumentation packages per library. Java/Quarkus: the OTel Java agent (-javaagent) auto-instruments everything; Quarkus also has build-time OTel extension. Spring: Micrometer Tracing + the OTel bridge, or the Java agent. .NET: OTel auto-instrumentation via the OpenTelemetry.AutoInstrumentation package or the operator's .NET injection; manual via System.Diagnostics.ActivitySource. The bold line is the mental model: injection delivers the agent, the agent instruments frameworks, you add manual spans on top — they layer into one trace.

## [066] OBSERVABILITY · Auto-instrument with OpenTelemetry .NET (sldId 321)

[chip] csharp · .NET 10 + OpenTelemetry.NET

```csharp
// Program.cs — OpenTelemetry .NET replaces Windows performance counters,
// ETW and the Event Log with one model.
builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order-service"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()        // every HTTP request → span
        .AddSource("order-service")            // your own ActivitySource
        .AddOtlpExporter())                    // endpoint and protocol from the env
    .WithMetrics(m => m
        .AddMeter("order-service")
        .AddOtlpExporter());
// compose: OTEL_EXPORTER_OTLP_ENDPOINT=http://lgtm:4318
//          OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
// custom business spans use the BCL ActivitySource (no extra dependency)
var activitySource = new ActivitySource("order-service");
app.MapPost("/orders", async (HttpContext ctx) =>
{
    // ...parse sku and quantity from the body
    using var reserveSpan = activitySource.StartActivity("reserve-stock");
    reserveSpan?.SetTag("sku", sku);
    var reply = await inventoryClient.ReserveStockAsync(          // gRPC; HttpClient
        new ReserveRequest { Sku = sku, Quantity = quantity });   // carries traceparent
    // ...insert the order, produce order.placed: trace_id rides every hop
});
```

ASP.NET Core requests become spans with no code; ActivitySource is the built-in API for your own spans. OTLP ships traces to Tempo, metrics to Mimir, logs to Loki.

p. 54

> OpenTelemetry .NET implements the OTel spec on top of types the runtime already has: System.Diagnostics.ActivitySource is the span API, built into the BCL since .NET 6, so starting a span needs no extra dependency.
>
> This is the running example's setup. AddAspNetCoreInstrumentation turns every HTTP request into a span; AddSource registers the service's own ActivitySource; AddOtlpExporter reads OTEL_EXPORTER_OTLP_ENDPOINT and OTEL_EXPORTER_OTLP_PROTOCOL from the environment, which compose sets to http://lgtm:4318 and http/protobuf. Add OpenTelemetry.Instrumentation.Http, GrpcNetClient or Runtime when you want outbound HTTP, gRPC client and GC or thread-pool signals as well.
>
> For business operations, declare one ActivitySource and wrap the work in using var span = source.StartActivity(...); the using stops the span when the scope exits. The gRPC call to inventory carries the W3C traceparent through HttpClient, so the inventory span lands in the same trace. For this audience this replaces Windows performance counters, ETW providers and the Event Log with one model that works the same in a container, in CI and on any cluster.

## [067] OBSERVABILITY · How correlation works — context propagation (sldId 322)

The trace context rides in-band with the request (W3C traceparent). The same trace_id at every hop is what stitches the story.

p. 55

> Demystify the magic word 'correlation.' It is not a backend join — it's the trace context physically travelling with the request, in-band, at every hop. The W3C traceparent header is the standard: version-traceid-parentspanid-flags. The trace_id (16 bytes) is constant across every hop of the request — that constancy is literally what stitches the distributed story into one trace. The span_id is new per operation, and each span records its parent span_id, which is how the backend rebuilds the tree. The flags byte carries the sampling decision (01 = sampled) so every hop honours the same decision. Alongside traceparent rides tracestate (vendor-specific) and baggage (your key-values). The transport differs per hop but the mechanism is identical: HTTP uses the traceparent header, gRPC uses metadata, Kafka uses message headers. The SDK injects the context on the way out and extracts it on the way in — automatically, which is why auto-instrumentation 'just works' across services. This propagated context is exactly why the same trace_id shows up on the trace waterfall, on every structured log line, and as an exemplar on your metrics — they all read it from the same in-band context.

## [068] OBSERVABILITY · Baggage in practice — carry request context downstream (sldId 323)

[chip] csharp · OpenTelemetry Baggage + Confluent.Kafka

```csharp
using OpenTelemetry;                        // Baggage: the W3C baggage API
using OpenTelemetry.Context.Propagation;
// set at the edge in middleware; the propagator writes the baggage header
app.Use(async (ctx, next) =>
{
    Baggage.SetBaggage("tenant_id",
        ctx.Request.Headers["X-Tenant"].FirstOrDefault() ?? "unknown");
    await next();
});
// Confluent.Kafka has no built-in propagation: the producer injects the context
// into the record headers and the consumer extracts it
var parent = Propagators.DefaultTextMapPropagator.Extract(default,
    cr.Message.Headers, ReadHeaders);      // ReadHeaders: UTF-8 values for a key
Baggage.Current = parent.Baggage;
using var span = source.StartActivity("process_shipment", ActivityKind.Consumer,
    parent.ActivityContext);
var tenant = Baggage.GetBaggage("tenant_id");
span?.SetTag("tenant_id", tenant);          // filterable in the trace UI
```

Baggage.SetBaggage at the edge; extract from the record headers and GetBaggage downstream. SetTag to filter traces.

p. 56

> Baggage in .NET goes through OpenTelemetry's Baggage API: Baggage.SetBaggage at the edge, and the default propagator writes the W3C baggage header on every outbound HTTP and gRPC call.
>
> Kafka is different: Confluent.Kafka has no built-in tracing, so the producer injects the trace context and baggage into the record headers and the consumer extracts them, as examples/05-event-driven/dotnet does (OrderService injects, ShippingConsumer and NotificationConsumer extract). After the extract, Baggage.Current carries the values and the consumer span is a child of the producer span.
>
> Baggage propagates on the wire; span attributes do not, but they are recorded and searchable. The idiom is to read the baggage value and set it as a tag on the local span so traces filter by tenant. Baggage travels to every downstream hop, so never put secrets or PII in it.

## [069] OBSERVABILITY · A single trace stitches the whole request (sldId 324)

One trace_id propagates from the edge REST call through gRPC, Kafka and the consumer — five services, one story.

p. 57

> This is what the instrumentation buys you, visually. One trace_id propagates from the edge REST POST through the gRPC ReserveStock call, onto the published order.placed event, and into the consumer that sends the notification. Five services, one readable waterfall. Point at the time axis: you can see exactly which span dominated latency. That same trace_id appears as an exemplar on your metrics and on every log line, so a latency alert is one click from the offending trace and its logs. This is what makes the choreographed, event-driven design from earlier sections debuggable.

## [070] OBSERVABILITY · Sampling — head vs. tail (sldId 325)

You can't store every trace at scale. Head decides at the start (cheap, blind); tail decides at the end (smart, costly).

p. 58

> The cost-control reality: at scale you cannot store every trace, so you sample. The key question is when the keep/drop decision is made. Head sampling decides at the start, in the SDK, before the trace even completes — typically 'keep 1 in N' (probabilistic) or 'keep N per second' (rate-limiting). It's cheap and low-overhead, but it is blind at decision time: it can't keep a trace because it errored or was slow, because it decides before knowing. Tail sampling decides at the end, in the Collector, after the whole trace has been seen — the Collector buffers spans, waits for the trace to complete, then applies rules: keep all errors, keep all traces over 500ms, keep rare routes, sample the boring successful ones at 1%. Tail is smart but costs memory (buffering in-flight traces) and CPU (the Collector does real work). The strategies, named: probabilistic (keep X%), rate-limiting (cap per second), parent-based (follow the upstream's decision so a trace isn't half-sampled), and tail rules (error / latency / attribute based). The common production setup is both: a parent-based head sample for a representative baseline, plus tail sampling at the Collector to guarantee every error and every slow trace is captured regardless of the baseline rate. Two rules to drill home: always sample by trace, not by span (a half-sampled trace is worse than no trace), and propagate the sampling flag (the 01 in traceparent) so every service agrees. Metrics and logs are usually not sampled the same way: metrics aggregate everything (you don't sample a counter), and logs are typically kept in full with retention limits or sampled on their own policy.

## [071] OBSERVABILITY · Choosing a sampling strategy (sldId 326)

- Probabilistic (head) — keep a fixed percentage (e.g. 10%). Simplest; predictable volume; blind to errors. Good baseline for high-traffic, low-stakes services.
- Rate-limiting (head) — keep at most N traces/sec per service. Protects your backend from traffic spikes; good when load is bursty.
- Parent-based (head) — honour the upstream service's sampling decision (carried in the traceparent flags). Essential in distributed systems: it stops a trace being sampled at service A but dropped at service B, which would give you broken half-traces.
- Tail-based (Collector) — buffer the whole trace, then keep by rule: all errors, all traces over a latency threshold, rare routes, plus a small % of the rest. The gold standard for keeping what matters, at the cost of Collector memory + CPU.
- Recommended production setup: parent-based head sampling at a modest baseline (1-10%) for representativeness, plus tail sampling at the Collector to guarantee every error and slow trace is kept.
  - Don't sample metrics the way you sample traces (metrics aggregate everything). Keep logs in full with retention limits, or sample them on their own policy keyed by trace_id so a kept trace keeps its logs.

p. 59

> The decision guide for sampling. Probabilistic is the simplest and the most common starting point — keep 10%, predictable volume. Rate-limiting is better when traffic is bursty because it caps absolute volume. Parent-based is non-negotiable in a distributed system: without it, service A samples a trace but service B independently drops it, and you get a broken trace with holes — worse than no trace. Tail-based sampling gives the most control: because the Collector sees the whole trace before deciding, it can guarantee you keep every error and every slow request, which are the traces you want during an incident. The cost is the Collector must buffer in-flight traces (memory) and evaluate rules (CPU), and it must see all spans of a trace (which constrains how you load-balance the Collector — use a trace-ID-aware load balancer). The recommended setup combines head (for a cheap representative baseline) and tail (for guaranteed capture of the interesting traces). The sub-bullet is the reminder: traces, metrics and logs are sampled differently — you never sample a metric counter, and logs typically follow their own retention or are sampled to match their parent trace.

## [072] OBSERVABILITY · Prove it with simple tools before you ship (sldId 327)

- curl / Postman — exercise REST contracts and inspect status codes, headers and pagination.
- hey — quick HTTP load to watch latency, error rate and the KEDA http-add-on scale the service.
- ghz — load-test gRPC endpoints and confirm timeouts and retries behave under pressure.
- GraphQL UI (GraphiQL) — explore the composed schema and watch the gateway fan out in Tempo.
- Kiali — read the live service-mesh topology, mTLS status and request flow during a load test.

p. 60

> Keep testing pragmatic: you don't need a heavy framework to validate this architecture. curl and Postman exercise REST contracts and check status codes and pagination. hey throws quick HTTP load so you can watch latency and error rate and see the KEDA http-add-on add replicas. ghz is the gRPC load tester: confirm your Istio timeouts and retries behave under pressure. The GraphQL IDE (Nitro / Banana Cake Pop, which HotChocolate serves at /graphql in dev) explores the composed schema and, with tracing on, shows the gateway fanning out in Tempo. Kiali visualizes the live mesh: topology, mTLS status and real-time request flow during a load test. The message: prove the behaviour with simple tools before you ship, not after an incident.

## [073] Security (sldId 328)

12

Defence in depth, in layers.

> Section 12 — security. The Anti-Patterns section that used to be 12 has shifted to 13. We organise this section around two ideas: the 4 C's of cloud-native security (concentric layers, each protecting what is inside it), and the seven patterns that you'll meet over and over in practice. The bias of this section: security is not a single product or a single team. It's a property of how the system is designed and run, owned at every layer. Each pattern here exists because no single layer is enough on its own.

## [074] SECURITY · The 4 C's of cloud-native security (sldId 329)

Cloud → Cluster → Container → Code. Concentric layers, each layer protects what is inside.

p. 61

> The mental model from the CNCF security paper. Four concentric layers of responsibility, each enforcing controls appropriate to its scope. Cloud is the outermost layer (IAM, VPC, KMS, audit logs, region selection), owned by the platform team or cloud admin. Cluster is the Kubernetes layer (RBAC, NetworkPolicy, Pod Security Standards, admission control), owned by platform/SRE. Container is the workload (minimal base images, non-root users, signed images, vulnerability scanning, secret mounting), owned jointly by app teams and platform. Code is the innermost layer (secure defaults, input validation, dependency scanning, secrets handling), owned by app teams. The point of the concentric metaphor: a weakness in any layer leaks into the inner ones. Strong code on a weak container is still vulnerable. Strong container on a weak cluster is still vulnerable. We design controls at all four. The 4 C's table lists each layer's controls and its owner.

## [075] SECURITY · The 4 C's — what each layer enforces, and who owns it (sldId 330)

- Cloud — IAM (principles of least privilege), VPC isolation, KMS for keys, audit logging, region & data-residency controls. Owner: platform / cloud admin.
- Cluster — Kubernetes RBAC, NetworkPolicy (default-deny + targeted allows), Pod Security Standards (restricted profile), admission control (OPA Gatekeeper / Kyverno), secret encryption at rest, etcd encryption. Owner: platform / SRE.
- Container — minimal base images (distroless, UBI-minimal), non-root users, read-only root filesystems, image signing (Sigstore / Cosign), vulnerability scanning (Trivy, Grype) on every build, secret mounting via projected volumes (never bake secrets into images). Owner: app team + platform.
- Code — secure defaults (parameterised queries, output encoding), input validation at the trust boundary, dependency scanning (Dependabot, Snyk, OSV-Scanner), secrets handling (no plaintext in source, no logging secrets), CSRF / SSRF / XXE awareness, threat modeling. Owner: app team.
- Cross-cutting: observability (audit who did what when), incident response runbooks, threat modeling per service, regular dependency updates.
  - The pattern: a control at the wrong layer is the most common source of false confidence. Network ACLs cannot save you from an SQL injection. Code-level input validation cannot save you from a compromised image. Defence in depth is real.

p. 62

> Walk each layer. The Cloud layer is where you control the perimeter and the identities and the keys; failures here often look like 'someone left a storage bucket open to the internet' or 'an over-permissive IAM role enabled lateral movement to another account.' The Cluster layer is the Kubernetes operating system for your workloads; failures look like 'the developer Pod could reach the database Pod' (no NetworkPolicy) or 'a privileged container was admitted' (no Pod Security Standards). The Container layer is about the image and runtime; failures look like 'a CVE in the base image' or 'the container ran as root and got out via a kernel exploit' or 'a secret was in the image.' Code is where most developer focus already lives. The sub-bullet is the take-home: a control at the wrong layer is false confidence. The pattern catalog holds seven patterns that show up across these four layers.

## [076] SECURITY · Seven patterns to know (sldId 331)

- Sidecar — move security concerns out of the app into a companion process. mTLS, JWT, audit, rate-limiting belong there.
- Valet Key — hand the client a short-lived signed token to access a resource directly. Less app proxying, less attack surface.
- Strangler Fig (for security modernisation) — encapsulate legacy auth behind an API gateway, replace pieces over time.
- Zero-Trust / Identity-Aware Proxy — every request authenticated and authorised. Perimeter trust is dead.
- Policy-as-Code — security gates declared in Git, evaluated at admission and at build. No human runs a checklist.
- Bulkhead — isolate resources so one failure (or compromise) cannot starve or cascade into others.
- Claim-Check — send a reference, not the payload. Keeps PII out of message bus history and limits the blast radius if a topic leaks.
  - The seven appear in different layers and combine. Each slide that follows shows the pattern, then implementation — platform config where it's mostly YAML, code where it's mostly code.

p. 63

> The roadmap for the next fourteen slides. These patterns span the 4 C's: Zero-Trust and Policy-as-Code are cluster-layer; Sidecar straddles cluster and container; Valet Key, Bulkhead, and Claim-Check are mostly code-layer; Strangler Fig is architecture-layer (modernisation). You'll see each pattern with a diagram explaining how it works, then either a YAML configuration block (for the platform-heavy patterns) or language-specific code (for the code-heavy patterns). Use the sub-bullet to set audience expectation that the section alternates between pattern-and-implementation pairs.

## [077] SECURITY · SIDECAR · Sidecar pattern — push security out of the app (sldId 332)

mTLS, JWT validation, rate limiting, audit logging — a companion process in the same Pod handles them all.

p. 64

> The sidecar pattern — a separate container running in the same Pod as the application, sharing localhost. The sidecar handles cross-cutting security concerns: terminates mTLS, validates JWTs, rate-limits, audits, enforces policy. The app receives only authenticated, authorised requests with trusted headers attached (X-Forwarded-Client-Cert, the validated JWT claims, the request ID). Why this matters: one security policy applied uniformly across every workload regardless of language. Same Envoy sidecar protects your Java app, your Python app, your Go app. App teams write business code, not crypto code. The sidecar is enforced by the platform (Istio injects them automatically) so it can't be disabled by accident. Examples in the field: Istio Envoy sidecars (the dominant choice), Linkerd2-proxy, OPA Sidecar for policy decisions, Cilium L7 with per-endpoint policy.

## [078] SECURITY · SIDECAR · Reading the sidecar's trusted headers (sldId 333)

- The sidecar handles mTLS, JWT validation, and policy decisions — the app trusts the headers the sidecar attaches and reads them as plain values.
- X-Forwarded-Client-Cert — the validated client identity from mTLS. Includes the SPIFFE ID (spiffe://cluster.local/ns/orders/sa/order-service) or the X.509 Subject. Set only by the sidecar; the app must reject requests that don't have it.
- JWT claims — the sidecar validates the signature, then passes the claims forward as a header or sets request.auth.claims via an envoy filter. The app reads sub, aud, scope, custom claims; it never re-validates the signature.
- Request ID — the sidecar attaches X-Request-Id for traceability. Log it; propagate it to downstream calls; correlate it with audit logs.
- Mode: only trust these headers when the sidecar is in front. In direct-to-Pod traffic (port-forward, debugging, mistakes), they could be spoofed. Use a NetworkPolicy to ensure traffic only enters via the sidecar's mTLS port.
  - Examples: Istio Envoy sidecars (auto-injected), Linkerd2-proxy, OPA Sidecar (policy decisions), Cilium L7 policy. License: all Apache 2.0.

p. 65

> The audience point: the sidecar pattern works only if the app uses the headers the sidecar attaches. The most common failure mode is an app that ignores X-Forwarded-Client-Cert and falls back to 'allow if you got here.' Make the headers required, not optional. The second-most-common failure mode is forgetting that traffic can sometimes bypass the sidecar (port-forward for debugging, host networking, direct pod-to-pod calls within the same node). NetworkPolicy is what closes that gap — only allow inbound traffic on the sidecar's mTLS port, never the app's container port directly. With both the sidecar and the NetworkPolicy, the app can fully trust the headers and become much simpler — no crypto code, no JWT parsing library, just header reads.

## [079] SECURITY · VALET KEY · Valet key pattern — short-lived signed token, direct access (sldId 334)

App mints a scoped, time-bound token; client uses it directly against the resource. App never proxies the bytes.

p. 66

> The valet key pattern: instead of streaming a large file through your application, the application mints a scoped, time-bound, operation-restricted token (a 'valet key') and the client uses it to interact directly with the storage system. Pros: dramatically less data through the application (memory, bandwidth, latency); no long-lived credentials at the client; no app-side credential to leak; the token can expire and be revoked. Cons: requires the storage side to validate tokens; the token's permissions and TTL must be carefully scoped — a leaked token still has its window. Every implementation has the same shape: sign the operation, the object key and the expiry with a key the storage side can check. Example 12 mints and verifies such a ticket in the service itself (HMAC-SHA256, an HS256 JWT in Go and C++), and most object stores, open-source ones included, accept signed URLs of the same shape. The code shows the pattern in the service's language.

## [080] SECURITY · VALET KEY · Valet key — scoped, time-bound, op-restricted (sldId 335)

[chip] csharp · ASP.NET Core 10 + HMACSHA256

```csharp
// Program.cs (excerpt), examples/12-security/dotnet: an HMAC-SHA256 valet key
var valetSecret = builder.Configuration.GetValue("VALET_SECRET",
    "demo-secret-do-not-use-in-prod");
app.MapPost("/valet-key", (HttpContext ctx) =>
{
    var resource = ctx.Request.Query["resource"].ToString();
    var operation = ctx.Request.Query["operation"].FirstOrDefault() ?? "GET";
    var expires = DateTimeOffset.UtcNow.ToUnixTimeSeconds() + 300;      // time-bound
    var payload = $"{resource}:{operation}:{expires}";                 // one object, one op
    var sig = ComputeHmac(valetSecret, payload);
    return Results.Ok(new { resource, operation, expires, token = sig });
});
// GET /verify-valet: 403 once expired, then a constant-time compare
    if (DateTimeOffset.UtcNow.ToUnixTimeSeconds() > expires)
        return Results.Json(new { detail = "expired valet key" }, statusCode: 403);
    var expected = ComputeHmac(valetSecret, $"{resource}:{operation}:{expires}");
    if (!CryptographicOperations.FixedTimeEquals(
            Encoding.UTF8.GetBytes(token), Encoding.UTF8.GetBytes(expected)))
        return Results.Json(new { detail = "invalid or expired valet key" }, statusCode: 403);
// ComputeHmac: HMACSHA256 keyed with the secret, Convert.ToHexStringLower of the hash
```

p. 67

> The handler mints a ticket that authorises one operation (GET or PUT) on one resource for 300 seconds; after that it is worthless. In Example 12 the ticket is an HMAC-SHA256 signature over resource:operation:expires, keyed with VALET_SECRET, read through IConfiguration (HMACSHA256). POST /valet-key returns the resource, the operation, the expiry and the token.
>
> The verifier (GET /verify-valet in the example, the storage gateway in a real system) rejects an expired ticket first, recomputes the signature and compares the two with CryptographicOperations.FixedTimeEquals, a constant-time comparison. A changed resource, operation or expiry gives a different signature, so any tampering is a 403.
>
> The application stays out of the data path: the client presents the ticket to the storage side directly. Most object stores, open-source ones included, accept signed URLs of the same shape: the method, the object key and the expiry signed into the URL. A user-scoped resource path also lets the store's policy restrict each user to their own prefix as defence in depth.

## [081] SECURITY · STRANGLER FIG · Strangler Fig for security modernisation (sldId 336)

- Use case: encapsulate legacy authentication (LDAP-only, HTTP Basic, hardcoded session cookies) behind a modern API gateway, then replace the legacy auth path one service at a time.
- Step 0: introduce the gateway in front of the monolith. Clients now hit the gateway, which forwards to the legacy auth. Day-zero behaviour unchanged.
- Step 1: the gateway terminates TLS, validates JWTs from a modern IdP (Keycloak, Dex), and translates to whatever the legacy expects; it speaks both languages.
- Step 2: per route, switch the gateway from 'forward legacy headers' to 'forward only the JWT claims to the new service'. Legacy auth is no longer in the path for that route.
- Step 3: when no routes still need legacy auth, remove it.
- Bounded blast radius: each route's auth migration is a config change in the gateway, reversible without a release.
  - See Appendix K for the general strangler-fig family (identify → move → redirect, with proxy, with shared database, with content-based routing). Same mechanics, applied to auth instead of business logic.

p. 68

> The strangler fig was covered as a general pattern in Appendix K — here it shows up specifically for security modernisation, which is a common need: most enterprises have legacy auth (LDAP-only, custom SSO, NTLM, hardcoded API keys) buried in critical systems, and a 'big bang' replacement is too risky. The gateway becomes the bilingual translator: it validates modern JWTs from your IdP at the edge and translates to whatever the legacy backend expects (X-Remote-User header, basic auth, NTLM, custom session cookie). Per route, you migrate when the new path is verified — if anything breaks, flip the gateway config back to forwarding legacy headers. The sub-bullet points to Appendix K for the full mechanics; this slide is the application of those mechanics to a specific security need.

## [082] SECURITY · ZERO-TRUST · Zero-trust / Identity-Aware Proxy (sldId 337)

Every request authenticated and authorised, on every hop. Perimeter trust is dead. SPIFFE inside, IAP at the edge.

p. 69

> The model: there is no trusted network. Every request, from any source, to any service, on every hop — authenticated and authorised. The old model (top of the diagram) was 'get inside the VPN, everything inside is trusted': once an attacker is in, they move laterally with little resistance. The new model (bottom): the user authenticates to an IAP (Identity-Aware Proxy) which evaluates identity, device posture, location, MFA. The IAP then forwards to a policy engine (OPA, Cedar) which returns an allow/deny per-request. The downstream service still authenticates the caller (mTLS + SPIFFE ID) and re-authorises against policy. Inside the cluster: mTLS via SPIFFE identity (every workload has an X.509 cert identifying its service account), AuthorizationPolicy per workload restricting which other workloads can call which endpoints. A breach in one service gives you nothing because the next call still has to prove identity and pass policy.

## [083] SECURITY · ZERO-TRUST · Implementing zero-trust (sldId 338)

- Edge (IAP): Pomerium or OAuth2 Proxy in front of an OIDC provider such as Keycloak — they terminate TLS, validate identity (OAuth/OIDC against your IdP), apply the route's access policy, then issue a JWT the downstream service sees in X-Forwarded-* headers.
- Inside the cluster (mTLS): Istio + SPIFFE assigns every workload an X.509 cert identifying its service account (spiffe://cluster.local/ns/orders/sa/order-service). Every service-to-service call is mutually authenticated automatically.
- Authorization: Istio AuthorizationPolicy declares 'order-service can call payment-service /charge but nothing else, only when carrying a valid customer JWT.' Per-workload, fine-grained, declarative.
- Policy decisions: OPA / Cedar evaluate context (user, time, device, target, action) and return allow/deny. Out-of-process so policy can change without redeploying every service.
- App-side discipline: read the validated peer identity from X-Forwarded-Client-Cert; never accept calls that arrive without it; log every authorization decision.
  - License notes: Istio, SPIFFE/SPIRE, OPA, Cedar — all open source (Apache 2.0 or similar). Pomerium (Apache 2.0) and OAuth2 Proxy (MIT) are open source too.

p. 70

> Concrete implementations to ground the model. The edge IAP is what your users hit — they authenticate against your IdP (Keycloak, or Dex federating an existing directory), the IAP issues a session, every request from then on carries identity. Inside the cluster, SPIFFE is the service-identity mechanism that makes mTLS work without manual cert management — it's what gives every Pod a verifiable identity. Istio's AuthorizationPolicy is the declarative layer on top: 'who can call what.' OPA / Cedar is the more flexible policy engine when your decision logic is complex (per-tenant, per-time-of-day, per-data-classification). The bold line is the app-side discipline: don't make these external policies redundant by accepting unauthenticated calls in your code; use the peer identity from the headers as a required input.

## [084] SECURITY · POLICY-AS-CODE · Policy-as-Code — security gates in Git (sldId 339)

OPA Gatekeeper / Kyverno enforce declarative policies at admission. CI runs the same policies pre-merge.

p. 71

> Security policies as code: declarative, version-controlled, tested, applied automatically. The flow on the diagram: a developer commits manifests; CI runs conftest or Kyverno against the manifests pre-merge (catches violations before they reach the cluster); on `kubectl apply` (or ArgoCD / Flux), the Kubernetes API server calls the admission controller (OPA Gatekeeper / Kyverno) which evaluates the ConstraintTemplate / ClusterPolicy against the incoming object. Non-conformant resources are rejected — they never become running Pods. The policy file lives in Git, reviewed like code, applied by the cluster. No human runs a checklist; consistency is enforced uniformly. Example policies: images must come from approved registries, no privileged containers, no host network, no host path mounts, all containers have resource limits, all images are signed.

## [085] SECURITY · POLICY-AS-CODE · OPA Gatekeeper ConstraintTemplate (Rego) (sldId 340)

[chip] yaml · OPA Gatekeeper (language-neutral)

```yaml
# ConstraintTemplate  —  reusable policy logic in Rego
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiresignedimages
spec:
    # ... crd: kind K8sRequireSignedImages, parameter allowedRegistries (string array)
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: |
      package k8srequiresignedimages
      violation[{"msg": msg}] {
        container := input.review.object.spec.containers[_]
        not startswith(container.image, input.parameters.allowedRegistries[_])
        msg := sprintf("image %v not from an allowed registry", [container.image])
      }
---
# Constraint  —  applies the policy to namespaces
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequireSignedImages
metadata: { name: must-be-signed }
spec:
  match:
    kinds: [{apiGroups: [""], kinds: ["Pod"]}]
    excludedNamespaces: ["kube-system", "gatekeeper-system"]
  parameters:
    allowedRegistries: ["registry.acme.com/", "quay.io/redhat/"]
```

p. 72

> The two-piece pattern: ConstraintTemplate defines the logic (in Rego, OPA's policy language), Constraint is the instance that applies the logic to specific resources with specific parameters. The Rego in violation[{msg}] reads as 'for every container in the Pod, if its image doesn't start with any of the allowed registries, emit a violation with this message.' Gatekeeper translates that into an admission webhook that rejects non-conformant Pods before they're scheduled. The Constraint binds the template to the kinds (Pods) and namespaces (everything except system namespaces), with the allowedRegistries list as the parameter. Lives in Git, applied via `kubectl apply` (or ArgoCD), versioned and reviewed like code. An equivalent Kyverno expression is more YAML-native if your team prefers it; Rego is more expressive for complex logic.

## [086] SECURITY · BULKHEAD · Bulkhead — isolate resources, bound the blast radius (sldId 341)

Per-tenant / per-call / per-priority pools. One tenant's storm cannot starve others. One compromise cannot cascade.

p. 73

> Bulkhead: borrowed from naval architecture, where watertight compartments stop one breach from sinking the ship. In software, you isolate resources (connection pools, thread pools, async semaphores, queues) by tenant, by call type, or by priority. The left side of the diagram (red) shows the default: one shared pool means a single tenant's traffic storm starves everyone else's. The right side: separate pools, each with its own bounded size. A storm from tenant A consumes tenant A's pool and rejects further A requests — tenants B and background workloads keep running. Why this matters for security as well as resilience: a compromised tenant or a compromised endpoint can be used to mount a denial-of-service against the shared system; bulkheads cap that to its own pool. Implementations: Resilience4j Bulkhead (JVM), Polly (.NET), asyncio.Semaphore (Python), Istio per-destination connection pools at the mesh layer.

## [087] SECURITY · BULKHEAD · Per-tenant bulkheads in ASP.NET Core (sldId 342)

[chip] csharp · ASP.NET Core 10 + SemaphoreSlim

```csharp
// Per-tenant bulkhead with a SemaphoreSlim; A's storm can't drain B's capacity
public class TenantBulkhead
{
    private readonly ConcurrentDictionary<string, SemaphoreSlim> _sems = new();
    public async Task<T> HandleAsync<T>(string tenant, Func<Task<T>> work)
    {
        var sem = _sems.GetOrAdd(tenant, _ => new SemaphoreSlim(5));   // 5 / tenant
        await sem.WaitAsync();               // blocks only this tenant when full
        try { return await work(); }
        finally { sem.Release(); }
    }
}
// Polly 8 alternative: ResiliencePipelineBuilder().AddConcurrencyLimiter(permitLimit,
// queueLimit) per tenant, from the Polly.RateLimiting package.
```

p. 74

> The bulkhead in its simplest .NET form: one SemaphoreSlim per tenant, created on first use. A tenant that floods the service fills only its own five slots and waits; other tenants keep their capacity.
>
> Polly 8 offers the same isolation as a pipeline strategy: AddConcurrencyLimiter (Polly.RateLimiting) with a permit limit and a queue limit, one pipeline per tenant, combined with a timeout so a slow downstream fails fast. Microsoft.Extensions.Http.Resilience can attach such pipelines to named HttpClients.
>
> At the platform layer, Istio connection-pool limits per destination complement these in-process limits.

## [088] SECURITY · CLAIM-CHECK · Claim-check — send a reference, not the payload (sldId 343)

Large or sensitive payload goes to a secure store; the message bus carries only an opaque token to fetch it.

p. 75

> The claim-check pattern: a producer puts the (large or sensitive) payload into a secure object store and publishes only a claim ticket (an opaque token plus a fetch URI) to the message bus. The consumer receives the ticket, fetches the payload from the store with the token. Two big security wins: PII never sits in Kafka's topic history (which is replicated, retained, and possibly visible to operators and other tools); and the token can expire and be revoked, while a Kafka message cannot. The pattern also has performance benefits (you don't push 50MB messages through the message bus), but this section frames it for security. Compare to the write-around caching pattern: same shape, different motivation. Where: any flow where sensitive payloads (health records, financial documents, customer PII) cross messaging infrastructure that shouldn't see them; any flow where payloads are large enough that the bus would be the bottleneck.

## [089] SECURITY · CLAIM-CHECK · Producer mints claim, consumer fetches payload (sldId 344)

[chip] csharp · ASP.NET Core 10 + Confluent.Kafka

```csharp
// claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key
var key = $"payloads/{orderId}";
await store.PutAsync(key, largePayload, encrypt: true);   // encrypted at rest, ACL'd
var expires = DateTimeOffset.UtcNow.ToUnixTimeSeconds() + 900;
var token = ComputeHmac(valetSecret, $"{key}:GET:{expires}");   // GET only, 15 minutes
await producer.ProduceAsync("order.documents",
    new Message<Null, string> { Value = JsonSerializer.Serialize(new {
        order_id = orderId,
        uri = $"https://objects.internal/{key}",
        resource = key, operation = "GET", expires, token,
    }) });                                             // claim only: small, routable
// consumer: read the claim, fetch the body out of band
var claim = JsonSerializer.Deserialize<Claim>(cr.Message.Value)!;
var body = await store.GetAsync(claim.Uri, claim.Token);  // PII never touched the topic
consumer.Commit(cr);
```

p. 76

> Two halves. The producer writes the payload to an encrypted object store under payloads/<order id>, mints a GET-only ticket for that key with Example 12's ComputeHmac (900 seconds), and publishes only a small claim (order id, URI and the ticket) to order.documents with Confluent.Kafka's ProduceAsync. The PII is never on Kafka's wire.
>
> The consumer decodes the claim, fetches the payload with the token, processes it, then commits the offset (at-least-once delivery, so the handler must be idempotent). The store verifies the ticket before it serves the object and logs every fetch with the principal, an audit trail plain Kafka does not give.
>
> Size the ticket's lifetime to the consumer's worst-case lag. No runnable example covers claim-check; store stands for any encrypted object store. Set a lifecycle rule that expires claims after the retention period, so a replayed message points at nothing.

## [090] SECURITY · Choosing the right pattern (sldId 345)

- Sidecar — when you want one security policy uniformly across every workload, regardless of language. Cost: an extra container per Pod (memory + startup time).
- Valet Key — when clients need direct access to a large or specific resource (file upload, image download). Cost: storage system must validate tokens (most do).
- Strangler Fig (auth) — when you have legacy authentication you can't change all at once. Cost: a gateway running translation logic during the transition.
- Zero-Trust / IAP — the default model for any system with users outside your immediate control. Cost: mTLS everywhere has real CPU and operational overhead.
- Policy-as-Code — always. Always. The cost of not having it (drift, inconsistency, forgotten review steps) is much higher than the cost of adopting OPA / Kyverno.
- Bulkhead — any multi-tenant system, any system with mixed-priority workloads. Cost: pools are extra moving parts to size and tune.
- Claim-Check — when payloads carry PII or are large enough to bloat the message bus. Cost: an extra fetch hop and the store-and-bus must agree on token semantics.
- Most production systems combine all of these, not as a checklist but as a decision per concern.

p. 77

> Close the section with the decision rules. The cost lines are there because every pattern is a trade. Sidecar costs a container per Pod (a few MB of memory, a couple hundred ms of startup); for most systems the security uniformity makes it worth that. Valet key requires storage-side validation: the store, or a small gateway in front of it, must check the signature, the operation and the expiry. Strangler fig (auth) is a deliberate transition strategy; the gateway running translation is the cost. Zero-trust / mTLS everywhere has real CPU overhead (TLS handshakes are not free) — mesh implementations like Istio amortise it well but it's not zero. Policy-as-code's cost is the upfront investment in writing policies; the ongoing cost is near zero. Bulkheads are extra moving parts to tune. Claim-check adds a hop. The bold line is the take-home: production systems combine all seven, chosen per concern, not applied as a one-size-fits-all checklist.

## [091] SECURITY · Take-aways and references (sldId 346)

- Defence in depth across the 4 C's: cloud, cluster, container, code. A control at the wrong layer is false confidence.
- Identity is the new perimeter. mTLS + SPIFFE inside; IAP / OIDC at the edge. Every request authenticated and authorised, on every hop.
- Policy in Git, enforced by the cluster. OPA Gatekeeper or Kyverno at admission; conftest in CI for early feedback.
- PII never crosses your message bus in cleartext. Claim-check or end-to-end encrypt.
- Isolate by tenant, by call, by priority. Bulkheads bound the blast radius of both incidents and outages.
  - References: NIST SP 800-204A (microservices security); CNCF Cloud Native Security Whitepaper; OWASP API Security Top 10; the OpenSSF SLSA framework; Istio AuthorizationPolicy docs; OPA Gatekeeper library; OWASP Microservices Security Cheat Sheet.
  - Open-source pillars: Istio (Apache 2.0), SPIFFE/SPIRE (Apache 2.0), OPA / Gatekeeper (Apache 2.0), Kyverno (Apache 2.0), Sigstore (Apache 2.0), Falco (Apache 2.0), Trivy (Apache 2.0).

p. 78

> Close with the take-aways the audience should remember. Defence in depth across the 4 C's is the philosophical anchor. Identity-as-perimeter is the operational anchor. Policy-in-Git is the automation anchor. The PII-never-in-cleartext and bulkhead lines are the specific applications. The reference list is what you'd recommend for further reading — NIST 800-204A is the canonical microservices security paper; CNCF's Cloud Native Security Whitepaper organises the same material; OWASP API Top 10 is the application-layer reference; SLSA covers supply-chain security (signing, provenance, build integrity). The open-source list emphasises that the entire security stack is buildable with Apache 2.0 components.

## [092] Anti-Patterns (sldId 347)

13

Most outages re-couple what you separated.

> The final main section, and the most memorable framing of the whole talk: nearly every cloud-native failure is coupling sneaking back in. You did the work to separate things; entropy and deadlines pull them back together. This section names the specific ways that happens and gives heuristics to catch it early.

## [093] ANTI-PATTERNS · How cloud-native API systems go wrong (sldId 348)

Each anti-pattern reintroduces the coupling the architecture worked to remove.

p. 79

> Walk the grid briefly — most of these are callbacks to earlier sections. Distributed monolith (services that must deploy together), shared database (two services on one table), chatty calls (deep synchronous chains), no contract/leaky internal models (DB rows as the public API), missing observability (debugging by guesswork), retry storms (no backoff). The unifying diagnosis is on screen: each one reintroduces the coupling the architecture worked to remove. If you only remember one slide for code review, it's this one. The anti-pattern heuristics turn these into positive rules.

## [094] ANTI-PATTERNS · The heuristics that keep you out of them (sldId 349)

- If two services must deploy together, they are one service — merge them or fix the contract.
- One writer per dataset; everyone else reads through the API or subscribes to its events.
- Push aggregation to a gateway/BFF; forbid service-to-service call chains deeper than one hop.
- No contract in the registry, no merge — and every retry has a timeout and a bound.
- If you can't trace it, you can't run it: observability is a launch requirement, not a follow-up.

p. 80

> These are the five tests to apply in design and code review. (1) If two services must deploy together, they are one service: merge them or fix the contract. (2) One writer per dataset; everyone else reads through the API or subscribes to events — no shared tables. (3) Push aggregation to a gateway or BFF and forbid synchronous call chains deeper than one hop. (4) No contract in the registry, no merge — and every retry has a timeout and a bound. (5) If you can't trace it, you can't run it — observability is a launch requirement, not a follow-up. Offer these as a checklist the team can literally paste into a PR template.

## [095] IN CLOSING · The whole talk, in five lines (sldId 350)

- Cloud-native is a set of properties; the platform exists to make them the default.
- Match each interaction to its style (REST, gRPC, GraphQL or async) and compose at the edge.
- Own your data; share it as contracts and facts, never as shared tables.
- Make the contract a governed artifact: registry to enforce it, metadata to find it, observability to run it.
- Every anti-pattern is coupling sneaking back in. Design to keep things apart.

p. 81

> The recap — read these five as the entire talk compressed. If the audience remembers nothing else: cloud-native is properties not tools; match the protocol to the interaction and compose at the edge; own your data and share it as contracts and facts; make the contract a governed artifact (registry, metadata, observability); and watch for coupling sneaking back in. Pause here before References and Q&A. If it's the long-form session, this is the natural point to say 'and now the appendices go deeper on four things people always ask about' and continue.

## [096] REFERENCES · The shoulders this stands on (sldId 351)

- Cloud-Native Patterns and Architecture
- Building Microservices, 2nd ed. — Sam Newman (O'Reilly)
- Designing Data-Intensive Applications, 2nd ed. — Martin Kleppmann & Chris Riccomini (O'Reilly)
- Building Event-Driven Microservices — Adam Bellemare (O'Reilly)
- Cloud Native Patterns — Cornelia Davis (Manning)
- Patterns of Distributed Systems — Unmesh Joshi (Addison-Wesley)
- Architecture Modernization — Nick Tune & Jean-Georges Perrin (Manning)
- Cloud Native Anti-Patterns — Gerald Bachlmayr
- Principles of Web API Design — James Higginbotham (Addison-Wesley)
- Patterns for API Design — Olaf Zimmermann et al. (Addison-Wesley)
- API Design Patterns — JJ Geewax (Manning)
- Learning Domain-Driven Design — Vlad Khononov (O'Reilly)
- Balancing Coupling in Software Design — Vlad Khononov (Addison-Wesley)
- ASP.NET Core 10 reference (learn.microsoft.com/aspnet/core), OpenTelemetry .NET, Temporal .NET SDK (docs.temporal.io/dev-guide/dotnet), Confluent.Kafka, HotChocolate, Streamiz.Kafka.Net, EF Core and Debezium docs — for the runtime specifics

p. 82

> The reading list this talk stands on. Call out a couple of pairings: Newman's Building Microservices for the boundaries and integration story; Kleppmann's Designing Data-Intensive Applications for the data and consistency foundations behind the outbox and saga; Bellemare for the event-driven backbone; and the API-design trio (Higginbotham, Zimmermann et al., Geewax) for contract and versioning depth. The architecture books are language-agnostic — they apply whether you build on .NET, Java, Go, or anything else. The ASP.NET Core reference docs, OpenTelemetry .NET guides, Temporal .NET SDK docs and Debezium docs are the practical references for the runtime specifics shown in the code. The slides and these references are enough to build the system, not only to discuss it.

## [097] Thank you (sldId 352)

Questions?

> End of the main talk. Thank the audience and open for questions. The appendices are deep-dive backup material: pull them up on demand during Q&A, or work through them if you're running the full-length session. They cover the questions that always come up: how the three protocols differ, how to version each one, how to run WebSockets on Kubernetes, and the hard parts of saga state and compensation.

## [098] REFERENCE · Glossary of acronyms (1 of 2) — protocols, data, events (sldId 353)

- Protocols & APIs — REST (Representational State Transfer); RPC (Remote Procedure Call); gRPC (Google's RPC framework, over HTTP/2 + Protobuf); HTTP (HyperText Transfer Protocol); TLS / mTLS (Transport Layer Security / mutual TLS, where both peers present certificates); SSE (Server-Sent Events); BFF (Backend-For-Frontend); SDK (Software Development Kit); API (Application Programming Interface).
- Messaging & integration — AMQP (Advanced Message Queuing Protocol); ESB (Enterprise Service Bus); DLQ (Dead-Letter Queue, where un-processable messages go); SerDe (Serializer / Deserializer); pub/sub (publish-subscribe).
- Data & persistence — CQRS (Command Query Responsibility Segregation); CDC (Change Data Capture); WAL (Write-Ahead Log, the DB's commit-ordered durable log); ACID (Atomicity, Consistency, Isolation, Durability); TTL (Time-To-Live: how long a cached key lives before expiring); LRU (Least Recently Used, a cache eviction policy); SETEX (the Redis "SET with EXpiry" command, which sets a key and its TTL atomically); ORM (Object-Relational Mapping); EF Core (Entity Framework Core, .NET's ORM); LINQ (Language-Integrated Query).
- Domain modelling & flow — DDD (Domain-Driven Design); OHS (Open Host Service: a published, stable interface a context offers others); ACL (Anti-Corruption Layer in DDD, which translates between models; ACL also means Access Control List in security); Saga (not an acronym: a sequence of local transactions with compensating actions).

p. 83

> Glossary part 1, the protocol/data/event vocabulary. Call out the ones most likely to trip people up: gRPC is recursively 'gRPC Remote Procedure Call' but practically it's Google's high-performance RPC over HTTP/2 with Protocol Buffers. mTLS (mutual TLS) is the one people often gloss — ordinary TLS authenticates the server to the client; mutual TLS also authenticates the client to the server, which is the basis of zero-trust service identity. The data row has the SETEX and TTL the audience asked about explicitly: TTL is the expiry duration on a cached key; SETEX is the Redis command that sets a value and its TTL in one atomic operation (SETEX key seconds value). LRU is the eviction policy that drops the least-recently-touched key when the cache is full. CDC and WAL go together — CDC tails the WAL. Call out the ACL ambiguity: in the DDD/data sections ACL means Anti-Corruption Layer; in the security section it means Access Control List.

## [099] REFERENCE · Glossary of acronyms (2 of 2) — platform, security, telemetry (sldId 354)

- Kubernetes & cloud — K8s (Kubernetes); RBAC (Role-Based Access Control); HPA (Horizontal Pod Autoscaler); KEDA (Kubernetes Event-Driven Autoscaling); PSS (Pod Security Standards); CRD (Custom Resource Definition); IAM (Identity & Access Management); KMS (Key Management Service); VPC (Virtual Private Cloud); CNI (Container Network Interface).
- Identity & security — SPIFFE (Secure Production Identity Framework For Everyone); SPIRE (the SPIFFE Runtime Environment); OPA (Open Policy Agent); IAP (Identity-Aware Proxy); JWT (JSON Web Token); OIDC (OpenID Connect); OAuth (Open Authorization); MFA (Multi-Factor Authentication); PII (Personally Identifiable Information); SLSA (Supply-chain Levels for Software Artifacts); CVE (Common Vulnerabilities & Exposures); SBOM (Software Bill of Materials).
- Observability — OTel (OpenTelemetry); RED (Rate, Errors, Duration: the request-driven metrics method); USE (Utilisation, Saturation, Errors: the resource metrics method); MDC (Mapped Diagnostic Context, per-thread log context); LGTM (Loki, Grafana, Tempo, Mimir); SLO / SLI / SLA (Service-Level Objective / Indicator / Agreement); p99 (99th-percentile latency).
- Runtime & build — CLR (Common Language Runtime, .NET's execution engine); BCL (Base Class Library); JIT (Just-In-Time compilation); AOT (Ahead-Of-Time / Native AOT compilation); GC (Garbage Collection); DI (Dependency Injection); DTO (Data Transfer Object); LINQ (Language-Integrated Query).

p. 84

> Glossary part 2, the platform/security/observability vocabulary. The Kubernetes row: HPA scales on CPU/memory, KEDA scales on event sources (queue depth, Kafka lag, HTTP rate) — the distinction matters in the autoscaling discussion. PSS (Pod Security Standards) replaced the deprecated PodSecurityPolicy. The security row has the terms from section 12: SPIFFE/SPIRE give workloads cryptographic identities for mTLS; OPA is the policy engine behind policy-as-code; IAP is the zero-trust edge proxy; JWT/OIDC/OAuth are the token/identity standards; SLSA/CVE/SBOM are supply-chain security. The observability row has RED and USE, the two metrics methods worth memorising: RED (Rate, Errors, Duration) for services, USE (Utilisation, Saturation, Errors) for resources. p99 means the 99th-percentile latency — 99% of requests are faster than this; it's what you alert on, not the average. The runtime row is tailored to this deck's language.

## [100] Appendix A · Protocols in Depth (sldId 355)

A

REST, gRPC and GraphQL: how they differ.

> Appendix A. This is the deep dive behind the 'pick the protocol' slide from section 2. We compare the three on three axes: the mental model each imposes, how they handle fetching and round trips, and what travels on the wire. By the end the audience should be able to defend a protocol choice on technical grounds, not fashion.

## [101] APPENDIX A · PROTOCOLS · Three paradigms and their mental models (sldId 356)

REST models resources, gRPC models procedures, GraphQL models a typed graph — the same intent, three shapes.

p. 85

> Start with the mental model, because it drives everything else. REST is resource-oriented: nouns and HTTP verbs, you transfer representations of state. gRPC is procedure-oriented: you call typed methods, it's behaviour not state, and the .proto is the contract. GraphQL is graph-oriented: one typed schema the client traverses, picking exactly the fields it wants. The same place_order intent takes three different shapes. Most arguments about 'which is best' are arguments about which mental model fits the problem, and the answer often differs per interaction.

## [102] APPENDIX A · PROTOCOLS · Over-fetching, under-fetching and round trips (sldId 357)

REST trades round trips or bespoke endpoints for simplicity; GraphQL shapes one response; gRPC is a typed call.

p. 86

> This is the practical difference clients feel. With REST you often need several round trips (order, then its items, then stock, then shipping) or you build a bespoke aggregate endpoint — and you still get fixed payload shapes that over- or under-fetch. GraphQL collapses that into one tailored query where the client names the fields, so no over- or under-fetching and the client controls the cost. gRPC is a single typed, binary call with a fixed reply shape: no field selection, but the fastest of the three. The trade: GraphQL gives clients flexibility at the cost of gateway complexity; gRPC gives speed at the cost of rigidity; REST gives reach and simplicity at the cost of round trips.

## [103] APPENDIX A · PROTOCOLS · The wire: transport, encoding and streaming (sldId 358)

Reach and caching, or raw speed, or client-shaped responses — choose on the wire properties you need.

p. 87

> What travels on the wire, and why it constrains your choice. REST: HTTP/1.1 or /2, JSON text, request/response, cacheable via standard HTTP, browser-native — maximum reach. gRPC: HTTP/2 only, protobuf binary, full uni- and bidirectional streaming, no HTTP caching, and it needs grpc-web to work from a browser. GraphQL: HTTP POST to a single URL, JSON, request/response plus subscriptions, caching is application-level (not HTTP), browser-native. The decision rule: if you need broad reach and HTTP caching, REST; if you need raw speed and streaming between services you control, gRPC; if you need client-shaped responses over many sources, GraphQL.

## [104] APPENDIX A · PROTOCOLS · Choosing between them in practice (sldId 359)

- Public or partner-facing, browser or third-party clients, caching matters → REST.
- Internal service-to-service, low latency, high call volume, streaming → gRPC.
- Aggregating many back-ends for varied clients that each want different fields → GraphQL at the gateway.
- A fact that many consumers react to, decoupled in time → none of these; emit an event.
- Real systems use all four; standardizing on one wire for everything is itself an anti-pattern.

p. 88

> The decision guide. Public/partner/browser with caching → REST. Internal, hot, streaming → gRPC. Client-driven aggregation across back-ends → GraphQL at the gateway. A fact many consumers react to → don't make it a call at all, emit an event. The bold closing point ties back to the whole talk: forcing one protocol everywhere ('we're a gRPC shop', 'everything is GraphQL') is itself an anti-pattern, because you pay gRPC's browser tax or GraphQL's gateway complexity where a plain cacheable GET would have done.

## [105] APPENDIX A · PROTOCOLS · Common mistakes with each (sldId 360)

- REST: verbs in URLs (/createOrder), 200-for-everything, offset pagination, and ignoring cache headers.
- gRPC: exposing it directly to browsers without grpc-web; treating it as REST-with-protobuf and ignoring streaming.
- GraphQL: the N+1 resolver explosion; no query depth/complexity limits; using it for simple single-resource reads.
- All three: leaking internal database models straight onto the wire, so you can never evolve them.
- Async: using a queue when you needed a log (no replay), or a request when you needed a fact.

p. 89

> The failure modes, drawn from real review comments. REST: verbs in URLs, returning 200 with an error body, offset pagination that breaks under load, and throwing away free HTTP caching. gRPC: trying to call it straight from a browser without grpc-web, or using it as 'REST with protobuf' and never touching its streaming superpower. GraphQL: the classic N+1 resolver explosion (fix with DataLoader batching), no depth or complexity limits so a malicious query melts the gateway, and reaching for it when a plain GET would do. The universal one is the last bold-adjacent: leaking your database schema onto the wire kills your ability to evolve — the same leaky-internal-models anti-pattern from section 12.

## [106] Appendix B · Versioning & Evolution (sldId 361)

B

REST vs RESTful, proto breaking changes, GraphQL evolution.

> Appendix B answers the question every team fights about: how do we version this without breaking everyone? The answer differs sharply by protocol. REST has several strategies with real trade-offs; gRPC has precise wire-compatibility rules; GraphQL rejects versioning entirely in favour of evolution. We'll see each, with code.

## [107] APPENDIX B · VERSIONING · Four ways to version a REST API (sldId 362)

URI versioning is common and visible; media-type versioning keeps URLs stable — the more RESTful choice.

p. 90

> REST has four strategies, ordered from coarse to fine. URI path (/v2/orders): visible, trivial to route, but couples the version to the URL and breaks REST's idea that a URL identifies a resource, not a representation. Query param: simple to default but muddies caches. Custom header: keeps URLs clean but is invisible and often forgotten. Media-type versioning (Accept: application/vnd.acme.order.v2+json): content negotiation keeps the URL stable as the identifier of the resource, and the representation is what's versioned. This is the RESTful approach. In practice, URI versioning is the most common because it's pragmatic; media-type is the most correct. Know which you're choosing and why. The media-type versioning code shows how.

## [108] APPENDIX B · VERSIONING · Media-type versioning with ASP.NET Core (sldId 363)

[chip] csharp · .NET 10 + Asp.Versioning

```csharp
// Asp.Versioning.Http (MIT, .NET Foundation): media-type, URI segment,
// query string or header versioning, picked centrally.
builder.Services.AddApiVersioning(o =>
{
    o.ApiVersionReader = new MediaTypeApiVersionReaderBuilder()
        .Template("application/vnd.acme.order.v{version}+json")   // Accept header
        .Build();
    o.DefaultApiVersion = new ApiVersion(1, 0);
    o.AssumeDefaultVersionWhenUnspecified = true;
});
// one resource URL, /orders/{id}; the representation is versioned
var orders = app.NewVersionedApi("Orders").MapGroup("/orders")
    .HasApiVersion(1, 0).HasApiVersion(2, 0);
orders.MapGet("/{id}", (string id, IOrderService svc) => OrderV2.From(svc.Get(id)))
      .MapToApiVersion(2, 0);
orders.MapGet("/{id}", (string id, IOrderService svc) => OrderV1.From(svc.Get(id)))
      .MapToApiVersion(1, 0);                     // the default for old clients
public record OrderV1(string Id, double Total);
public record OrderV2(string Id, double Total, string Currency);
```

The resource URL is stable; the representation is negotiated. New clients ask for v2; old clients keep getting v1.

p. 91

> ASP.NET Core versioning lives in Asp.Versioning.Http (.NET Foundation). The reader is pluggable: MediaTypeApiVersionReaderBuilder with a template reads the version from the Accept media type (application/vnd.acme.order.v2+json), the most RESTful choice; UrlSegment, QueryString and Header readers swap in without changing handlers.
>
> There is one URL for the order resource, and it never changes. NewVersionedApi declares the versions the group supports, and MapToApiVersion binds each handler to one. New clients ask for the v2 media type and get the currency field; old clients send the default and get v1, unaffected. Contrast with /v2/orders, which gives one resource two URLs.
>
> OrderV1 and OrderV2 are explicit representation DTOs: the wire contract stays decoupled from the domain entity, a discipline WCF DataContracts taught, applied to HTTP.

## [109] APPENDIX B · VERSIONING · gRPC / protobuf: what is a breaking change (sldId 364)

Field numbers are the contract — names and order are not. Never reuse or renumber a field.

p. 92

> gRPC's rules are precise because the wire format is positional. Safe, wire-compatible changes: add a field with a new number, add an rpc method, add an enum value, rename a field (the number is what matters, not the name), mark fields deprecated, and reserve removed tags. Breaking changes: change a field's number or type, reuse a removed number, remove a field without reserving its tag, rename or move a service or package, or change the request/response message type. The one people miss is on screen at the bottom: changing a method between unary and any streaming mode changes the HTTP/2 framing and is always breaking. The discipline: field numbers are forever; never reuse or renumber. Code shows safe evolution next.

## [110] APPENDIX B · VERSIONING · Evolving a .proto safely (sldId 365)

[chip] protobuf

```protobuf
syntax = "proto3";
message Order {
  string id     = 1;
  string sku    = 2;
  int32  qty    = 3;
  reserved 4;                 // tag 4 once held 'notes' — never reuse it
  reserved "notes";
  string currency = 5;        // safe: brand-new field, new tag number
  PaymentState state = 6;     // safe: new field; old clients ignore it
}
enum PaymentState { PENDING = 0; PAID = 1; REFUNDED = 2; }  // 0 must exist
// breaking (don't): qty -> int64, or moving 'sku' to tag 7, or reusing tag 4
```

Add with new tags, reserve what you remove, and never change an existing field's number or type.

p. 93

> Walk the safe pattern. We removed an old 'notes' field, so we reserve both its tag number (4) and its name permanently: nobody can reuse them and silently corrupt old data on the wire. We add currency and state as brand-new fields with new tag numbers; old clients ignore unknown fields and new clients read them, which gives forward and backward compatibility without extra work. Note the enum must keep a zero value as its default. The comment at the bottom lists the things that would break the wire: widening qty's type, moving an existing field to a new tag, or reusing a reserved tag. Apicurio's compatibility check (section 9) enforces exactly these rules in CI.

## [111] APPENDIX B · VERSIONING · GraphQL versions by evolution, not by number (sldId 366)

There is no /v2 in GraphQL: add fields, mark old ones @deprecated, watch usage, then retire.

p. 94

> GraphQL takes a completely different stance: there are no versions. There's one schema that evolves continuously. The lifecycle on screen: add new fields and types (additive is always safe, because existing queries did not ask for the new field); mark superseded fields @deprecated with a reason and a pointer to the replacement, while still serving them; watch field-level usage metrics to see who still queries the old field and drive their migration; and retire, the single breaking step, only once usage hits zero. The insight: GraphQL pushes you toward data-driven deprecation instead of big-bang version cutovers. Code shows the @deprecated directive next.

## [112] APPENDIX B · VERSIONING · Deprecating a field in HotChocolate (sldId 367)

[chip] csharp + graphql · .NET 10 + HotChocolate

```csharp+graphql
// HotChocolate — [GraphQLDeprecated] maps to the SDL @deprecated directive
public class Order
{
    public string Id { get; init; }
    [GraphQLDeprecated("Use totalMinor (integer cents) instead.")]
    public double Total { get; init; }           // still served; shows in introspection
    public int TotalMinor => (int)(Total * 100); // the replacement, added additively
}
// Schema-first alternative, if your team prefers .graphql files:
//   type Order {
//     id: ID!
//     total: Float @deprecated(reason: "Use totalMinor (integer cents) instead.")
//     totalMinor: Int!
//   }
// Per-field usage counters (a diagnostic event listener exporting to OpenTelemetry)
// show when 'total' has zero callers. Only then remove it. No /v2 endpoint.
```

Additive change plus [GraphQLDeprecated] plus usage metrics replaces versioning entirely.

p. 95

> The mechanics in HotChocolate. Code-first is the dominant style in .NET GraphQL: you write a C# record (or class) and HotChocolate infers the schema from your types. We add TotalMinor additively and mark the old Total field with [GraphQLDeprecated("reason")] — the attribute maps directly to GraphQL's native @deprecated schema directive. If your team prefers schema-first, the .graphql file syntax works identically and the C# resolvers bind to it. The field keeps working and nothing breaks, but the deprecation shows up in introspection, in any IDE plugin that reads the schema, and in HotChocolate's bundled GraphQL IDE (Nitro, formerly Banana Cake Pop) at /graphql. The crucial operational piece is the comment: you instrument field-level usage (HotChocolate has IDiagnosticEventListener hooks; pair with OpenTelemetry to push per-field counters), and you only remove Total when its usage drops to zero. That's the whole GraphQL philosophy — evolution governed by data, with the breaking removal deferred until provably safe. Each protocol answers the same problem differently.

## [113] APPENDIX B · VERSIONING · Principles that cut across all three (sldId 368)

- Additive change is always safe; removal and mutation are where you break people.
- Make compatibility mechanical — the registry's BACKWARD/FORWARD/FULL rules, checked in CI, not by reviewers' memory.
- Never break silently: deprecate with a reason, a replacement and a sunset date; measure who's still on the old version.
- Run old and new in parallel and migrate consumers before retiring — retirement is the only step that can break.
- Version data the same way you version APIs: event schemas in the registry follow the identical rules.

p. 96

> Step back to the universal principles, because the protocol-specific rules all rhyme. Additive change is safe; removal and mutation break people — so design to add. Make compatibility mechanical: the registry's rules checked in CI, never a reviewer remembering. Never break silently: deprecate with a reason, a replacement, a sunset date, and measure who's still on the old thing. Run old and new in parallel and migrate before you retire, because retirement is the only inherently breaking move. And the bold line that connects this back to the event-driven section: your event schemas version by exactly the same rules — the registry treats an Avro schema and an OpenAPI spec identically. Versioning data and versioning APIs are the same discipline.

## [114] Appendix C · WebSockets at Scale (sldId 369)

C

Raw WebSockets, pod pinning, the backplane, binary framing, reconnection — and where Blazor fits.

> Appendix C covers the protocol left out of the main interaction-styles discussion, because it behaves so differently on Kubernetes. WebSockets are long-lived, stateful and pinned to a Pod: the opposite of the stateless request model the platform assumes.
>
> We build an endpoint with raw ASP.NET Core WebSockets, as the running example does, see why it fights scaling, fix it with a Redis backplane, make it fast and versioned with protobuf frames, and make it survivable with reconnection. Then Blazor: Blazor Server sits on the SignalR pinning side of this discussion and Blazor WebAssembly on the other; both run on Kubernetes as plain ASP.NET Core Pods. SignalR itself is the subject of Appendix Q.

## [115] APPENDIX C · WEBSOCKETS · A WebSocket endpoint in ASP.NET Core (sldId 370)

[chip] csharp · ASP.NET Core 10 WebSockets

```csharp
// raw ASP.NET Core WebSockets, as in the running example (no SignalR)
app.UseWebSockets();
app.Map("/ws/{clientId}", async (HttpContext ctx, string clientId) =>
{
    if (!ctx.WebSockets.IsWebSocketRequest) { ctx.Response.StatusCode = 400; return; }
    var ws = await ctx.WebSockets.AcceptWebSocketAsync();
    clients[clientId] = ws;                             // per-pod state
    var buf = new byte[4096];
    while (ws.State == WebSocketState.Open)
    {
        var result = await ws.ReceiveAsync(buf, CancellationToken.None);
        if (result.MessageType == WebSocketMessageType.Close) break;
        var msg = Encoding.UTF8.GetString(buf, 0, result.Count);
        await Broadcast(msg);                           // fan-out to this pod's clients
    }
    clients.TryRemove(clientId, out _);
});
```

Raw ASP.NET Core WebSockets, as in the running example. The clients map lives in this Pod: that single fact is the scaling problem.

p. 97

> The running example's endpoint uses raw ASP.NET Core WebSockets: UseWebSockets, a mapped route, AcceptWebSocketAsync, then a receive loop. No SignalR, so any client can connect and verify.sh can test it with a plain WebSocket client.
>
> Point at the clients dictionary: it lives in this Pod's memory. The connection, the client id and the fan-out all stay on one Pod, and that single fact is the scaling problem a Redis backplane solves, which the example also runs.
>
> SignalR (Appendix Q) wraps the same transport with hubs, groups, reconnection and serialization; it is the choice when server and clients are .NET. The per-Pod state problem is the same either way.

## [116] APPENDIX C · WEBSOCKETS · Why WebSockets fight Kubernetes scaling (sldId 371)

A long-lived connection pins to one pod; new pods get no existing connections and scale-down drops them.

p. 98

> Here's the collision with Kubernetes. A WebSocket connection, once established through the load balancer, is pinned to one pod for its entire lifetime. Two problems follow. Scale-up: the HPA or KEDA adds ws-pod-3, but it gets zero existing connections, only new ones, so a hot pod stays hot and the new pod sits idle; scaling doesn't relieve the load you already have. Scale-down and rollouts: terminating a pod severs every connection it was holding, so a routine deploy disconnects thousands of users at once. Stateless HTTP shrugs both off; WebSockets don't. The fix is to stop making any single pod the home of a conversation, which is the backplane, rather than to avoid scaling.

## [117] APPENDIX C · WEBSOCKETS · The scaling problem, stated precisely (sldId 372)

- Pinning: a connection is bound to one pod; the LB can't move it without dropping it.
- Uneven load: new replicas only receive new connections, so existing hotspots persist.
- Rollouts hurt: every deploy or scale-down severs the connections on the affected pods.
- Cross-pod delivery: to push to user X you must reach whichever pod holds X — which you don't track.
- Connection limits & memory: each socket is held-open state; pods cap out on file descriptors, not CPU.

p. 99

> Name the five distinct problems so the audience can recognize them. Pinning: the LB can't migrate a live socket. Uneven load: scaling adds capacity for new connections but doesn't rebalance existing ones. Rollouts hurt: every deploy is a mass disconnect event — you need graceful drain and client reconnection. Cross-pod delivery: to push a message to user X you must route to the specific pod holding X's socket, and nothing tracks that by default. And the resource shape is different (the bold point): you scale on open-connection count, file descriptors and memory, not CPU, so your KEDA/HPA trigger has to change too. The pub/sub backplane solves or eases every one of these.

## [118] APPENDIX C · WEBSOCKETS · Scaling out: a pub/sub backplane (sldId 373)

Each pod owns only its own sockets; a Redis or Kafka backplane fans a message out to whichever pod holds the client.

p. 100

> The pattern that makes WebSockets horizontally scalable. Each Pod still owns only its own sockets, but every Pod subscribes and publishes to a shared backplane: Redis pub/sub for low latency, or a Kafka topic if you want durability and replay. In SignalR specifically, this is one line of code: services.AddSignalR().AddStackExchangeRedis("redis:6379") wires up the Microsoft.AspNetCore.SignalR.StackExchangeRedis package (MIT). When a publisher calls Clients.User("X").SendAsync(…), the message goes to the backplane without knowing which Pod holds X; the backplane fans it to all Pods, and the one Pod that holds X's connection delivers it. Now scale-up and zero-downtime rollouts work again, because no Pod is the single home of a conversation — connections can land anywhere and still receive everything. Redis is the common open-source default; Kafka if you already run it and want the durability. A managed, cloud-hosted SignalR service is not used: the open-source Redis backplane is what runs on your own Kubernetes.

## [119] APPENDIX C · WEBSOCKETS · Binary framing with protobuf — fast and versioned (sldId 374)

[chip] csharp · Google.Protobuf + WebSockets

```csharp
// raw System.Net.WebSockets: a protobuf binary frame, not JSON text
async Task Push(WebSocket socket, ulong seq, OrderPlaced ev)
{
    var env = new Envelope {
        Version = 2, Seq = seq, Type = "OrderPlaced",
        Payload = ev.ToByteString() };                // nested protobuf
    await socket.SendAsync(env.ToByteArray(),
        WebSocketMessageType.Binary, endOfMessage: true, ct);
}
// receive: parse the Envelope, dispatch on Type
var result = await ws.ReceiveAsync(buf, ct);
if (result.MessageType == WebSocketMessageType.Binary)
{
    var env = Envelope.Parser.ParseFrom(buf, 0, result.Count);
    switch (env.Type)
    {
        case "OrderPlaced":
            HandleOrderPlaced(env.Seq, OrderPlaced.Parser.ParseFrom(env.Payload));
            break;
    }
}
```

Protobuf frames are smaller and faster than JSON; the versioned envelope and seq number enable evolution and resume.

p. 101

> Two wins in one slide. Performance: protobuf binary frames are smaller and cheaper to parse than JSON text, which matters when pushing high-frequency updates to many connections.
>
> Versioning: a WebSocket message has no URL to hang a version on, so you version the envelope. The Version field lets the client detect an incompatible payload format and renegotiate; the Type field dispatches to the right typed payload; and a monotonic Seq number per connection is what makes reconnection and replay possible, the subject of the failure-handling slide.
>
> The envelope is a protobuf message compiled with Grpc.Tools, so the same .proto evolution rules from Appendix B apply. With SignalR (Appendix Q) the equivalent is the MessagePack hub protocol plus a versioned envelope record.

## [120] APPENDIX C · WEBSOCKETS · Failure handling: resume, don't restart (sldId 375)

Heartbeats detect dead links; the client reconnects with backoff and resumes from the last acknowledged sequence.

p. 102

> The cloud-native posture: treat every connection as disposable and design for its loss. Heartbeats (ping/pong) detect a dead link quickly — TCP alone can hang for minutes. When the connection drops, the client reconnects with exponential backoff plus jitter (so ten thousand clients don't reconnect in lockstep and hammer your pods after a rollout). On reconnect, the client sends its last-seen sequence number (last_seq = 1042); the server replays only the events the client missed (1043 onward), and because each frame carries a seq, the client can dedupe — so the whole thing is at-least-once and idempotent. The principle on screen: resume, don't restart. A reconnect should be invisible to the user, not a full state reload.

## [121] APPENDIX C · WEBSOCKETS · A cloud-native WebSocket checklist (sldId 376)

- Externalize fan-out to a backplane (Redis or Kafka); never assume one pod holds the client.
- Scale and trigger on connection count and memory, not CPU; set realistic per-pod connection caps.
- Drain gracefully on shutdown: stop accepting, signal clients to reconnect, let backoff spread the herd.
- Heartbeat to detect dead links (SignalR ships keep-alive built in: KeepAliveInterval defaults to 15s, ClientTimeoutInterval to 30s); reconnect with exponential backoff + jitter (also built into the JS / .NET clients); resume via a per-connection seq.
- Use binary frames with a versioned envelope; authenticate on connect and re-check on resume.

p. 103

> The operational checklist to leave on screen. Externalize fan-out to a backplane so no pod is special. Scale and set your KEDA/HPA trigger on connection count and memory, not CPU, and cap connections per pod realistically. Drain gracefully on shutdown — stop accepting, tell clients to reconnect, and let backoff-with-jitter spread the reconnect storm across your rollout. Heartbeat to detect dead links fast; reconnect with backoff and jitter; resume from a per-connection sequence number so the user never notices. And the security note in bold that teams forget: authenticate on connect and re-authenticate on resume, because a resume is a new TCP connection that could come from anywhere. Do these and WebSockets are just another well-behaved cloud-native workload.

## [122] APPENDIX C · WEBSOCKETS · Blazor on Kubernetes: Server vs WebAssembly (sldId 377)

Two Blazor hosting models with different scaling profiles; both run on plain ASP.NET Core Pods and need no managed SignalR service.

p. 104

> Blazor deserves its own slide in this appendix because it sits on both sides of the WebSocket scaling discussion. Walk the picture left to right. Blazor Server (left): a server-side ASP.NET Core process holds the user's component tree and view-model; a thin JS client renders DOM diffs streamed over a persistent SignalR WebSocket. Every UI interaction, every button click, is a round-trip. Every component instance is pinned to one Pod for its session lifetime. Calls to inventory, payment, etc. happen server-to-server. Once you scale to N Pods, you need a Redis backplane (one line: AddStackExchangeRedis), and every pinning, connection-count and drain concern from this appendix applies in full: it is a WebSocket workload that happens to drive UI updates. Blazor WebAssembly (right): the entire .NET runtime ships to the browser as WebAssembly; your C# components run client-side; the Pod is just a static-file host (nginx or ASP.NET Core serving .wasm + .dll + .css + .html). No SignalR, no per-user server state, no backplane — scales like any other static site. The trade: WASM has a one-time download cost (.NET 8+ AOT trims it considerably; .NET 10 trims it further) and your APIs must be browser-callable (CORS, public auth, gRPC-Web instead of gRPC). The decision rule at the bottom: pick Server for line-of-business apps where you want server-side auth and real-time state with minimal client work; pick WebAssembly for offline, high-interactivity, or SEO-friendly client surfaces. Most production .NET shops run both: Blazor Server for the admin console, Blazor WebAssembly for the customer-facing app. The cloud-native posture in either case: a containerised ASP.NET Core Pod, open-source Redis if needed, KEDA scaling on connections (Server) or RPS (WASM static host).

## [123] APPENDIX C · WEBSOCKETS · Choosing between Blazor Server and Blazor WebAssembly (sldId 378)

- Blazor Server — inherits everything in this appendix. SignalR-pinned; needs Redis backplane to scale (Microsoft.AspNetCore.SignalR.StackExchangeRedis, Apache 2.0); KEDA scales on connection count, not CPU; every deploy disconnects everyone.
- Blazor WebAssembly — escapes everything in this appendix. No persistent connection; static-file host scales like nginx; deploys are an atomic file swap; client runs .NET in WASM with full C# capability.
- Cost trade: Server has tiny client download but pays per-interaction round-trip latency and server-side memory per user. WebAssembly has a larger first-load (mitigated by AOT + trimming in .NET 8+, smaller again in .NET 10) but zero server state per user.
- Auth trade: Server uses normal cookie / server-side identity (the WCF / IIS-era mental model). WebAssembly uses bearer tokens visible to the browser — OAuth2 / OIDC with public clients.
- Both are MIT, both run on Kubernetes as plain ASP.NET Core Pods, both work without any managed cloud service. Open-source Redis for the backplane is all you need.

p. 105

> The take-home for the audience. For the WCF/IIS-era developer, Blazor Server feels familiar (server-side state, cookie auth, classic web app shape), which is both its appeal and its scaling problem. Blazor WebAssembly feels foreign at first (real client-side .NET running in a sandbox), but it scales the way the rest of cloud-native does: stateless static hosting + back-end APIs. There's no wrong answer; there are appropriate answers per workload. The bold final line is the one to leave up: nothing here requires a managed cloud service. SignalR is in-box ASP.NET Core. The Redis backplane is the StackExchangeRedis package (MIT) against any Redis (or Valkey, or KeyDB). The static-file host can be nginx or ASP.NET Core's UseStaticFiles. Hosting on Kubernetes is just two Deployments and two Services. A team moving from managed app hosting to Kubernetes keeps Blazor: it runs Redis itself as the backplane instead of a managed SignalR service.

## [124] Appendix D · Saga State & Compensation (sldId 379)

D

Persisting state, compensating cleanly, and the step-B-needs-A's-data problem.

> Appendix D is the deep mechanics behind the saga slide in the Data section. Three hard parts that the happy-path picture glosses over: where the orchestrator keeps its state so it survives a crash, how compensation works when a step fails midway, and a specific gnarly case people hit: when step B needs data that only step A produced, and how to resume after a crash between them.

## [125] APPENDIX D · SAGAS · Where a saga keeps its state (sldId 380)

Memory won't survive a Pod restart — persist every step transition in a DB, an event log, or a workflow engine.

p. 106

> First problem: the orchestrator must survive a crash mid-flow, so in-memory state is a non-starter: a Pod restart would strand every in-flight saga with no idea what to compensate. Three real options. A DB-backed state machine: one row per saga instance holding its status and a context blob; you own the transitions with EF Core; the simplest option, and enough for most cases. Event-sourced: append each step as an event and rebuild state by replay — full audit history; Marten on Postgres is the natural .NET fit, or EF Core for hand-rolled. A workflow engine like Temporal: durable execution with retries and timers built in — most power, least code, but a new dependency to run. Stateless is the lighter in-process alternative, compared with Temporal in this appendix. For the WCF/COM+ audience: this slide is where MSDTC distributed transactions get permanently retired — you can't have a two-phase commit across services in this world, so you reach for compensation-based consistency instead. The cross-cutting rule on screen: the state transition and the outbound command must commit together (the outbox pattern again), or you get lost or duplicated steps.

## [126] APPENDIX D · SAGAS · A persisted saga state machine (EF Core) (sldId 381)

[chip] csharp · .NET 10 + EF Core

```csharp
// SagaEngine.cs (excerpt), examples/17-sagas/dotnet: one durable step per call
static readonly string[] Steps = { "charge_payment", "reserve_stock", "book_shipping" };
public async Task AdvanceAsync(string sagaId, CancellationToken ct = default)
{
    await using var db = await dbFactory.CreateDbContextAsync(ct);
    await using var tx = await db.Database.BeginTransactionAsync(ct);
    var saga = (await db.Sagas.FromSql(                          // pessimistic row lock
        $"SELECT * FROM sagas WHERE id = {sagaId} FOR UPDATE")
        .ToListAsync(ct)).SingleOrDefault();
    if (saga is not { Status: "RUNNING" }) { await tx.CommitAsync(ct); return; }  // idempotent
    if (saga.StepIndex >= Steps.Length) saga.Status = "COMPLETED";
    else try {
        var step = Steps[saga.StepIndex];
        saga.Context[step] = ExecuteStep(step, saga.Context);   // call the service
        saga.StepIndex++;
    }
    catch (Exception) {
        saga.Status = "COMPENSATING";                           // hand off to the unwinder
    }
    await db.SaveChangesAsync(ct);                              // durable after every step
    await tx.CommitAsync(ct);                                   // the caller advances again
}
```

One locked row per saga, advanced one durable step at a time. A crash just means 'load the row and call AdvanceAsync again.'

p. 107

> This is the DB-backed option made concrete with EF Core — the default choice when the saga is bounded and the team wants to own the transitions. Key ideas: one Saga entity row, loaded with a pessimistic lock (FOR UPDATE in Postgres, equivalent in SQL Server) so two workers can't advance the same saga concurrently. The status guard makes AdvanceAsync idempotent — calling it on a finished saga is a no-op, which matters because retries and redeliveries will call it again. Each successful step accumulates its result into the Context dictionary, which is what the data-dependency slide relies on, and bumps the step index; the EF Core SaveChangesAsync makes the row durable after every step. Recovery needs no special path: Example 17 resumes RUNNING sagas from an IHostedService at startup by calling AdvanceAsync again, and a BackgroundService with PeriodicTimer (or Quartz.NET on a cron) plus DistributedLock does the same continuously, the cloud-native equivalent of a Windows Service that processed an MSMQ queue. Temporal .NET and Stateless, both in this appendix, solve the same problem at a different point on the build-vs-buy spectrum.

## [127] APPENDIX D · SAGAS · Compensating transactions unwind a failed saga (sldId 382)

Each committed step has an inverse; on failure they run in reverse order — there is no cross-service rollback.

p. 108

> Compensation is how a saga 'rolls back' when there's no actual rollback available across services. Each forward step that committed (payment.charge, inventory.reserve) has a defined semantic inverse: payment.refund, inventory.release. When book_shipping fails, you don't undo a database transaction (the payment has already happened at the provider); you run the compensations for the already-committed steps, in reverse order, newest first. Two things that bite people, both on screen: compensations must themselves be idempotent and durable, because a crash mid-unwind has to resume cleanly; and a compensation can itself fail, so it needs its own retries. The saga ends in a persisted COMPENSATED state with a full audit trail of what was done and undone.

## [128] APPENDIX D · SAGAS · Running compensations in reverse (sldId 383)

[chip] csharp · .NET 10 + EF Core

```csharp
static readonly Dictionary<string, string> Compensations = new()  // inverse per step
{
    ["charge_payment"] = "refund_payment",
    ["reserve_stock"]  = "release_stock",
    ["book_shipping"]  = "cancel_shipping",
};
public async Task CompensateAsync(string sagaId, CancellationToken ct)
{
    await using var tx = await db.Database
        .BeginTransactionAsync(IsolationLevel.ReadCommitted, ct);
    var s = await db.Sagas.FromSqlInterpolated(
        $"SELECT * FROM sagas WHERE id = {sagaId} FOR UPDATE").FirstAsync(ct);
    // undo only the steps that actually completed, newest first
    foreach (var step in Steps.Take(s.StepIndex).Reverse())
    {
        await InvokeAsync(Compensations[step], s.Context,
                          idempotencyKey: $"{sagaId}:{step}", ct);   // safe to retry
    }
    s.Status = "COMPENSATED";
    await db.SaveChangesAsync(ct);
    await tx.CommitAsync(ct);
}
```

Compensate only completed steps, in reverse, with an idempotency key so a retry never double-refunds.

p. 109

> The compensation logic. A simple dictionary gives each forward step its inverse. We iterate the completed steps (Take(StepIndex) then Reverse) and invoke each compensation. The idempotency key built from sagaId plus step is the line that prevents the nightmare scenario: a retry double-refunding a customer. The compensating service dedupes on that key. In production you'd track per-step compensation status too, so if compensation itself crashes halfway you resume from the right place — but the idempotency key makes even naive re-runs safe. This is why compensations are designed up front, as part of each step, not bolted on after. For this audience: this replaces the old MSDTC rollback semantics — in a distributed system the 'transaction' is the saga, the 'rollback' is the compensation sequence, and the 'commit' is when the last step succeeds. With Temporal .NET the workflow keeps a stack of compensations and runs them in reverse on failure, with the same guarantees and durable history.

## [129] APPENDIX D · SAGAS · When step B needs data only step A produced (sldId 384)

Don't make B call A. Persist A's output into the saga context and pass it forward; on resume, read it back.

p. 110

> This case is a common source of bad designs. The orchestrator calls service A, then service B — but B needs a value that only A produced (say A returns a reservation_id and a warehouse region that B requires to proceed). The tempting wrong answer is to have B call A directly — now you've created a hidden synchronous dependency between B and A, exactly the chatty coupling the whole architecture fights. The right answer is on screen: the orchestrator owns a saga context (a 'blackboard'), persists A's output into it after step A, and passes the needed values into B's call. B never knows A exists. And note this is already in our state-machine code — that 's.Context[step] = result' line is exactly this. Temporal .NET does the same automatically through its workflow input/output passing; Stateless does it via the OnTransitioned listener that lets you write the payload into the saga's persisted state.

## [130] APPENDIX D · SAGAS · Two ways to make a saga durable without rolling your own (sldId 385)

- When you outgrow the hand-rolled EF Core state machine, you have two well-trodden open-source paths in the .NET ecosystem — both featured in the diagrams that follow.
- Temporal .NET SDK — a durable execution engine (Temporal Server MIT, .NET SDK Apache 2.0, on NuGet as Temporalio). You write workflows and activities as plain C#; the Server persists every event and replays them deterministically on recovery. Most power, separate cluster to run.
- Stateless — a tiny in-process state-machine library (Apache 2.0). States, triggers, transitions, guards, entry/exit actions; you persist the current state to your own DB. Lighter weight, no extra cluster, less ceremony.
- Decision rule: reach for Temporal when the saga is long, complex, or shared across services and you want first-class retries, timers, signals and child workflows. Reach for Stateless when it's small, in-process and you'd rather keep one fewer thing to operate.
- Sidebar: Dapr Workflows is a third option if your platform already runs Dapr sidecars (CNCF Incubating, MIT) — same durable-execution model as Temporal, exposed via the Dapr sidecar instead of a direct SDK. Use it when the team's already invested in Dapr.

p. 111

> Frame the choice as managed durability against lightweight in-process state, both open source and production-grade.
>
> Temporal: an MIT-licensed Server and an open-source .NET SDK, on NuGet as Temporalio, actively maintained by the team that built Cadence. You get durable execution, deterministic replay, retries with backoff, timers, child workflows, signals and queries, and a CLI and UI to inspect runs. The cost is operating a Temporal cluster on your own Kubernetes, or choosing Temporal Cloud.
>
> Stateless: a small in-process .NET state-machine library (a community project). No extra cluster; you persist the CurrentState property to your own database, one column, and restore it before firing the next trigger. Better when the saga is small, the team already works in EF Core, and another runtime is overkill.
>
> Dapr Workflows is a sidebar: a third option when your environment already uses the sidecar pattern, not the focus of this deck. The decision is how much engine this saga needs.

## [131] APPENDIX D · SAGAS · Temporal .NET: a plain-C# saga the Server makes durable (sldId 386)

Worker (your ASP.NET Core BackgroundService) runs Workflow + Activity code; the Temporal Server persists every event and replays deterministically.

p. 112

> Walk the picture. Three boxes. On the left, your client, a REST handler in an ASP.NET Core app, injects ITemporalClient and calls StartWorkflowAsync(…) to kick off a workflow. In the middle, the Temporal Server: a cluster of Frontend, Matching and History services backed by Postgres (or MySQL / Cassandra) that persists every workflow event (every activity invocation, every result, every timer firing), so the workflow can be reconstructed from scratch by replay. On the right, the Worker: another ASP.NET Core app where you implement the workflow as a regular C# class annotated [Workflow] with a [WorkflowRun] method, and activities as plain C# classes annotated [Activity]. The worker runs as a BackgroundService that polls a task queue, gets the next workflow task, executes the next deterministic step. Crash the worker mid-flow and Temporal reissues the task to another worker, which replays history and resumes exactly where you were — no lost steps, no double-charges. That's durable execution. For this audience: think of it as 'BizTalk orchestration done right, open-source, polyglot, on Kubernetes' — except the workflow is just C# code with normal IDE tooling and unit testing, not a BizTalk visual designer. The bottom captions confirm the open-source posture: Temporal Server is MIT, the .NET SDK is Apache 2.0, both running on your Kubernetes if you want, no SaaS lock-in.

## [132] APPENDIX D · SAGAS · Temporal .NET workflow + activity, in ASP.NET Core (sldId 387)

[chip] csharp · Temporalio + ASP.NET Core

```csharp
// PaymentActivities: [Activity] ChargeAsync / RefundAsync, plain C# methods
[Workflow]
public class FulfillmentWorkflow    // deterministic C#, replayed by a Worker after a crash
{
    private static readonly ActivityOptions Opts =
        new() { StartToCloseTimeout = TimeSpan.FromSeconds(10) };
    [WorkflowRun]
    public async Task<string> RunAsync(SagaInput input)
    {
        var undo = new Stack<Func<Task>>();                // compensations, newest on top
        try
        {
            var paymentId = await Workflow.ExecuteActivityAsync(
                (PaymentActivities a) => a.ChargeAsync(input), Opts);
            undo.Push(() => Workflow.ExecuteActivityAsync(
                (PaymentActivities a) => a.RefundAsync(paymentId), Opts));
            var reservationId = await Workflow.ExecuteActivityAsync(
                (InventoryActivities a) => a.ReserveAsync(input, paymentId), Opts);
            undo.Push(() => Workflow.ExecuteActivityAsync(
                (InventoryActivities a) => a.ReleaseAsync(reservationId), Opts));
            return await Workflow.ExecuteActivityAsync(
                (ShippingActivities a) => a.BookAsync(input, reservationId), Opts);
        }
        catch (ActivityFailureException) { while (undo.TryPop(out var u)) await u(); throw; }
    }
}
```

Workflow and activities are plain C# classes; the workflow keeps its own compensation stack. State is durable on the Server.

p. 113

> The whole story on one slide. Activity classes are plain C#; methods marked [Activity] are registered with the worker at startup. The workflow class is marked [Workflow] with one [WorkflowRun] entry point. The body reads like synchronous code, but every activity call goes through Temporal's task queue and is durably scheduled, retried and timed out on the Server. StartToCloseTimeout is required on every activity call, so the options object is shared.
>
> The output of each activity (paymentId, reservationId) is captured in a local variable and in Temporal's event history. If the worker dies between charge and reserve, a replacement worker replays the history, recovers paymentId, and continues at reserve without re-running charge.
>
> Compensation is plain C# as well: each completed step pushes its undo onto a stack, and on an activity failure the workflow pops and runs them in reverse, the same discipline as the hand-rolled version, now durable because each undo is itself an activity. Hosting in ASP.NET Core: Temporalio.Extensions.Hosting registers the client and a hosted worker that lists the workflow and activity types.

## [133] APPENDIX D · SAGAS · Stateless: lighter, in-process, no extra cluster (sldId 388)

States, triggers, transitions, guards — plus a tiny serialization of CurrentState to save/restore across crashes.

p. 114

> Walk the picture. The top row is the saga as a state machine: Created → Paid → Reserved → Shipped → Done, with each transition triggered by an event (PayOk, ReserveOk, ShipOk, Delivered). On StepFail at any point, the machine drops down into the Compensating state and ultimately Failed — the same compensation discipline expressed as state transitions. Under it, three pieces. The StateMachine<TState, TTrigger> itself, configured in a small builder method via the Stateless package's fluent API — you declare states, transitions, guards (predicates that gate a transition), entry/exit actions (code that runs on a transition, where you'd call _payments.ChargeAsync or _inventory.ReserveAsync), and OnTransitioned listeners for notifications. The 'persist state yourself' block is the lightweight bit: serialize the CurrentState property to a single column in your saga row using EF Core or Dapper, restore it before firing the next trigger. No persister framework needed. And on the right, the code that drives the machine: await sm.FireAsync(Trigger.PayOk, payload) runs guards, actions, transitions, and the OnTransitioned hook writes the new state to your DB. The whole thing runs in-process inside your ASP.NET Core app — no extra cluster, Apache-2.0 open source.

## [134] APPENDIX D · SAGAS · Stateless: configure and drive (sldId 389)

[chip] csharp · Stateless package + EF Core

```csharp
public enum State    { Created, Paid, Reserved, Shipped, Done, Compensating, Failed }
public enum Trigger  { PayOk, ReserveOk, ShipOk, Delivered, StepFail }
public class FulfillmentSagaMachine
{
    private readonly StateMachine<State, Trigger> _sm;
    // ... CurrentState => _sm.State; OrderId { get; }
    public FulfillmentSagaMachine(string orderId, State initial,
                                   IPaymentService payments,
                                   IInventoryService inventory,
                                   IShippingService shipping)
    {
        OrderId = orderId;
        _sm = new StateMachine<State, Trigger>(initial);
        _sm.Configure(State.Created)
            .Permit(Trigger.PayOk, State.Paid)
            .OnEntryAsync(() => payments.ChargeAsync(orderId));
        _sm.Configure(State.Paid)
            .Permit(Trigger.ReserveOk, State.Reserved)
            .Permit(Trigger.StepFail,  State.Compensating)
            .OnEntryAsync(() => inventory.ReserveAsync(orderId));
        // ... Reserved -> Shipped and Compensating -> Failed are configured the same way
    }
    public Task FireAsync(Trigger t) => _sm.FireAsync(t);
}
// ... drive it: FulfillmentService.OnAsync loads the saga row, builds the machine, fires, saves
```

All in your ASP.NET Core process: states + triggers declared, entry actions invoke services, CurrentState persisted to your own DB.

p. 115

> FulfillmentSagaMachine wraps a Stateless StateMachine<State, Trigger> with enums for both type parameters: type-safe states and triggers. Configure() declares each state's permitted transitions and its entry action; OnEntryAsync runs the business call when the state is entered, and FireAsync is required once entry actions are asynchronous. The Permit chain reads like the state diagram.
>
> FulfillmentService.OnAsync is the entry point, called from an HTTP handler or a Kafka consumer. It restores the saga's state by order id from EF Core, rebuilds the machine in that state, fires the trigger, and saves the new CurrentState.
>
> The transactional discipline is yours: wrap the action's effects and the state save in one DbContext transaction, the same commit-together rule as the hand-rolled version. Compared with Temporal there is no separate server, but also no automatic retries, timers or replay; the BackgroundService sweeper from the persisted-state slide still applies.

## [135] Appendix E · API Error Handling (sldId 390)

E

One discipline, four wire formats.

> Appendix E. Error handling is where cloud-native systems fall apart, more often than the happy path. The thesis: agree one error contract (a stable machine code, a safe human message, a correlation id, a retryable flag, field details) and then map that same model onto REST, gRPC, Kafka and GraphQL. We finish on the failure mode that turns a blip into an outage, the retry storm, and the handful of controls that prevent it.

## [136] APPENDIX E · ERRORS · One error model, four wire formats (sldId 391)

The same five facts in every error; only the encoding changes per protocol.

p. 116

> Start with what every error must carry, regardless of protocol: a stable machine-readable code clients can branch on (not a localized string), a human-readable message safe to show, a correlation/trace id that ties the error to the distributed trace from section 11, a retryable flag (with retry-after when known), and structured field-level details. The four protocols just encode those same five facts differently — REST as problem+json, gRPC as status+details, Kafka via headers and a DLQ record, GraphQL as an errors[] entry with extensions. Agree this once as a shared contract; never leak stack traces or internal type names to callers.

## [137] APPENDIX E · ERRORS · REST: status, then Problem Details (sldId 392)

The status code is the category; the problem+json body carries the machine code and specifics.

p. 117

> REST has two layers. First the HTTP status class, which is the category and drives client behaviour: 4xx means the client must fix the request and should not blindly retry; 429 and 503 mean 'busy' and must be paired with a Retry-After header so clients back off; 5xx means a server fault that idempotent calls may retry with backoff. Second, the body: RFC 9457 Problem Details (application/problem+json, which superseded RFC 7807) gives a standard envelope (type, title, status, detail, instance), and you extend it with your stable code and the traceId. Status for the category, body for the specifics.

## [138] APPENDIX E · ERRORS · REST errors with ASP.NET Core ProblemDetails (sldId 393)

[chip] csharp · .NET 10 + IExceptionHandler

```csharp
// ProblemDetails (RFC 9457) in the box since .NET 6; IExceptionHandler since .NET 8.
builder.Services.AddProblemDetails();             // standard problem+json output
builder.Services.AddExceptionHandler<DomainExceptionHandler>();
app.UseExceptionHandler();                        // wires up the chain
public class DomainExceptionHandler : IExceptionHandler      // one place: domain → wire
{
    public async ValueTask<bool> TryHandleAsync(HttpContext ctx, Exception ex,
                                                 CancellationToken ct)
    {
        var (status, problem) = ex switch
        {
            StockException s => (StatusCodes.Status409Conflict, new ProblemDetails {
                Type = "https://errors.acme.io/stock", Title = "Insufficient stock",
                Status = StatusCodes.Status409Conflict, Detail = s.Message,
                Extensions = {
                    ["code"]    = "STOCK_UNAVAILABLE",                  // stable
                    ["traceId"] = Activity.Current?.TraceId.ToString() } }),
            _ => (StatusCodes.Status500InternalServerError, new ProblemDetails())
        };
        ctx.Response.StatusCode = status;
        await ctx.Response.WriteAsJsonAsync(problem, (JsonSerializerOptions?)null,
            "application/problem+json", ct);                       // RFC 9457 media type
        return true;
    }
}
```

ProblemDetails + IExceptionHandler give you RFC 9457 out of the box — stable code, safe message, trace id; never a raw stack trace.

p. 118

> ASP.NET Core has had ProblemDetails (RFC 9457) built into Microsoft.AspNetCore.Mvc since .NET 6 — the wire format, the media type (application/problem+json), and the integration with minimal APIs (Results.Problem) and controllers ([ProducesProblemDetails]) are all included. The IExceptionHandler interface added in .NET 8 is the central mapping seam — register one or more, each one inspects the exception and returns true if it handled it, false to defer to the next. Use it for domain-to-wire mapping so you never scatter ad-hoc error JSON across handlers. The status matches the category (409 here — a conflict the client can act on), and Extensions carries the stable machine code and the W3C trace id from System.Diagnostics.Activity for correlation. Nothing internal leaks: no stack trace, exception class name, or SQL. Those are an attack surface, and the WCF-era habit of returning SoapFault detail with full stack traces is exactly what this replaces. For validation specifically, ValidationProblemDetails is the typed subclass and Results.ValidationProblem the minimal-API helper.

## [139] APPENDIX E · ERRORS · gRPC: status codes + rich details (sldId 394)

A small fixed set of canonical codes, plus structured google.rpc.Status details in the trailers.

p. 119

> gRPC gives you a small, fixed set of canonical status codes, and the code you choose is part of the contract, because clients (and the Istio mesh) decide retry behaviour from it. INVALID_ARGUMENT and NOT_FOUND are client bugs: don't retry. FAILED_PRECONDITION and ALREADY_EXISTS are state issues: don't retry. UNAVAILABLE and ABORTED are transient: retry with backoff. RESOURCE_EXHAUSTED means you're being rate-limited — honour the RetryInfo delay. DEADLINE_EXCEEDED means tune the timeout. Beyond the code, attach a google.rpc.Status in the trailers with rich details, ErrorInfo (machine reason + domain) and RetryInfo (how long to wait), so the client gets the same five facts as everywhere else.

## [140] APPENDIX E · ERRORS · gRPC errors with rich status details (sldId 395)

[chip] csharp · grpc-dotnet + Google.Rpc

```csharp
using Grpc.Core;
using Google.Rpc;            // ErrorInfo, RetryInfo, Status
public override async Task<ReserveReply> ReserveStock(
    ReserveRequest req, ServerCallContext context)
{
    if (_inventoryDown)
    {
        var status = new Google.Rpc.Status
        {
            Code    = (int)Code.Unavailable,        // canonical code
            Message = "inventory temporarily down",
            Details =
            {
                Any.Pack(new ErrorInfo {
                    Reason = "STOCK_DOWN", Domain = "inventory" }),
                Any.Pack(new RetryInfo {
                    RetryDelay = Duration.FromTimeSpan(TimeSpan.FromSeconds(2)) }),
            }
        };
        // grpc-dotnet: throw RpcException with the rich status in trailers
        throw status.ToRpcException();           // extension from Grpc.StatusProto
    }
    return ToReply(await _stock.ReserveAsync(req));
}
```

Pick the canonical code (Unavailable = retryable) and attach ErrorInfo + RetryInfo so clients back off correctly.

p. 120

> This is grpc-dotnet's standard rich-error model — the same wire shape as every other gRPC stack because google.rpc.Status is the cross-language contract. The canonical code Unavailable tells the client and the mesh this is transient and retryable; the Status carries structured details — ErrorInfo with a machine reason and domain, and RetryInfo telling the client exactly how long to wait. The Grpc.StatusProto NuGet package provides the ToRpcException extension that packs the rich Status into the trailers, and throwing the RpcException signals the failure. For the audience: this is the gRPC equivalent of WCF's FaultException<T> with a fault contract — except the contract is google.rpc.Status (standard across languages), the codes are canonical, and the mesh (Istio) can act on them. The key discipline: don't overload a generic Internal code for everything — the code is how automated clients and Istio decide whether and when to retry, so getting it right is what prevents both lost work and retry storms.

## [141] APPENDIX E · ERRORS · Kafka: retry topics and a dead-letter queue (sldId 396)

Commit the offset, route the failed record aside, and keep consuming — a poison record never blocks the partition.

p. 121

> Kafka error handling has a failure mode unique to logs: a single poison record can block the whole partition forever if you keep retrying it in place, because the offset never advances — head-of-line blocking that stalls every record behind it. The fix is to move failures aside: try a bounded number of in-place retries, then route the record to a delayed-retry topic (reprocessed after a delay without blocking the live stream), and after N attempts send it to a dead-letter queue for humans or tooling. You commit the offset either way, so the main consumer keeps making progress. With Confluent.Kafka the loop is yours, so the invariant is explicit: bounded retries, then a delayed-retry topic, then a DLQ, with the offset committed on every branch.

## [142] APPENDIX E · ERRORS · Kafka retry + DLQ with Confluent.Kafka (sldId 397)

[chip] csharp · Confluent.Kafka + Polly 8

```csharp
// Confluent.Kafka + Polly 8: bounded in-place retries, a delayed-retry topic, a DLQ.
var pipeline = new ResiliencePipelineBuilder()
    .AddRetry(new RetryStrategyOptions {
        MaxRetryAttempts = 3, Delay = TimeSpan.FromMilliseconds(200),   // in-place
        BackoffType = DelayBackoffType.Exponential, UseJitter = true,
        ShouldHandle = new PredicateBuilder()
            .Handle<Exception>(e => e is not ValidationException) })
    .Build();
while (!ct.IsCancellationRequested)
{
    var cr = consumer.Consume(ct);
    try { await pipeline.ExecuteAsync(async t => await HandleAsync(cr.Message.Value, t), ct); }
    catch (Exception ex)
    {
        var attempts = cr.Message.Headers.TryGetLastBytes("retries", out var raw)
            ? int.Parse(Encoding.UTF8.GetString(raw)) : 0;
        var dlq = ex is ValidationException || attempts >= MaxRetries;  // 4xx or exhausted
        var headers = new Headers();
        if (dlq) headers.Add("error", Encoding.UTF8.GetBytes(ex.GetType().Name));
        else headers.Add("retries", Encoding.UTF8.GetBytes((attempts + 1).ToString()));
        await producer.ProduceAsync(dlq ? "orders.DLQ" : "orders.retry.30s",
            new Message<Null, string> { Value = cr.Message.Value, Headers = headers });
    }
    consumer.Commit(cr);                     // every branch commits: no head-of-line block
}
```

Bounded in-place retries, a delayed-retry topic, then a DLQ; the offset is committed on every branch, so a poison record can't stall the partition.

p. 122

> This is the Appendix E pattern over Confluent.Kafka. The loop is yours, so the invariant is explicit and readable: a Polly 8 retry pipeline gives bounded in-place retries with exponential backoff and jitter, and treats ValidationException as non-retryable, since retrying a 4xx gains nothing.
>
> When the in-place retries are exhausted, the record is re-published to a delayed-retry topic with a retries header; after MaxRetries attempts, or immediately for a validation failure, it goes to the dead-letter topic with the error type attached. Either way the offset is committed, so the consumer keeps making progress and a poison record never blocks the partition.
>
> Make the handler idempotent: at-least-once delivery means a retried record may have partly applied. For the MSMQ audience this is the MaxRetryCount, ReceiveErrorHandling and poison-queue model, written as code you can test.

## [143] APPENDIX E · ERRORS · GraphQL: partial success with errors[] (sldId 398)

One HTTP 200; the failed field is null and explained in errors[] with a machine code in extensions.

p. 123

> GraphQL breaks the one-request-one-status assumption: a single query can touch many resolvers, so the response is almost always HTTP 200 and carries both a data object and an errors array. When one field fails (say stock can't reach inventory), that field is set to null, an entry is added to errors[] with a message and the path to the failed field, and the machine code goes in extensions.code along with retryable and traceId. The rest of the data still returns. The anti-pattern to call out: blanket-failing the whole query (or returning a 500) when only one field broke — that throws away useful data the client already asked for. Partial success is a feature; let the client decide whether to retry just the failed field.

## [144] APPENDIX E · ERRORS · GraphQL field errors with HotChocolate (sldId 399)

[chip] csharp · .NET 10 + HotChocolate

```csharp
public class GraphQLErrorFilter : IErrorFilter
{
    public IError OnError(IError error) =>
        error.Exception switch
        {
            InventoryUnavailable iu => error
                .WithMessage(iu.Message)
                .WithCode("UNAVAILABLE")                  // → extensions.code
                .SetExtension("retryable", true)
                .SetExtension("traceId", Activity.Current?.TraceId.ToString())
                .RemoveException(),                       // don't leak stack trace
            _ => error                                    // default for everything else
        };
}
// ... Program.cs: AddGraphQLServer().AddErrorFilter<GraphQLErrorFilter>()
[ExtendObjectType<Order>]
public class OrderExtensions
{
    public async Task<int> GetStock(
        [Parent] Order order, IInventoryService inventory)
    {
        // ... RemainingAsync; on UpstreamException throws InventoryUnavailable (nulls the field)
    }
}
```

Throw from the field resolver; an IErrorFilter nulls that field and adds it to errors[] with code + retryable + traceId in extensions.

p. 124

> Throwing from a single field's resolver is exactly right: HotChocolate's exception-resolution chain catches it, sets that field to null, and appends an entry to errors[] with the message and path — while every other field resolves and returns normally. The IErrorFilter is the central mapping point — one IErrorFilter implementation, one method per exception family (here using a switch expression), return a transformed IError with WithCode and SetExtension calls. The .WithCode("UNAVAILABLE") sets the standard GraphQL error code in extensions.code; SetExtension lets you add any structured fields — retryable flag, traceId from Activity.Current, anything else you want. The .RemoveException() call is critical security hygiene: by default HotChocolate may include the exception type and stack in extensions during development; in production you strip it. Resist letting the exception bubble to the top and fail the whole operation — that's the blanket-failure anti-pattern. The client sees the order and total, sees stock is null, reads extensions.code, and decides whether to retry just stock. The same discipline works for HotChocolate's mutation errors (the 6a-style error unions) if you go that route for richer error contracts.

## [145] APPENDIX E · ERRORS · How a retry storm forms — and how to stop it (sldId 400)

Naive retries multiply load on a struggling service; bounded, spaced, circuit-broken retries break the feedback loop.

p. 125

> This is the failure mode that turns a brief blip into a full outage. The loop: a service slows, calls start timing out, clients retry (often 3x), which triples the load on the already-struggling service, causing more timeouts, causing more retries. It's a positive feedback loop, and naive retry logic is the amplifier. The controls that break it, bottom of the slide: bound every call with a timeout; cap retries to a small number and only for idempotent calls; space them with exponential backoff plus jitter (so clients don't retry in lockstep); add a circuit breaker to fail fast while the dependency is down; enforce a retry budget (cap retries as a percentage of traffic); and shed load early with 429/UNAVAILABLE rather than queueing work you can't do. In .NET, Polly is the canonical resilience library (BSD-3, ships under Microsoft.Extensions.Resilience and Microsoft.Extensions.Http.Resilience) — retries, circuit breakers, bulkheads, timeouts, hedging, all composable into a single ResiliencePipeline. Plus the Istio config from section 2, you get these at both the code and mesh layers.

## [146] APPENDIX E · ERRORS · Error-handling heuristics across all four (sldId 401)

- One contract, four encodings: a stable code, a safe message, a trace id, a retryable flag, field details — everywhere.
- The category lives in the protocol: HTTP status, gRPC code, GraphQL errors[] entry, Kafka DLQ vs retry topic.
- Make retryability explicit and honour it: Retry-After, RetryInfo, extensions.retryable — don't make clients guess.
- Never leak internals: no stack traces, SQL, or class names on the wire; map them to a code and log the detail server-side.
- Bound every retry (@Timeout, @Retry + jitter, @CircuitBreaker, retry budget) and make handlers idempotent.

p. 126

> The cross-cutting checklist to leave on screen. One contract expressed four ways — the same five facts whether it's problem+json, google.rpc.Status, a GraphQL extensions object, or a Kafka DLQ header. Let each protocol carry the category natively rather than inventing your own. Make retryability explicit and machine-readable so clients and the mesh back off correctly instead of guessing. Never leak internals — that's both a security issue and a coupling issue. And the bold line is the one that prevents outages: every retry is bounded and spaced (Polly's AddRetry with exponential backoff and jitter, AddCircuitBreaker, AddTimeout composed into a ResiliencePipeline), protected by a retry budget, and every handler idempotent so a redelivered or retried request is safe. Get these right and your failure paths become as boring as your happy paths.

## [147] Appendix F · DDD & Hexagonal Architecture (sldId 402)

F

Where the boundaries and the contracts come from.

> Appendix F. The whole talk assumes you've drawn good service boundaries and know what each API should say — this is where those come from. Domain-Driven Design gives you the strategic tools to place boundaries (subdomains, bounded contexts) and the tactical tools to model what's inside (aggregates, domain events); hexagonal architecture keeps the four protocols we've discussed as mere adapters around a clean domain core. Together they answer: where does an API boundary go, what should its contract say, and how do I keep REST/gRPC/GraphQL/Kafka out of my business logic. The reference is Vlad Khononov's Learning Domain-Driven Design.

## [148] APPENDIX F · DDD · Why DDD belongs in an API talk (sldId 403)

- An API is a contract between two bounded contexts — so “where's the boundary?” and “what does the contract say?” are DDD questions before they're API questions.
- Strategic DDD places the boundaries: subdomains (core, supporting, generic) and bounded contexts, each with its own model and ubiquitous language.
- Tactical DDD models what's inside: aggregates (consistency boundaries), entities, value objects and domain events — which become your resources and your Kafka events.
- Hexagonal architecture keeps it clean: the domain core is isolated, and REST, gRPC, GraphQL and Kafka are just adapters plugged into ports.
- Get the boundaries right and the APIs almost design themselves; get them wrong and no amount of REST polish will save you.

p. 127

> Set up why a DDD appendix belongs in an API talk. The throughline: an API is the contract between two bounded contexts, so the hardest API questions (where to split, what the contract should contain, what stays private) are boundary questions, and DDD is the discipline for boundaries. Distinguish strategic DDD (where the lines go) from tactical DDD (how you model inside a line), and preview that hexagonal architecture is what stops the four protocols from contaminating the domain. The closing line is the one to land: boundaries dominate outcomes far more than protocol polish.

## [149] APPENDIX F · DDD · Strategic DDD: subdomains & bounded contexts (sldId 404)

Place boundaries by business value and rate of change; each context owns one model and exposes it through an API.

p. 128

> Strategic DDD first. Classify the business into subdomains by value and volatility: core subdomains are your competitive edge, complex and fast-changing, where your best people belong; supporting subdomains are necessary but not differentiating, so build them cheaply; generic subdomains are solved problems you buy or adopt (auth, notifications). Each subdomain becomes one or more bounded contexts — a boundary inside which one model and one ubiquitous language are consistent. The punchline here is the bottom box: that boundary is exactly where the API sits, and the contract translates between two contexts' models rather than sharing internals. Map it to our system: order and pricing are core, inventory and shipping supporting, auth and notification generic.

## [150] APPENDIX F · DDD · A bounded context is a service-and-API boundary (sldId 405)

- A bounded context is the scope within which one model and one ubiquitous language stay consistent — the natural unit for a service and its API.
- The same word means different things across contexts: an “order” in fulfillment is not an “order” in billing. Don't force one shared model across the system.
- The context's published API is its only public surface; the schema, storage and internal types stay private — this is the “no leaky internal models” rule from anti-patterns, restated.
- Put boundaries where the business naturally splits and where a team can own them end-to-end (Conway's law) — that's where the integration cost is worth paying.

p. 129

> Make the bounded context concrete as the service/API boundary. The vivid example is the word 'order' meaning different things in fulfillment and in billing: that is why a single shared canonical model across the whole company fails, and why each context exposes its own model through an API instead. Tie back explicitly to the anti-patterns section: 'no leaky internal models' is just 'keep the bounded context's internals private.' And invoke Conway's law: boundaries that don't match team ownership generate constant cross-team coordination.

## [151] APPENDIX F · DDD · Context mapping: how contexts integrate (sldId 406)

The relationship patterns between contexts, and which ones your API implements.

p. 130

> Context mapping catalogues the ways two contexts relate. Walk the starred ones because they're what APIs implement: an Open-Host Service is a context that, because many others integrate with it, publishes a stable public API; the Published Language is the shared, versioned schema that API speaks; and an Anticorruption Layer is the translation you build when consuming someone else's context so their model doesn't leak into yours. The others are trade-offs: Conformist means you just accept the upstream model; Shared Kernel means you share a model and therefore change in lockstep — high coupling, use sparingly; Partnership means two contexts co-evolve; Separate Ways means don't integrate. The starred three are the ones to design explicitly.

## [152] APPENDIX F · DDD · Open-Host Service & Published Language (sldId 407)

- Open-Host Service: a context integrated by many publishes a stable, documented API as its public protocol — that's your REST / gRPC / GraphQL surface.
- Published Language: the shared, versioned schema that API speaks (OpenAPI, .proto, Avro), which is exactly what lives in the Apicurio registry.
- Anticorruption Layer: when you consume another context, translate their model into yours at the edge so their concepts never leak into your domain.
- Conformist is the cheap opposite — accept their model wholesale and inherit their changes; choose an ACL instead when the upstream model is messy or volatile.
- So the registry-backed contract from section 9 is a Published Language, and edge/gateway translation is an Anticorruption Layer.

p. 131

> This slide does the real work of connecting DDD vocabulary to the platform we built. Open-Host Service = the public API; Published Language = the schema in the registry; Anticorruption Layer = the translation at your edge. The bold line is the payoff: the audience has already built these things in sections 9 and 8 without the names; now they have the names and the theory. Emphasize the ACL-vs-Conformist choice as a real decision: conform when the upstream is clean and stable, build an ACL when it's messy or changes a lot, because the ACL localizes the blast radius of their changes to one translation layer.

## [153] APPENDIX F · HEXAGONAL · Hexagonal architecture: ports & adapters (sldId 408)

The domain core is isolated; REST, gRPC, GraphQL and Kafka are just adapters that plug into ports.

p. 132

> This is the architectural payoff of the whole protocols discussion. The domain core in the middle holds entities, aggregates and domain logic and depends on nothing — no framework, no I/O. It declares ports: inbound ports (what it can be asked to do) and outbound ports (what it needs from the world). Driving adapters on the left (REST, gRPC, GraphQL) translate an incoming protocol into a call on an inbound port. Driven adapters on the right (a Postgres repository, a Kafka publisher) implement the outbound ports. The arrows all point inward: adapters depend on the domain, never the reverse. The consequence we care about: the four protocols we spent the talk on are interchangeable adapters; you can add gRPC alongside REST, or a Kafka consumer, without touching a line of domain logic.

## [154] APPENDIX F · HEXAGONAL · Ports & adapters in code (sldId 409)

[chip] csharp · ports & adapters in .NET

```csharp
// domain — the core declares the interfaces (ports) it needs; no framework
public interface IOrderRepository { Task SaveAsync(Order order); /* FindByIdAsync, ... */ }
public interface IEventPublisher  { Task PublishAsync(OrderPlaced evt); }
// pure application logic; C# 12 primary constructor — no DI annotations needed
public class PlaceOrderUseCase(IOrderRepository repo, IEventPublisher events)
{
    public async Task<Order> ExecuteAsync(PlaceOrderCmd cmd)
    {
        var order = Order.Create(cmd);                // aggregate enforces invariants
        await repo.SaveAsync(order);
        await events.PublishAsync(new OrderPlaced(order.Id, order.Sku, order.Quantity));
        return order;
    }
}
// driving adapter — REST; the CLI adapter calls the same use case on a plain Host
app.MapPost("/orders", async (PlaceOrderCmd cmd, PlaceOrderUseCase placeOrder) =>
    Results.Json(OrderView.From(await placeOrder.ExecuteAsync(cmd)), statusCode: 201));
// driven adapters (Adapters/): EfOrderRepository : IOrderRepository over an OrdersContext,
//                             LogEventPublisher : IEventPublisher.
```

The domain depends only on ports it declares; the .NET container injects the adapters (EF Core repo, log or Kafka publisher). Swap or add one without touching PlaceOrderUseCase.

p. 133

> Walk the three blocks. Ports: the domain declares plain C# interfaces, a repository and an event publisher, and depends on nothing else (no ASP.NET Core, no EF Core, no Confluent.Kafka imports anywhere in the domain project). The application service PlaceOrderUseCase is pure logic: it creates the aggregate, saves via the port, publishes a domain event via the port, and never references framework types directly. C# 12 primary constructors give you the cleanest possible injection — no [Inject] attribute and no explicit constructor, just the parameter list on the class, available everywhere in the class body. The Microsoft.Extensions.DependencyInjection container resolves them at construction. The minimal-API endpoint is a thin driving adapter — turn the HTTP body into a command and call the use case; a gRPC service or HotChocolate resolver is the same shape. The outbound ports are implemented by adapters (EfOrderRepository over an EF Core OrdersContext for persistence, a log publisher in the example and a Kafka publisher on Confluent.Kafka in production) in separate projects so the domain project has zero infrastructure references — enforced by the .csproj graph. That's dependency inversion serving the boundary: protocols are replaceable, the domain stays stable. For audiences coming from MVC's classic Service → Repository → DAL stack: this is the same instinct, formalised by the .csproj dependency direction (domain depends on nothing; infrastructure depends on domain; web depends on application; nothing depends on web).

## [155] APPENDIX F · DDD · Aggregates and domain events (sldId 410)

- An aggregate is a cluster of objects treated as one consistency unit — the boundary inside which invariants hold and a single transaction commits. It's usually what sits behind one API resource.
- That makes the aggregate the natural transaction boundary, and therefore the outbox boundary: the state change and the domain event commit together (section 4).
- Domain events (“OrderPlaced”) are first-class in DDD; they become the Kafka events other contexts react to (section 5) — choreography between bounded contexts.
- Keep aggregates small: one aggregate per transaction, reference others by id, and let events connect them — which is exactly the saga story in Appendix D.

p. 134

> Tactical DDD, and it ties three earlier sections together. The aggregate is the consistency boundary: invariants hold within it and one transaction commits it, and it typically maps to a single API resource. Because it's the transaction boundary, it's also the outbox boundary from section 4: state plus event commit atomically. Domain events are the DDD concept that becomes your Kafka topic payloads, enabling choreography across contexts (section 5). And the small-aggregate rule (one per transaction, reference others by id, connect via events) is precisely why cross-aggregate consistency needs a saga (Appendix D). This slide is where DDD stops being abstract and visibly underpins the data, event and saga designs.

## [156] APPENDIX F · DDD · How DDD maps to our API stack (sldId 411)

- Bounded context → a service and its API boundary.
- Open-Host Service / Published Language → the REST/gRPC/GraphQL contract + the Apicurio registry.
- Anticorruption Layer → model translation at the gateway / consumer edge.
- Aggregate → an API resource and the transaction/outbox boundary behind it.
- Domain event → a Kafka event other contexts consume.
  - Reference: Vlad Khononov — Learning Domain-Driven Design (O'Reilly, 2021).

p. 135

> The summary map — leave it up while you recap. Every DDD concept on the left has shown up concretely on the right somewhere in the talk: contexts are services, the OHS/Published Language is the registry-backed contract, the ACL is edge translation, aggregates are resources and outbox boundaries, domain events are Kafka events. The message: DDD is the naming and reasoning behind the boundaries the whole architecture already relies on, not a separate methodology bolted on. Point people to Khononov's Learning Domain-Driven Design for the full treatment.

## [157] Appendix G · Balancing Coupling (sldId 412)

G

Coupling isn't the enemy — imbalance is.

> Appendix G. We've thrown around “coupled” and “decoupled” throughout as if loose is always better. This sharpens it, using Vlad Khononov's Balancing Coupling model. The reframe: coupling is necessary, since a system with zero coupling does nothing, so the goal is to balance it, not eliminate it. Coupling has three dimensions (integration strength, distance and volatility), and a coupling only hurts when all three are high together. This gives precise language for why a shared database is bad but a registry-backed API contract is fine, and it ties every anti-pattern from section 12 back to one model.

## [158] APPENDIX G · COUPLING · Coupling is necessary — balance it, don't eliminate it (sldId 413)

- Components must share some knowledge to collaborate; a system with zero coupling also has zero behaviour. “Loosely coupled” is too blunt a goal.
- Khononov's model evaluates the connection between two components, not the components themselves, along three dimensions: integration strength, distance and volatility.
- The headline: a coupling is only painful when strength, distance and volatility are all high at once — reduce any one and the pain drops.
- This is why “just split it into microservices” can backfire: spreading strong, volatile coupling across a network maximises all three dimensions — a distributed monolith.

p. 136

> Frame the appendix. The central, slightly contrarian idea: coupling is not a defect to be driven to zero — it's necessary, and the real skill is balancing it. Credit Khononov's Balancing Coupling model and stress that it measures the connection between components, not the components, along three dimensions. The headline sentence is the whole model in one line — pain needs all three of strength, distance and volatility to be high. The bold line is the cautionary tale that resonates with anyone burned by microservices: splitting strongly- and volatile-coupled code across a network doesn't remove the coupling, it just adds distance to it — the distributed monolith.

## [159] APPENDIX G · COUPLING · Coupling has three dimensions (sldId 414)

Integration strength × distance × volatility — a coupling only hurts when all three are high.

p. 137

> The model in one picture. Integration strength is how much knowledge two parts share — the more they share, the more likely a change in one forces a change in the other. Distance is how far apart they sit (same method, class, module, service, or system), and it sets the cost of a change that has to cross the boundary. Volatility is how often the coupled thing changes. The cost box at the bottom is the key relationship: strong plus distant is global complexity (the distributed monolith), but it only bites when the code is volatile. A strong, distant coupling on something that never changes costs you nothing. That's why all three dimensions have to be considered together rather than chasing “lose coupling” in the abstract.

## [160] APPENDIX G · COUPLING · The three dimensions, in practice (sldId 415)

- Integration strength: how much knowledge two parts share — from intrusive (private internals) down to contract (an explicit interface). Less shared knowledge = looser coupling.
- Distance: how far apart they sit — method, class, module, service, system. Greater distance raises the cost of any change that crosses the boundary.
- Volatility: how often the coupled thing changes. Khononov derives it from DDD subdomain type — core is volatile, generic is stable.
- Modularity = strength XOR distance: keep strong coupling local, and make anything distant a weak (contract) coupling. Being both strong and distant is the trap.

p. 138

> Unpack each dimension with a concrete handle. Strength is a ladder (intrusive to contract). Distance is intuitive — the further apart, the more it costs to change across the seam. Volatility is the clever part of the model: you can't know the future, but you can predict change-rate from DDD subdomain type (core changes a lot, generic barely changes), which connects this appendix straight back to Appendix F. The bold line is Khononov's modularity rule rendered as a slogan, strength XOR distance: you want exactly one of them, not both; strong-and-local (a cohesive module) is fine, weak-and-distant (microservices via contracts) is fine, strong-and-distant is the distributed monolith.

## [161] APPENDIX G · COUPLING · Integration strength: a ladder, worst to best (sldId 416)

From intrusive (shared internals) to contract (a versioned schema) — across distance, aim for the bottom rung.

p. 139

> Integration strength has four levels, worst to best. Intrusive coupling: one component reaches into another's private internals — the classic case is two services on one database, where either can break the other invisibly. Functional coupling: they share business logic or rules and must change together for functional reasons. Model coupling: they share a data model or DTOs — a shared library of types. Contract coupling: they integrate only through an explicit, stable, versioned contract — and that's our REST, gRPC, GraphQL and Kafka schemas in the registry. Lower on the ladder means less shared knowledge and looser coupling. The rule that matters: the greater the distance between two components, the further down this ladder you need to be.

## [162] APPENDIX G · COUPLING · Strength in our system (sldId 417)

- Intrusive (worst): two services sharing one database, or reaching into another's internals — any change can break the other invisibly. This is the shared-database anti-pattern.
- Functional / Model: sharing business logic or a model — e.g. a shared library of types. Fine within a context; risky across teams because it forces lockstep change.
- Contract (best across distance): integrate only through an explicit, versioned schema — our REST/gRPC/GraphQL APIs and Kafka event schemas, governed by the registry.
- The rule: the greater the distance, the weaker the coupling must be. Across services that means contract coupling — never shared state.

p. 140

> Map the ladder onto decisions in our system. The shared database is intrusive coupling and it's the worst precisely because the integration strength is maximal and invisible — neither side knows what the other depends on. Shared libraries are model/functional coupling: perfectly fine inside one bounded context or team, dangerous when they force two independently-deployed teams to release together. Contract coupling (APIs and event schemas in the registry) is the only strength level appropriate across service distance. The bold rule is the actionable takeaway and it's exactly why every cross-service integration in the talk went through a registered contract rather than a shared table.

## [163] APPENDIX G · COUPLING · Balancing coupling: strength vs. distance (sldId 418)

Strong or distant, rarely both — and put any unavoidable strong-and-distant coupling where volatility is low.

p. 141

> This brings strength and distance together into the design rule. Read the quadrants: high strength and close together is a cohesive module — perfectly healthy, keep it local. Low strength and distant is healthy microservices — services integrating through contracts. Low strength and close is needless indirection — you've split things that could just be merged. And the danger quadrant, top-right, is high strength at high distance: the distributed monolith, global complexity, where one change ripples across services and teams. The right-hand panel adds the third dimension: even a top-right coupling is tolerable if it never changes, but on volatile core-domain code it's where slow delivery and outages come from. So the formula: balance equals strength-XOR-distance, OR low volatility.

## [164] APPENDIX G · COUPLING · Distance and volatility (sldId 419)

- Distance is the cost multiplier: a change contained in one module is cheap; the same change spanning two services and two teams is slow and expensive.
- Volatility is the trigger: a strong, distant coupling on code that never changes is harmless; on volatile core-domain code it's where outages and slow delivery originate.
- Predict volatility from the domain: core subdomains change often — keep their couplings weak and local; generic subdomains are stable, so you can afford more coupling.
- Balance = (strength XOR distance) OR low volatility — put any unavoidable strong-and-distant coupling where the code rarely changes.

p. 142

> Deepen distance and volatility. Distance is why the same logical change can be a one-line edit or a multi-team, multi-deploy project — it multiplies cost. Volatility decides whether a less-than-ideal coupling matters: a textbook-ugly coupling on frozen code is a non-problem; a textbook-fine coupling on hot, ever-changing core code can still hurt. The DDD connection (from Appendix F) is the practical tool: subdomain type predicts volatility, so you route your strongest couplings away from core and toward stable, generic areas. The bold formula is Khononov's balance condition — worth writing on a whiteboard in a design review.

## [165] APPENDIX G · COUPLING · Coupling and our APIs (sldId 420)

- Every protocol choice we've made is a coupling choice: REST, gRPC, GraphQL and events are all contract coupling — the loosest kind that still lets services collaborate.
- The registry is what keeps that contract coupling stable: compatibility rules stop a producer from silently raising the integration strength on its consumers.
- Connascence (Page-Jones) is a finer lens on the same idea — API versioning is managing connascence of name and position in your schemas (why protobuf field numbers matter).
- Every anti-pattern from section 12 is an imbalance: shared DB = intrusive at distance; chatty sync chains = strong + distant + volatile; leaky models = model coupling across a boundary.

p. 143

> Bring it home to the talk's content. The reframe to offer: every protocol decision was secretly a coupling decision, and we kept choosing contract coupling because it's the loosest that still works across distance. The registry's compatibility gate is, in this language, a guard against a producer silently increasing integration strength on consumers — that's what a breaking change is. Mention connascence as the finer-grained classical model (Page-Jones) that versioning manages — protobuf field numbers are connascence of position made explicit and stable. The bold line re-diagnoses the anti-patterns section through the coupling model, which is a satisfying way to show these aren't separate lists of rules but one underlying principle.

## [166] APPENDIX G · COUPLING · Heuristics for balanced coupling (sldId 421)

- Don't chase zero coupling — chase balance. Strong coupling is fine when it's local and stable.
- As distance grows, drive strength down: across services, integrate only through versioned contracts, never shared state.
- Keep strong, volatile couplings inside a single bounded context or aggregate, where distance is small.
- Use DDD subdomain types to predict volatility, and put your weakest couplings around the parts that change most.
  - References: Vlad Khononov — Learning Domain-Driven Design (O'Reilly) and Balancing Coupling in Software Design (Addison-Wesley).

p. 144

> The closing heuristics — the slide to leave up. Don't eliminate coupling, balance it; lower strength as distance rises; keep strong-and-volatile couplings local (inside an aggregate or context); and use subdomain types to predict volatility so your loosest seams are around your most-changing code. These five lines are a usable design-review checklist. Close by pointing to both Khononov books, Learning Domain-Driven Design for the boundary tools in Appendix F and Balancing Coupling in Software Design for this model, as the two references that underpin both of these appendices.

## [167] Appendix H · Graceful Shutdown (sldId 422)

H

Disposability, kept as a promise.

> Appendix H. This is the operational flip side of factor 9 (disposability) and the cloud-native pillars: pods are killed and replaced constantly, so a service has to be able to go away cleanly. Ungraceful exits are the source of the 5xx blips users see during otherwise-healthy rolling deploys. The thesis: graceful shutdown isn't one setting, it's a short protocol between your app and Kubernetes — stop new traffic, finish in-flight work, drain consumers and sockets, then exit before the grace period runs out.

## [168] APPENDIX H · SHUTDOWN · Disposability is a promise you have to keep (sldId 423)

- Pods are cattle: every deploy, scale-down, autoscale event or reschedule kills and replaces them — often many times a day.
- An ungraceful exit drops in-flight requests, abandons unacked messages and leaves work half-done: the 5xx blips users notice during a rollout.
- Graceful shutdown is the flip side of factor 9, disposability: stop taking new work, finish what you accepted, release resources, then exit.
- It's a protocol between your app and the platform, not a single setting, and the platform gives you a fixed budget to do it in.

p. 145

> Set up the appendix by connecting it to two earlier ideas: factor 9 (disposability) from the twelve-factor arc, and the resilience pillar. The motivating story is the one every team has lived: a rolling deploy that looks healthy in tests but throws a scatter of 5xx errors in production because pods were torn down mid-request. Stress that this is not about a magic flag — it's a sequence the app and Kubernetes perform together, on a clock. This appendix walks that sequence, then shows the code on both sides of it.

## [169] APPENDIX H · SHUTDOWN · What happens when Kubernetes stops a pod (sldId 424)

SIGTERM starts a race; readiness-down plus a short preStop keep new traffic off until you've drained.

p. 146

> Walk the two lanes. Top, Kubernetes: it sends SIGTERM to PID 1, starts the terminationGracePeriodSeconds clock, and will SIGKILL you if you overrun. The catch is the red box — removing the pod from the Service endpoints is asynchronous (kube-proxy, kubelet, the mesh all have to catch up), so for a moment after SIGTERM traffic can still arrive. Bottom, your pod: the response is to flip readiness DOWN immediately (which starts the deregistration) and run a short preStop sleep to cover the lag, then stop accepting, drain in-flight work, stop consumers and close resources, and exit — ideally well before the grace period ends. The red arrows are the whole point: readiness + preStop are what keep new traffic off your dying pod during the race.

## [170] APPENDIX H · SHUTDOWN · The contract with Kubernetes (sldId 425)

- SIGTERM is the signal: Kubernetes sends it to PID 1, then waits terminationGracePeriodSeconds (default 30s) before SIGKILL.
- Readiness DOWN is how you stop new traffic — the pod leaves the Service endpoints but keeps running to finish in-flight work.
- There's a race: endpoint removal is asynchronous, so traffic can still arrive briefly after SIGTERM — a short preStop sleep covers the lag.
- Liveness must stay UP during the drain, or the kubelet restarts a pod that is already winding down.
- Set the grace period larger than your longest acceptable in-flight operation — too short cuts work off, too long stalls deploys.

p. 147

> These five points are the rules of the protocol. The distinction that trips people up is readiness vs liveness during shutdown: readiness should fail (it stops new traffic), but liveness must not fail (the kubelet would restart a pod that is draining). The asynchronous-deregistration race is the subtle one — it's why a preStop sleep exists at all; it's not about doing work, it's about waiting for the rest of the cluster to stop routing to you. And the sizing rule on the grace period is the practical lever: it must exceed your real worst-case in-flight operation, with headroom, or you'll be SIGKILLed mid-request.

## [171] APPENDIX H · SHUTDOWN · Graceful means something different per workload (sldId 426)

Only HTTP drains automatically; Kafka consumers, WebSockets and jobs each need their own drain.

p. 148

> The trap is assuming 'graceful shutdown' is one thing. Only HTTP request draining tends to be automatic (the server stops accepting and finishes in-flight). Everything else you wire up yourself in your shutdown hook. Kafka consumers: stop polling, finish the records already in hand, commit offsets, and leave the group so the rebalance is clean. WebSockets (from Appendix C): you can't finish a long-lived connection, so send a close/go-away and rely on client reconnection plus the per-connection seq and backplane. Jobs and schedulers: stop starting new work and either let running jobs finish or checkpoint so they resume after restart. The green footer is the safety net under all of it — because a hard SIGKILL is always possible, idempotent handlers make a redelivered request or message harmless.

## [172] APPENDIX H · SHUTDOWN · Graceful shutdown in ASP.NET Core (sldId 427)

[chip] csharp · .NET 10 + ASP.NET Core

```csharp
// Program.cs and DrainService.cs (excerpt), examples/21-graceful-shutdown/dotnet
// The default ConsoleLifetime turns one SIGTERM into a graceful stop; the drain is a hosted
// service step and HostOptions.ShutdownTimeout bounds the whole stop.
builder.Services.AddSingleton<ShutdownState>();
builder.Services.AddHostedService<DrainService>();
builder.Services.Configure<HostOptions>(o => o.ShutdownTimeout = TimeSpan.FromSeconds(20));
builder.Services.AddHealthChecks().AddCheck<ShutdownHealthCheck>("shutdown", tags: ["ready"]);
// GET /readyz answers 503 once ShutdownState.ShuttingDown is set; /healthz stays 200
public sealed class DrainService(ShutdownState state, IConfiguration config,
    ILogger<DrainService> logger) : IHostedLifecycleService
{
    public async Task StoppingAsync(CancellationToken cancellationToken)  // before StopAsync
    {
        state.MarkShuttingDown();                          // 1. readiness fails first
        var delay = TimeSpan.FromSeconds(config.GetValue("DRAIN_DELAY_SECONDS", 5));
        try { await Task.Delay(delay, cancellationToken); }   // 2. serve on: endpoints update
        catch (OperationCanceledException) { }
        logger.LogInformation("shutting down HTTP server (in_flight={InFlight})",
            state.InFlight);
    }                       // 3. Kestrel stops in StopAsync: no new requests, drains in-flight
    // 4. the DbContext services are disposed with the host; exit 0
}
```

One SIGTERM flips readiness; StoppingAsync waits DRAIN_DELAY_SECONDS, then Kestrel drains in-flight requests within ShutdownTimeout (20 s).

p. 149

> ASP.NET Core's default ConsoleLifetime already turns SIGTERM into a graceful stop, so Example 21 keeps it and adds the drain as one more hosted service. DrainService implements IHostedLifecycleService, and the host runs every StoppingAsync before any StopAsync. In StoppingAsync the service flips ShutdownState, so the ShutdownHealthCheck behind /readyz answers 503 and the Service stops routing, then waits DRAIN_DELAY_SECONDS (5 s, read through IConfiguration; it plays the part of a preStop sleep) while the endpoint removal propagates; /healthz stays 200 and Kestrel keeps serving. Kestrel then stops accepting and finishes in-flight requests in its StopAsync, all bounded by HostOptions.ShutdownTimeout (20 s here; the default is 30 s). The host disposes the DbContext services and the process exits 0, inside the 30-second grace period. The pattern for other work: one BackgroundService per long-running concern (a Kafka consumer, a scheduler, the Temporal worker from Appendix D, the Streamiz processor from Section 6), each draining in its own StopAsync: consumer.Close() commits offsets and leaves the group, a SignalR hub sends close frames, a Temporal worker shuts down. For the WCF refugees: this is the in-box equivalent of ServiceHost.Close, except that SIGTERM triggers it and the budget is HostOptions.ShutdownTimeout rather than a per-binding timeout. The Kubernetes settings (probes, preStop, grace period) are the platform half of the contract.

## [173] APPENDIX H · SHUTDOWN · The Kubernetes side: probes, preStop, grace period (sldId 428)

[chip] yaml · Kubernetes

```yaml
# deployment.yaml — give the pod time to deregister and drain
spec:
  terminationGracePeriodSeconds: 30        # >= preStop + drain + buffer
  containers:
    - name: order-service
      readinessProbe:                      # flips the Pod out of the Service
        httpGet: { path: /readyz, port: 8080 }
        periodSeconds: 5
        failureThreshold: 2                # ~10s to stop routing after DOWN
      livenessProbe:                       # keeps answering during the drain
        httpGet: { path: /healthz, port: 8080 }
      lifecycle:
        preStop:
          exec:
            command: ["sh", "-c", "sleep 5"]   # cover async endpoint removal
```

Readiness removes you from the Service; preStop covers the dereg lag; terminationGracePeriodSeconds must exceed your full drain or you get SIGKILLed mid-flight.

p. 150

> The platform half of the contract, the same in every language. terminationGracePeriodSeconds is the total budget: it must exceed the preStop sleep plus the worst-case drain plus a buffer. The readiness probe's periodSeconds times failureThreshold sets how fast Kubernetes stops routing after the service reports not ready, about ten seconds here, which the preStop sleep should cover.
>
> Readiness points at /readyz, which returns 503 from the moment SIGTERM arrives. Liveness points at /healthz, which keeps answering during the drain, so the kubelet does not restart a pod that is shutting down cleanly. The examples expose both endpoints in all six languages.
>
> The preStop sleep looks crude, but it is the practical fix for the asynchronous-deregistration race: align it with the probe timing rather than picking an arbitrary number.

## [174] APPENDIX H · SHUTDOWN · Beyond HTTP: messages, sockets, jobs (sldId 429)

- Only HTTP drains without extra code; everything else needs explicit drain code in your shutdown hook.
- Kafka consumers: stop polling, finish the records in hand, commit offsets, and leave the group so the rebalance is clean (ties to Event-Driven).
- WebSockets: send a close / go-away, let clients reconnect to another pod, and lean on the per-connection seq + backplane from Appendix C.
- Jobs and schedulers: don't start new work; let running jobs finish or checkpoint so they resume after restart.
- A hard SIGKILL is always possible — idempotent handlers make a redelivered request or message safe, which is your real safety net.

p. 151

> Reinforce the per-workload point from the diagram with the concrete drain steps. The Kafka sequence is the one to emphasize because it connects to the at-least-once delivery discussion from the Event-Driven section: committing offsets on the way out minimizes redelivery, and leaving the group makes the rebalance fast. WebSockets can't be 'finished,' so graceful there means handing the client off, which is exactly what the Appendix C reconnection design enables. The closing bold point anchors the whole appendix: you cannot guarantee a graceful exit, because the kubelet will sometimes SIGKILL you, so idempotency is what makes the system safe, and graceful shutdown makes the unsafe window rare.

## [175] APPENDIX H · SHUTDOWN · Graceful shutdown checklist (sldId 430)

- Handle SIGTERM; flip readiness DOWN first so the Service stops routing before you stop accepting.
- Add a short preStop sleep to cover asynchronous endpoint removal; keep liveness UP throughout the drain.
- Drain in-flight HTTP, commit consumer offsets, close sockets and pools — all bounded by terminationGracePeriodSeconds.
- Make the work idempotent so the inevitable occasional SIGKILL is survivable.
- Test it under a real SIGTERM during a rolling deploy — not just a happy-path integration test.
  - References: ASP.NET Core hosting — “BackgroundService / IHostedService” and “IHostApplicationLifetime” on learn.microsoft.com; HostOptions.ShutdownTimeout; Confluent.Kafka consumer Close semantics; Kubernetes “Termination of Pods” documentation.

p. 152

> The leave-up summary. Read it as an ordered runbook: readiness first, preStop to cover the race, then the actual drains, all inside the grace budget. The fourth point turns shutdown from fragile to safe: with idempotency, the occasional hard kill is a non-event. And the bold final point is the one teams skip: graceful shutdown that's never tested under a real SIGTERM during a rollout is just hopeful configuration. Encourage a small script (or a chaos test) that kills a Pod mid-request and asserts the client still got an answer — a 30-line `dotnet test` integration test with a `kubectl delete pod` step is enough to prove the contract holds.

## [176] Appendix I · L7 Routing & Traffic Management (sldId 431)

I

Software-defined, north/south and east/west.

> Appendix I. This one is large enough to be its own talk — the user explicitly suggested it could be cut later for that. The thesis: L7 routing isn't one box in a rack any more; it's a four-layer stack of software (edge, gateway, mesh, in-app) that makes decisions on every HTTP and gRPC envelope crossing the network, north/south and east/west. We'll walk what each layer can see and decide, show real config in HAProxy/Nginx/Istio, cover sticky sessions, traffic steering, payload modifications and latency, then go inside the app for rule-based routing with a Confluent.Kafka consumer and NRules, then circle back to east/west, where most decisions happen.

## [177] APPENDIX I · L7 ROUTING · L7 routing: software, not silicon (sldId 432)

- The hardware load balancer used to be where routing decisions lived. In a cloud-native system that work has moved into software — programmable, observable, and runnable anywhere.
- L7 means application layer: the router sees the HTTP or gRPC envelope (host, path, method, headers, cookies, gRPC service.method) and can route on any of it.
- It lives in four layers — edge / ingress, API gateway, service mesh, and (sometimes) inside the app itself. Each makes a different type of L7 decision.
- It runs both directions: north/south (clients into your system) and east/west (service to service). Most L7 decisions happen on internal traffic.
- The non-hardware stack is open source and composable: HAProxy, Nginx, Envoy, Istio, Linkerd, Kong, Traefik, YARP, NRules — plus a YAML or two.

p. 153

> Open the appendix by reframing what L7 routing is in 2026: not an appliance, but layered software that runs inside Kubernetes alongside everything else. The four-layer mental model (edge, gateway, mesh, in-app) is the backbone of the whole appendix — we'll touch each layer in turn. Stress north/south plus east/west early; people default to thinking about ingress, but inside a microservices system the volume of east/west calls dwarfs north/south, and that's where mTLS, retries and locality routing earn their keep. Name the open-source pieces explicitly so the audience knows the talk is about real, free, runnable software.

## [178] APPENDIX I · L7 ROUTING · L4 vs L7: what each layer can decide on (sldId 433)

L4 sees connections; L7 sees the conversation — paths, headers, methods, cookies, gRPC service.method.

p. 154

> Anchor the discussion in the OSI model just enough to be useful. L4 is the layer of IPs, ports and TCP — a classic load balancer can pick a backend by 5-tuple and hash-balance traffic, but it cannot read URLs, headers, cookies, methods or gRPC metadata. L7 sees the full HTTP/gRPC envelope: host, path, headers, cookies, JWT claims, query parameters, methods, and the gRPC service.method pair. That's the entire menu of inputs the routing patterns in this appendix use to make routing decisions. The TLS SNI line in both columns matters: L4 LBs can route by SNI without terminating TLS (cheap, opaque), while L7 LBs typically terminate TLS so they can see everything else (richer, slightly slower).

## [179] APPENDIX I · L7 ROUTING · The L7 capability menu (sldId 434)

- Routing rules: path / host / header / method / cookie / gRPC method → backend.
- TLS termination: decrypt at the edge, re-encrypt (or use mTLS) inward.
- Traffic management: canary, blue/green, A/B, header-based, geo, shadow.
- Payload modification: inject / strip headers, rewrite URLs, transform bodies.
- Resilience: timeouts, retries with backoff + jitter, circuit breakers, outlier ejection — the same toolkit from Appendix E, applied at the network.
- Cross-cutting: authn/authz, rate limiting, WAF, request mirroring, full traces and metrics on every hop.

p. 155

> Read this as the menu of L7 features you can mix and match across layers. The bold last point is the operational payoff: every L7 router emits traces and metrics, which is how you see what is happening across the four layers, and it ties back to the observability section. Most of these features used to be hardware appliances; now they're an annotation or a YAML block away. The resilience capabilities (timeouts, retries, circuit breakers) overlap with what Appendix E said about avoiding retry storms: the mesh implements many of them by default, but you still need bounded retries and budgets to prevent amplification.

## [180] APPENDIX I · L7 ROUTING · Where L7 lives: the layered stack (sldId 435)

Four layers, north/south at the top, east/west at the bottom, each making a different type of L7 decision.

p. 156

> This is the backbone diagram for the whole appendix. North/south traffic (clients into the system) enters through the edge/ingress layer (HAProxy, Nginx, Envoy, Traefik), where TLS terminates and coarse host/path routing happens, then through the API gateway (Kong, Istio gateway, YARP), which handles product-level concerns like auth, rate limiting and transformation. Once inside the cluster, east/west traffic is governed by the service mesh (Istio + Envoy sidecars, or Linkerd) — every internal call gets mTLS, retries, outlier detection and locality-aware load balancing. Finally, when L7 decisions need to consider business rules the platform doesn't know about, you push routing into the app itself (.NET: a Confluent.Kafka consumer + NRules). Each layer is the right place for a different type of decision; every topic in this appendix maps to one of them.

## [181] APPENDIX I · L7 ROUTING · A request's L7 path (sldId 436)

One HTTP request is a chain of L7 decisions made by four independent components.

p. 157

> Walk a single request left to right. It starts at the client — say a browser or another service. The edge load balancer terminates TLS, does host/path routing and maybe WAF; the API gateway authenticates the caller, applies rate limits and may transform; the mesh sidecar adds mTLS for the cluster's internal hop, applies retries and locality routing; and finally the service can do its own in-app routing if the business rules demand it. Each box can refuse, transform or branch the request, and each emits a trace span, so the full path is observable end to end. This is the request lifecycle from section 11, viewed through the L7 lens.

## [182] APPENDIX I · L7 ROUTING · Open-source L7 building blocks (sldId 437)

- HAProxy: fast, battle-tested L7 LB; ACL-driven config; classic ingress.
- Nginx: ubiquitous web server / LB; location-block routing; widely used as ingress controller.
- Envoy: the modern L7 proxy; HTTP/2, gRPC, dynamic config; the sidecar of choice.
- Istio: a control plane built on Envoy; CRDs for routing, security, observability across the mesh.
- Kong, Traefik, YARP: opinionated API gateways with plugin ecosystems. YARP (Yet Another Reverse Proxy, MIT, from Microsoft) is the .NET-native one — a reverse proxy library you embed in an ASP.NET Core app for full code-level control.
- Kafka consumer + NRules: when the routing logic is a business rule, push it into the app — a content-based router + a rule engine.

p. 158

> Differentiate the pieces so the audience knows when to reach for which. HAProxy and Nginx are the workhorses of the edge — mature, fast, predictable. Envoy is the modern choice for sidecars because it speaks HTTP/2 and gRPC natively and supports dynamic configuration via xDS. Istio (and Linkerd) wrap Envoy in a control plane and give you the mesh CRDs (VirtualService, DestinationRule). Kong, Traefik and YARP are API gateways with plugin ecosystems and a more product-aware feature set; YARP (MIT, from Microsoft) is the .NET-native option — a library you embed in an ASP.NET Core app for full code-level control of routing, transforms and load-balancing. The bold last point introduces the rule-based routing material: when the decision is 'route based on a business rule a non-developer needs to change weekly,' the right place is a rule engine inside the app, not a YAML file in the cluster.

## [183] APPENDIX I · L7 ROUTING · Content-based routing with HAProxy (sldId 438)

[chip] haproxy.cfg

```haproxy.cfg
frontend http_in
    bind *:443 ssl crt /etc/haproxy/certs/ alpn h2,http/1.1 # TLS here; h2 for gRPC
    acl is_api          path_beg /api/
    acl is_grpc         req.hdr(content-type) -m beg application/grpc
    acl is_internal     req.hdr(x-internal) -m str 1
    acl is_canary       hdr(cookie) -m sub canary=on
    use_backend grpc_pool      if is_grpc        # by content-type
    use_backend order_v2_pool  if is_canary      # by cookie
    use_backend order_int_pool if is_internal    # by header
    use_backend order_pool     if is_api         # by path
    default_backend            web_pool
backend order_v2_pool
    balance roundrobin
    server v2a 10.1.0.10:8080 check
    server v2b 10.1.0.11:8080 check
```

ACLs read the L7 envelope (path, header, cookie, content-type) and use_backend dispatches — classic, fast, predictable.

p. 159

> HAProxy is the lingua franca of L7 LBs. The pattern is always the same: declare ACLs that read parts of the L7 envelope (path_beg for URL prefixes, hdr/req.hdr for headers, content-type for the body type), then use_backend dispatches based on those ACLs in order. This single frontend shows four different content-based routing decisions — by content-type (gRPC traffic goes to a gRPC pool), by cookie (canary users), by header (internal users), by path. Notice TLS terminates at this frontend; everything inside is plaintext within the cluster (or re-encrypted via mTLS at the mesh layer). HAProxy's reload semantics are graceful by default — it can drain old workers while new ones take traffic, which matters for Appendix H's shutdown discipline.

## [184] APPENDIX I · L7 ROUTING · Content-based routing with Nginx (sldId 439)

[chip] nginx.conf

```nginx.conf
# map directive — declarative routing table on a header value
map $http_x_app_version $upstream_pool {
    default   order_v1;
    "v2"      order_v2;
    "v2beta"  order_v2_beta;
}
server {
    listen 443 ssl; http2 on;
    ssl_certificate     /etc/nginx/certs/tls.crt;
    ssl_certificate_key /etc/nginx/certs/tls.key;
    location /api/orders/ {                       # path-based routing
        proxy_pass http://$upstream_pool;         # picked by the map
        proxy_set_header X-Request-Id $request_id;
    }
    location ~ ^/api/grpc/ {                       # gRPC traffic
        grpc_pass grpc://orders_grpc_pool;
    }
}
```

map turns a header value into an upstream pool name; location blocks dispatch by path and protocol — HTTP and gRPC side by side.

p. 160

> Nginx's content-based routing is built around location blocks and the map directive. The map is the elegant bit: it converts a header value into a variable, which then drives proxy_pass — you express the routing table declaratively, then point a single location at the variable. Location blocks split HTTP from gRPC (grpc_pass) so you can run both protocols through one server. The X-Request-Id injection is a tiny example of payload modification — the L7 router can inject correlation headers so downstream traces can be stitched together. Nginx as an ingress controller in Kubernetes (the ingress-nginx project) is one of the most-deployed L7 routers in the world.

## [185] APPENDIX I · L7 ROUTING · Content-based routing in the mesh: Istio VirtualService (sldId 440)

[chip] yaml · Istio VirtualService

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: orders }
spec:
  hosts: [orders]
  http:
  - match:                                    # gRPC by service.method
    - uri: { prefix: /acme.orders.v1.OrderService/ }
    route: [{ destination: { host: orders, subset: v2 } }]
  - match:                                    # by header
    - headers: { x-internal: { exact: "1" } }
    route: [{ destination: { host: orders, subset: v2 } }]
  - match:                                    # by cookie
    - headers: { cookie: { regex: ".*canary=on.*" } }
    route: [{ destination: { host: orders, subset: v2 } }]
  - route: [{ destination: { host: orders, subset: v1 } }]   # default
```

Match by URI prefix (gRPC service.method), header, or cookie — same L7 inputs, expressed as Kubernetes CRDs.

p. 161

> The same content-based routing primitives, but expressed as Kubernetes CRDs that the mesh control plane (Istio) compiles down to Envoy sidecar configuration. Three match rules, each sending to a different DestinationRule subset: by URI prefix (which is how you route on gRPC service.method, since gRPC paths look like /package.Service/Method), by header, and by cookie. The default route at the bottom is critical; without it, unmatched requests have nowhere to go. The CRD lives in Git, gets reviewed like any other change, and Istio reconfigures every sidecar in the cluster within seconds. This is the modern face of L7 routing — declarative, GitOps-managed, distributed across thousands of pods.

## [186] APPENDIX I · L7 ROUTING · SSL / TLS termination at L7 (sldId 441)

- Edge terminates TLS so the L7 router can read and route on the request — you cannot inspect headers or paths through an encrypted connection.
- Re-encrypt or mTLS inward: terminate at the edge, then either plaintext within the cluster (rare today) or mTLS via the mesh (the modern default).
- Certificate management: cert-manager + Let's Encrypt for public certs; SPIFFE / SDS for service identity inside the mesh; Istio rotates pod certs automatically.
- TLS passthrough (no termination) when you need end-to-end encryption (gRPC client mTLS, regulated payloads); route by SNI only.
- Cost: TLS handshakes are real CPU. Modern stacks use session resumption, TLS 1.3 and HTTP/2 to amortise the cost across many requests.

p. 162

> Cover the three modes of TLS at the edge: terminate-and-decrypt (the common case, lets you do L7 things), terminate-and-re-encrypt (most secure default in a mesh, since mTLS inside is automatic), and passthrough (when you must not see the payload, e.g. client mTLS for regulated traffic — route by SNI only). cert-manager is the standard cluster-side answer for public certificates; SPIFFE-style identity and Envoy's SDS handle service-to-service certs automatically inside the mesh. Mention the CPU cost briefly so the L7 latency budget makes sense — a TLS handshake is milliseconds, and you want to amortise it via session resumption, TLS 1.3 and HTTP/2 multiplexing.

## [187] APPENDIX I · L7 ROUTING · Sticky sessions: cookie vs IP-hash vs none (sldId 442)

Convenient for legacy state, hostile to elastic scaling — prefer stateless behind a JWT.

p. 163

> Three modes worth knowing about. No affinity is the default and what you want — any pod gets any request, load is even, and client state lives somewhere else (Redis, the JWT, the database). Cookie-based stickiness is what you fall back to when something stateful (a shopping cart in memory, a legacy session) has to stay with one pod; the LB sets a cookie on the first response and uses it to route subsequent requests to the same pod. It works behind any L7 LB but ties the user's session to one pod's lifetime — restart that pod, lose the session. IP-hash hashes the source IP to a pod; it needs no cookies but is fragile to NAT and mobile networks where many users share an IP, leading to skewed load. The red footer is the real cost: stickiness fights elastic scaling, hurts pod restarts and breaks scale-to-zero. Use it only for a known constraint, never as a default.

## [188] APPENDIX I · L7 ROUTING · Sticky sessions in practice (sldId 443)

- When you need them: legacy session state, a stateful WebSocket that hasn't been moved off-process yet, certain rate-limit windows tied to a token bucket per pod.
- Cookie-based is almost always the right choice over IP-hash: it survives NAT and lets clients explicitly drop the cookie.
- What stickiness breaks: even load balancing, fast pod restarts, scale-to-zero, blue/green flips, and a clean Appendix H graceful shutdown for any stateful pod.
- The right fix is usually upstream: move session state to Redis or the JWT, use a backplane for WebSocket fan-out (see Appendix C), and treat every pod as disposable.

p. 164

> Make stickiness a last resort, not a first reach. Cookie-based affinity is the safer of the two stickiness options because clients can drop the cookie and NAT doesn't break it. The list of things stickiness breaks is the real argument against it: it actively fights the entire cloud-native delivery model — elastic scaling, fast restarts, graceful shutdown. The bold final point is the architectural fix: externalise the state. Redis for session data, JWT claims for user identity, the WebSocket backplane from Appendix C for fan-out. With that done, your LB is back to no-affinity and the platform works the way it wants to.

## [189] APPENDIX I · L7 ROUTING · Intelligent traffic steering (sldId 444)

Six familiar shapes — each is a header or weight rule away.

p. 165

> Six patterns that all share the same L7 primitives. Canary: 90/10 weighted routing to a new version, watching metrics and ramping. Blue/green: two identical environments, traffic flipped atomically (and rolled back atomically). A/B test: a stable cohort maps to a variant via a user identifier so the same user always sees the same variant — critical for valid measurement. Header-based: dark launches and internal-only previews by routing on x-internal or similar. Geo / latency: send EU users to EU pods for RTT and data residency. Shadow / mirror: copy a percentage of real traffic to a new version, observe its behaviour, but don't return its responses to the client; this tests the new version under realistic load. The point is they're not different things mechanically; they're the same routing rule expressed with different inputs and weights. The difficult part is the deploy discipline around them: alerts that trigger an automatic rollback, gradual ramps, and the metrics that tell you the canary is bad before users do.

## [190] APPENDIX I · L7 ROUTING · Canary release: weighted Istio routing (sldId 445)

[chip] yaml · Istio canary

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: orders }
spec:
  hosts: [orders]
  http:
  - route:
    - destination: { host: orders, subset: v1 }
      weight: 90                              # 90% on the stable version
    - destination: { host: orders, subset: v2 }
      weight: 10                              # 10% on the canary
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata: { name: orders }
spec:
  host: orders
  subsets:
  - name: v1
    labels: { version: v1 }
  - name: v2
    labels: { version: v2 }
```

VirtualService splits traffic by weight; DestinationRule defines the subsets by pod labels — the canonical canary release pattern.

p. 166

> The canonical Istio canary. Two CRDs working together: DestinationRule defines subsets by pod label (version=v1 and version=v2), and VirtualService routes by weight to those subsets. Changing the weights in Git and reconciling the cluster ramps the canary — typically through 10%, 25%, 50%, 100% over hours or days, with metric gates between each step. If error rate or latency on v2 crosses a threshold, an automated controller (Flagger, Argo Rollouts) flips the weights back to 100/0 in seconds. The same weighted-routing primitive does shadow traffic, geo balance, and blue/green flips — the only thing that changes is which subsets you target and what the weights are.

## [191] APPENDIX I · L7 ROUTING · Header-based steering: dark launches (sldId 446)

[chip] yaml · Istio header-based

```yaml
# route internal beta users to v2; everyone else stays on v1
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: orders }
spec:
  hosts: [orders]
  http:
  - match:
    - headers:
        x-acme-beta: { exact: "true" }        # set by your auth proxy
    route: [{ destination: { host: orders, subset: v2 } }]
  - match:
    - headers:
        user-agent: { regex: ".*AcmeInternal.*" }
    route: [{ destination: { host: orders, subset: v2 } }]
  - route: [{ destination: { host: orders, subset: v1 } }]
```

First match wins; an internal-only header (set upstream by auth) hands real production traffic to v2 — with zero blast radius.

p. 167

> Header-based steering is how you do dark launches and betas safely. An upstream identity proxy sets an x-acme-beta header for opted-in users, and the VirtualService routes those users to v2 — in real production traffic, on real data, but with zero exposure to anyone outside the beta. First match wins, so order the rules from most-specific to least, ending with the catch-all default. This is also how you do internal-only previews (route by an internal user-agent string) and per-tenant feature gates (route by an x-tenant-id). Combined with weighted routing, you can do 'roll the canary forward only for the beta cohort,' which is the most surgical release pattern in the toolbox.

## [192] APPENDIX I · L7 ROUTING · Payload modifications (sldId 447)

- Header injection: X-Request-Id, traceparent, X-Forwarded-For, identity claims — propagate context downstream so the trace stitches together.
- Header stripping: drop Authorization or PII headers before forwarding to a less-trusted backend; strip Server / X-Powered-By outbound.
- URL rewrites: /api/v1/orders → /orders internally; clean public URLs over messy service paths.
- Body transformation: rare but possible — protocol translation, redaction, format conversion (Envoy filters, Camel transforms).
- Cost: body inspection means reading the full request into memory — the slowest L7 thing you can do. Use it sparingly, never on every request.

p. 168

> Distinguish the cheap modifications from the expensive ones. Header inject/strip and URL rewrites cost almost nothing: the router is already parsing the HTTP line and headers. Body transformation is the expensive one because it forces the router to buffer the full payload, which kills streaming, blows memory on large requests and can become a bottleneck under load. Two examples: trace context propagation (the W3C traceparent header is how the spans from earlier in the request path stitch together with the spans downstream, which is why the request-id injection in the Nginx example mattered), and identity propagation (the auth proxy validates a JWT once at the edge and injects validated claims as headers so downstream services don't each re-validate). The bold point is the practical advice: if you can do it in the headers, do it in the headers.

## [193] APPENDIX I · L7 ROUTING · Header injection and URL rewrites (sldId 448)

[chip] yaml · Envoy / Istio

```yaml
# Envoy / Istio: inject identity headers, strip secrets, rewrite paths
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: orders }
spec:
  hosts: [orders.acme.io]
  http:
  - match: [{ uri: { prefix: /api/v1/orders } }]
    rewrite:
      uri: /orders                                  # external -> internal path
    route: [{ destination: { host: orders } }]
    headers:
      request:
        set:
          x-client-ip: "%DOWNSTREAM_REMOTE_ADDRESS_WITHOUT_PORT%"      # caller address
          x-peer-identity: "%DOWNSTREAM_PEER_URI_SAN%"
        remove: [ authorization, cookie ]            # don't leak inward
      response:
        remove: [ server, x-powered-by ]             # don't leak outward
```

Rewrite paths, inject the caller address and identity, strip secrets — all declaratively in the VirtualService.

p. 169

> Payload modification as configuration, not code. The URL rewrite cleans up the path before forwarding: public /api/v1/orders becomes internal /orders.
>
> The request header set adds the caller's address and the identity from the client's mTLS certificate (its URI SAN, which is the SPIFFE ID inside the mesh), so identity arrives at the network layer. Envoy creates an x-request-id itself when a request has none.
>
> The request header remove strips Authorization and Cookie before the request reaches the backend, after the gateway has validated the token and turned it into trusted claims. The response header remove drops Server and X-Powered-By so responses do not reveal the stack. All of it is declarative and reconciled from Git; no service code is involved.

## [194] APPENDIX I · L7 ROUTING · Beyond the edge: routing inside the app (sldId 449)

- Sometimes the routing decision is a business rule the platform doesn't know about: route 'high-value-customer claims' here, 'European HL7 messages of type A03' there.
- Pushing those rules into HAProxy ACLs or VirtualService matches does not scale: domain experts own them, they change often, and they depend on the payload, not just the envelope.
- The pattern: an in-app router (a Kafka consumer, Wolverine routing, a custom dispatcher) calls a rule engine (NRules) and routes on the result.
- It runs inside one service, behind the mesh — not on the network. The mesh still does mTLS, retries and locality; the rule engine just decides where to send the message next.

p. 170

> Pivot from network-layer routing to in-app routing. The threshold: if the decision fits in a few YAML lines and depends only on the envelope, do it at the mesh. If it depends on the payload, needs a decision table that domain experts edit, or involves many intersecting conditions, push it into the app.
>
> The classic example is HL7 healthcare messages, routed by patient class, encounter type and message subtype: dozens of conditions a non-developer maintains. That belongs in a rule engine, not a VirtualService. In-app routing sits behind the mesh and complements it.
>
> In .NET the router is a plain Confluent.Kafka consumer (or Wolverine's routing), and NRules (MIT, Rete-based, the same algorithm as Drools) is the open-source decision engine. The rule-based-routing slide shows them together.

## [195] APPENDIX I · L7 ROUTING · .NET + Confluent.Kafka + NRules: rule-based routing (sldId 450)

A Kafka consumer owns the plumbing; NRules owns the decision logic; the whole thing runs in-process behind the Istio mesh.

p. 171

> The .NET take on rule-based routing. Inputs arrive over REST, gRPC or Kafka and land in a Confluent.Kafka consumer, which does two things: it enriches the message with context from an HTTP lookup (customer, region, tier), then evaluates the enriched fact in an NRules session.
>
> NRules is an MIT-licensed Rete rules engine, the algorithm Drools uses. Rules are C# classes with a fluent Match/Do API, so the IDE catches typos and the test runner runs them, or external NRules.Language files when domain experts edit the rules on their own. The rules set a WhereTo property on the fact, and the consumer dispatches to each destination: a Kafka topic or an HTTP endpoint.
>
> Everything runs in the ASP.NET Core Pod, with no separate rule server, behind Istio, which still owns mTLS, retries and locality. The running example keeps the rules in a runtime-editable table instead of NRules; the shape is the same.

## [196] APPENDIX I · L7 ROUTING · A Kafka consumer in .NET, calling NRules (sldId 451)

[chip] csharp · .NET 10 + Confluent.Kafka + NRules

```csharp
// NRules + Confluent.Kafka — the consumer enriches, evaluates, dispatches.
// ... record OrderFact(OrderId, AmountCents, Customer) with a settable WhereTo
public class OrderRouter(HttpClient http, ISessionFactory rules,
                         IProducer<Null, string> producer)
{
    public async Task Route(OrderInbound msg)
    {
        var customer = await http.GetFromJsonAsync<Customer>(          // 1) enrich
            $"http://customer-svc/lookup/{msg.OrderId}") ?? throw new NotFoundException();
        var fact = new OrderFact(msg.OrderId, msg.AmountCents, customer);
        var session = rules.CreateSession();     // 2) evaluate; one session per message
        session.Insert(fact); session.Fire();    // matching rules set fact.WhereTo
        var body = JsonSerializer.Serialize(msg); // 3) dispatch: kafka:<topic>, http:<url>
        foreach (var dest in (fact.WhereTo ?? "kafka:orders.default").Split(','))
        {
            var parts = dest.Split(':', 2);
            if (parts[0] == "kafka")
                await producer.ProduceAsync(parts[1],
                    new Message<Null, string> { Value = body });
            else if (parts[0] == "http")
                await http.PostAsync(parts[1],
                    new StringContent(body, Encoding.UTF8, "application/json"));
        }
    }
}
```

enrich → NRules evaluate → dispatch to Kafka or HTTP: the content-based router, with the decision externalised to NRules.

p. 172

> The .NET reading of the Camel and Drools pattern, on Confluent.Kafka. OrderRouter takes an HttpClient for enrichment and destinations, an NRules ISessionFactory, and a producer.
>
> The flow: enrich the message by calling customer-svc (attach Polly pipelines through Microsoft.Extensions.Http.Resilience, as in Appendix E); create a session per message, because sessions are not thread-safe; insert the fact and call Fire(), which runs every rule whose pattern matches and sets WhereTo; then dispatch to each destination, producing to a Kafka topic or posting to an HTTP endpoint.
>
> NRules.Language, also MIT, parses an external rule file into the same model, so domain experts can change routing without rebuilding the consumer; the NRules rule slide shows the C# class form. The EIP semantics match Apache Camel; the API is C#-native.

## [197] APPENDIX I · L7 ROUTING · An NRules rule: the decision, externalised (sldId 452)

[chip] csharp · NRules.Fluent (or external NRules.Language DSL)

```csharp
[Name("High-value VIP orders go to the priority queue")]
public class HighValueVipRule : Rule
{
    public override void Define()
    {
        OrderFact order = default!;            // declare the fact binding
        When()
            .Match<OrderFact>(() => order,
                f => f.AmountCents > 50_000,
                f => f.Customer.Tier == "VIP");
        Then()
            .Do(ctx => order.WhereTo = "kafka:orders.priority,http:notify-vip");
    }
}
// ... EuropeanOrderRule: Customer.Region == "EU" sets WhereTo = "kafka:orders.eu"
[Name("Default route")] [Priority(-100)]    // salience equivalent — fires last
public class DefaultRouteRule : Rule
{
    public override void Define()
    {
        OrderFact order = default!;
        When().Match<OrderFact>(() => order, f => f.WhereTo == null);
        Then().Do(ctx => order.WhereTo = "kafka:orders.default");
    }
}
```

Each rule is a small business statement: when X is true, then route to Y. Compile-time-checked, IDE-friendly, unit-testable — or move to NRules.Language for domain-expert ownership.

p. 173

> NRules rules are 'When/Then' statements, structurally identical to Drools 'when/then'. When().Match<T>() is a pattern match against facts in the working memory (here, OrderFact), with one or more predicates that all must hold. Then().Do() is the action — in our case, setting the WhereTo property the router will consume. Two real rules and a default with Priority -100 (salience equivalent) so it fires last if nothing else matched. The point isn't the syntax: these rules are first-class C# classes (type-safe, refactor-friendly, unit-testable through NRules.Testing) and live in their own .csproj. For domain experts who'd rather work outside C# (closer to the Drools .drl experience), NRules.Language is a separate sub-project that parses an external DSL into the same rule model, so non-developers can edit and redeploy the rule file without rebuilding the consumer. Decision tables: if your rules fit a spreadsheet shape (the DMN sweet spot), the .NET ecosystem doesn't ship a strong open-source DMN runtime; the pragmatic answer is to run Apache KIE (Kogito) DMN as a separate service and call it via REST from the same enrichment step, or implement the table convention in NRules. The toolkit appendix (Appendix J) lists that gap.

## [198] APPENDIX I · L7 ROUTING · Every L7 hop costs time (sldId 453)

Typical p50/p99 added per stage — the budget you spend before your service even runs.

p. 174

> Set expectations with the numbers. Each L7 capability has a typical cost: TLS termination is sub-2ms, path/header routing is sub-1ms, auth/JWT validation is a few ms, WAF a few more, mesh sidecar another millisecond per hop, rate-limit Redis lookup is a couple of ms. Body inspection is the outlier — it can be 5 to 50 ms depending on size, which is why we say to use it sparingly. The numbers are typical, not authoritative; profile your own stack. The right-side card has the working heuristic: stay under ~10ms total L7 on hot paths. With four layers (edge, gateway, mesh sidecar in, mesh sidecar out), every layer must be lean and justify its latency. The retry-storm discipline from Appendix E applies here too — timeouts must account for the total L7 budget plus the service's own work, or retries will pile up.

## [199] APPENDIX I · L7 ROUTING · L7 pitfalls and how to avoid them (sldId 454)

- Too many hops: edge → gateway → ingress → mesh sidecar in → mesh sidecar out adds up fast. Collapse layers that aren't earning their place.
- Regex-heavy ACLs / matches: each regex evaluation is real CPU. Prefer exact / prefix matches; use regex only when needed.
- Sticky sessions break elasticity without any error: the auto-scaler can't rebalance, restarts are painful, scale-to-zero is gone.
- Body inspection on every request: blows memory, kills streaming. If you must transform bodies, do it on a small percentage or just at the edge.
- Sync auth lookups on the hot path: cache validated tokens, validate JWT signatures locally, never do a per-request DB lookup for identity.
- Misaligned timeouts and retries between layers — a 30s gateway timeout + 3 mesh retries with 10s each = a retry storm at the bottom (see Appendix E).

p. 175

> Run quickly through the failure modes. The hop-count one is the most common: every layer feels free until you measure p99 — then you realise the request crossed seven proxies. The regex point is a perf footgun many people miss. The sticky-session one ties back to the sticky-sessions comparison. Body inspection is the latency-budget killer. The auth-lookup one is the most common cause of cascading slowdowns under load. And the timeout-misalignment is the gateway-to-mesh-to-service version of the retry storm we covered in Appendix E — the lesson is identical: bound retries, align timeouts top-down, give the deepest layer the strictest budget.

## [200] APPENDIX I · L7 ROUTING · East / West: L7 between services, inside the mesh (sldId 455)

Every service-to-service call is L7-routable through the sidecars.

p. 176

> Most L7 decisions in a microservices system don't happen at the edge — they happen east/west, between services, every time service A calls service B. The mesh's sidecar pair handles that traffic: mTLS between services (encryption and identity), HTTP/2 multiplexing, native gRPC support, retries with backoff and jitter, outlier detection (eject misbehaving pods automatically), locality-aware load balancing (prefer same-zone pods to keep RTT low), header-based routing and canary weights for east/west versions, plus rich per-call traces and metrics. The headline is the second box: all of that, per call, with no app code. Application services keep talking plain HTTP or gRPC; the sidecars make it secure, reliable and observable in flight. This is the modern answer to 'how do you build a microservices system that works in production.'

## [201] APPENDIX I · L7 ROUTING · Why east/west L7 matters (sldId 456)

- Internal traffic dominates: in a microservices system the volume of east/west calls dwarfs north/south by 10x or more.
- Security: mTLS everywhere by default — every internal call has an identity, encryption and an audit trail without per-service code.
- Resilience: timeouts, retries, circuit breakers and outlier ejection live in the sidecar, applied uniformly to every internal hop.
- Observability: every internal call gets a span, latency histogram and per-route success rate — the request lifecycle from section 11, populated automatically.
- Locality: prefer same-zone or same-region pods so internal RTT stays in single-digit milliseconds, and graceful failover when a zone goes.
- Routing decisions: header-based canaries and weighted releases work east/west too — you can canary a backend service that has no external traffic at all.

p. 177

> Hammer the volume point first: most production L7 routing happens between services, not at the edge. The security argument is the one that justifies the mesh on its own — mTLS everywhere is otherwise hard to retrofit. The resilience and observability arguments are the operational ones; you stop writing the same boilerplate in every service. Locality is the perf argument: with the right Istio config, two pods in the same zone talk over a few milliseconds; cross-region traffic gets degraded gracefully. And the last point is non-obvious but important: canary releases of a deeply internal service (say, a payments calculation engine that no client touches directly) are possible because the mesh can split east/west traffic by weight — you cannot canary internal services through an edge LB.

## [202] APPENDIX I · L7 ROUTING · Istio for east/west: DestinationRule + VirtualService (sldId 457)

[chip] yaml · Istio east/west

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata: { name: payments }
spec:
  host: payments.acme.svc.cluster.local
  trafficPolicy:
    # ... connectionPool: http2MaxRequests 1000, maxRequestsPerConnection 10
    outlierDetection:                              # eject bad pods
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
    # ... loadBalancer: localityLbSetting enabled (prefer same zone)
  subsets:
  - { name: v1, labels: { version: v1 } }
  - { name: v2, labels: { version: v2 } }
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: payments }
spec:
  hosts: [payments.acme.svc.cluster.local]            # internal DNS — east/west
  http:
  - route:
    - { destination: { host: payments, subset: v1 }, weight: 95 }
    - { destination: { host: payments, subset: v2 }, weight: 5 }
```

Same CRDs as north/south, but pointed at an internal host — outlier detection, locality LB, canary weights, all between services with no app code.

p. 178

> Same Istio primitives as the weighted canary, but applied to an internal service (note the cluster.local host). DestinationRule sets up the connection pool (HTTP/2 multiplexing for gRPC), enables outlier detection (5 consecutive 5xxs in 30s ejects the pod), enables locality-aware load balancing (same-zone preferred), and defines version subsets. VirtualService weights east/west traffic 95/5 between v1 and v2 — a canary release of a backend service that no external client knows exists. This is what the 'mesh' is: the same routing CRDs the edge uses, applied everywhere, between every pair of services, configured centrally and enforced by the sidecars.

## [203] APPENDIX I · L7 ROUTING · gRPC east/west specifics (sldId 458)

- gRPC is HTTP/2 under the hood, so it works natively in any L7 router that speaks HTTP/2 (Envoy, Istio, modern HAProxy/Nginx).
- Route by gRPC service.method: the URI path is /package.Service/Method — use a uri prefix match in Istio, grpc_pass in Nginx, or path_beg in HAProxy.
- Header-based balancing matters more for gRPC: connections are long-lived and multiplexed, so least-request or per-request load balancing beats round-robin.
- Streaming RPCs (server-streaming, client-streaming, bidi): retries are dangerous if the stream is non-idempotent — cap retries to UNARY calls in the mesh policy.
- Trailers carry status: a 200 + a non-OK trailer is the gRPC equivalent of a 5xx — outlier detection has to be configured to read trailers, not just the status line.

p. 179

> gRPC has a few sharp edges of its own. Route on the gRPC URI prefix to do per-method canaries. Use least-request (or random-3-choices) load balancing instead of round-robin because gRPC connections are long-lived — a few long-running streams can starve other backends if you round-robin connections instead of requests. Be careful with retries on streaming RPCs: the mesh can retry a UNARY call safely if it's idempotent, but retrying a half-completed streaming RPC will replay half the work — Istio lets you scope retries to specific gRPC status codes and request kinds. And the trailer point is subtle: gRPC returns its real status in HTTP trailers (a 200 with a non-OK gRPC status is a failure), so outlier detection has to know to read those, or it will think a failing service is healthy.

## [204] APPENDIX I · L7 ROUTING · When to use which L7 layer (sldId 459)

- Edge / ingress: TLS termination, host/path routing, WAF, public-facing rate limits. Anything north/south that affects all clients.
- API gateway: cross-cutting product policy — auth, per-consumer rate limits, request transformation, monetisation, key management.
- Service mesh: east/west routing, mTLS, retries, outlier detection, canaries between internal services. The default home for service-to-service L7.
- In-app router (a Kafka consumer + NRules): when routing depends on business rules, payload content, or decisions that domain experts must own.
- Rule of thumb: prefer the lowest layer that can fully express the decision, and never push business rules into mesh CRDs.

p. 180

> This is the decision guide to leave on screen for a beat. The mental model: each layer has a job it's good at, and pushing work to the wrong layer is where complexity comes from. Edge/ingress for the things every client crosses. API gateway for product-shaped policy. Mesh for east/west and everything internal. In-app for business rules. The bold rule of thumb prevents the common antipattern of growing increasingly baroque Istio VirtualService configs to encode rules that domain experts need to maintain — if it's a business rule, it belongs in a rule engine inside a service, not in a network CRD.

## [205] APPENDIX I · L7 ROUTING · L7 routing checklist (sldId 460)

- Pick one ingress, one gateway, one mesh — don't run three competing L7 layers because each team had a favourite.
- TLS terminates at the edge; mTLS between services in the mesh; cert rotation is automatic (cert-manager + SDS), not a quarterly outage.
- Routing rules live in Git, reviewed like code; GitOps reconciles them; rollback is a git revert.
- Every L7 layer emits traces and metrics — sample the spans, alert on per-route SLOs, watch for retry budget exhaustion.
- Stickiness is an exception, not a default; business rules belong in a rule engine inside a service, not in network YAML.
- Test under load and under failure: bring a pod down, eject a zone, ramp a canary, verify the mesh does what the YAML says.
  - References: HAProxy / Nginx / Envoy docs; Istio traffic management guide; Confluent.Kafka .NET client documentation; NRules documentation (Fluent API + NRules.Language + NRules.Testing); YARP docs for the reverse-proxy library. For DMN specifically, the Apache KIE (Kogito) DMN docs — run as a separate service called over REST when you need decision tables.

p. 181

> Leave the checklist up at the end. The first point is the most common organisational failure — a cluster ends up running three ingress controllers because three teams each picked one. Pick one and standardise. The cert-rotation point is the one teams underestimate — expired certs are still a top-3 outage cause in many shops. GitOps for routing is the operational discipline that makes the whole thing reviewable. Observability and the load/failure-test point are non-negotiable. The references sub-bullet is the reading list: official docs for each piece, plus the NRules samples. The architecture itself is language-neutral — the same pattern lives behind any service-mesh stack in any language; we've just made it concrete in .NET.

## [206] Appendix J · .NET 10 Toolkit & Migration (sldId 461)

J

Pinned stack, expanded migration table, known gaps.

> Appendix J is the reference appendix — the tables you keep open in another window while you build. Three diagrams: every NuGet library in your csproj, every cloud-native platform component your Pods rely on, and an expanded version of the Section 1 bridge diagram with concrete migration rationale. Then the gaps in the .NET cloud-native story, and a short closing recipe to start a new cloud-native service. Built specifically for the .NET-developers-moving-from-Windows audience this whole deck is aimed at.

## [207] APPENDIX J · TOOLKIT · The pinned .NET 10 toolkit (sldId 462)

Every library in your csproj: purpose, license, NuGet package. All MIT, Apache 2.0 or BSD-3; no cloud-vendor lock-in.

p. 182

> The application-side bill of materials: every NuGet library used in the deck, grouped by concern, each MIT, Apache 2.0 or BSD-3, with no commercial-only dependency and no cloud-only service.
>
> Highlights: Microsoft.AspNetCore.OpenApi and SignalR are part of ASP.NET Core 10; Confluent.Kafka 2.16.0 is the Kafka client for every producer and consumer, chosen because it keeps the Kafka semantics visible (MassTransit was dropped: it hides those semantics and moved to a commercial license in version 9); Streamiz.Kafka.Net 1.8.2 is the Kafka Streams model in .NET, so windowed aggregations need no Flink cluster; Temporalio pairs with the Temporal Server for durable workflows; Stateless covers the lightweight state-machine slot; NRules covers rules; YARP and Wolverine appear where they fit.
>
> The running examples pin every package exactly on .NET 10.0.12: OpenTelemetry 1.19.1, EF Core 10.0.12 with Npgsql.EntityFrameworkCore.PostgreSQL 10.0.3, HybridCache 10.10.0, Grpc 2.84.0, StackExchange.Redis 3.4.0, HotChocolate 16.6.8, OpenFeature 2.14.1. Everything runs on plain Kubernetes; nothing requires a cloud-specific service.

## [208] APPENDIX J · TOOLKIT · The pinned cloud-native platform stack (sldId 463)

The cluster-side OSS components your .NET Pods rely on — standard CNCF-friendly stack.

p. 183

> The platform half of the bill of materials. These components are what your .NET Pods talk to — the substrate the cluster provides. None of them know or care that your services happen to be .NET; the same stack would serve a Spring Boot, Quarkus or Python deployment identically. That's the point: the .NET library choices in the toolkit table are entirely separable from the platform choices on this one. If you're already running this platform with a Java or Python application, you can drop .NET services in alongside without changing anything under the application layer. A few callouts: Strimzi is the Kubernetes-native Kafka operator (open-source, Apache 2.0); Apicurio is the open-source schema registry that holds your OpenAPI / .proto / Avro contracts; OpenMetadata is the asset-catalog/lineage tool; LGTM (Tempo + Mimir + Loki + Grafana) is Grafana Labs' open-source observability stack (note the AGPL-3.0 licensing if that's a concern for you); PostgreSQL is the primary OLTP store; Redis (or its BSD-licensed Valkey fork) is the SignalR backplane and distributed-lock substrate; Temporal Server pairs with the Temporal .NET SDK from the application stack. The bottom line: standard cloud-native stack, your .NET Pods are just one workload type running on it.

## [209] APPENDIX J · MIGRATION · From Windows / .NET 4.x to Kubernetes / .NET 10 (sldId 464)

Concrete patterns, side by side, with a one-line rationale per row. Print this and keep it on your desk.

p. 184

> The expanded version of the bridge diagram from Cloud-Native Principles, a 22-row table with four columns: the concern, what you came from in the Windows world, what it becomes in the cloud-native world, and what changes most. Read the rightmost column first; that is where the architectural shift lives.
>
> Almost every row keeps the shape of the pattern (request handlers, background workers, scheduled jobs, distributed locks, health checks, configuration, telemetry) and changes who owns the substrate. IIS owned the host; Kubernetes does now. MSDTC owned distributed transactions; the saga and outbox do. MSMQ owned messaging; Kafka with Confluent.Kafka does. Active Directory owned service identity; SPIFFE and mTLS through Istio do. Performance counters and the Event Log owned telemetry; OpenTelemetry with Loki, Tempo and Mimir does.
>
> Two rows are conceptual rewrites, not substrate swaps. COM+ and MSDTC distributed transactions become sagas, with compensations written explicitly because there is no two-phase commit across services. BizTalk orchestration becomes a Temporal workflow or a Kafka consumer with NRules routing: orchestration is C# in your repository, not an artifact in a separate runtime.

## [210] APPENDIX J · GAPS · What the .NET cloud-native story lacks (sldId 465)

- Native DMN runtime — .NET doesn't ship an open-source DMN (Decision Model and Notation) engine. If you need spreadsheet-style decision tables for non-developers, run a DMN engine such as Apache KIE (Kogito) as a separate service and call it over REST from your enrichment step. NRules covers the rule-engine slot but not the DMN UX.
- Apache Camel ecosystem — nothing in .NET matches the breadth of Camel's 300+ component connectors. For integration with long-tail systems (HL7, AS2, EDI, mainframe connectors) you may still want a Camel sidecar in a JVM Pod.
- Stream processing — Streamiz.Kafka.Net is excellent but is one project (one maintainer, MIT) compared to Kafka Streams' larger contributor base. Flink remains the heavyweight option — typically as a separate JVM service if your stream workloads are central.
- DI complexity — Microsoft.Extensions.DependencyInjection is simple by design. For property injection, decorators, or advanced lifetime scopes, look at Autofac (MIT) or Lamar (MIT) — both drop-in replacements.
- MediatR is no longer open source — it moved to a commercial license in 2025. Wolverine (MIT) is the modern OSS equivalent; consider it for new projects.
- These are real gaps with known workarounds: in each case there is either a workable .NET path or a polyglot path. The .NET cloud-native story is solid for >95% of cases; the remaining 5% is where you mix runtimes or accept a different trade-off.

p. 185

> Every ecosystem has gaps; naming them keeps trust. (1) DMN: the closest open-source option in .NET is a decision-table convention on top of NRules; for spreadsheet authoring, decision-table semantics and the FEEL expression language, run Apache KIE (Kogito) as a separate service.
>
> (2) Camel breadth: Apache Camel has about 300 components, from HL7 over MLLP to FTP and mainframe gateways. An integration shop with heavy mainframe, EDI or HL7 needs may run Camel in a JVM Pod and call it from .NET. (3) Streamiz scale: it works well, but its maintainer count and ecosystem are smaller than Kafka Streams'; if streams are central, plan for that.
>
> (4) DI: Microsoft.Extensions.DependencyInjection is simple enough that complex patterns sometimes want Autofac. (5) Licensing moves: MediatR and MassTransit both moved to commercial licenses; many teams pick Wolverine (MIT) to replace MediatR, and this deck uses Confluent.Kafka directly instead of MassTransit. For LOB and SaaS workloads these gaps rarely bite; for integration platforms or heavy stream processing, plan for a polyglot runtime.

## [211] APPENDIX J · RECIPE · The five-line recipe for a new .NET 10 cloud-native service (sldId 466)

- 1. dotnet new web; add Microsoft.AspNetCore.OpenApi, Microsoft.Extensions.Diagnostics.HealthChecks.EntityFrameworkCore, OpenTelemetry.Extensions.Hosting. AddHealthChecks with AddDbContextCheck, MapHealthChecks at /healthz and /readyz; expose ActivitySource-based telemetry from line one.
- 2. Pick exactly the protocols you need: ASP.NET Core minimal APIs for REST at the edge, Grpc.AspNetCore for internal service-to-service, HotChocolate only if you need GraphQL aggregation. Don't surface all three by default.
- 3. For data: EF Core for the OLTP store, with the outbox table in the same DbContext as your aggregates. Add Debezium to Kafka via Strimzi. Produce and consume with Confluent.Kafka directly; it keeps the Kafka semantics (keys, partitions, offsets) visible.
- 4. For state across calls: Temporal .NET SDK if the saga is durable, long, or cross-service; Stateless if it's small and in-process. Persist every transition; never trust in-memory state to survive a Pod restart.
- 5. Ship it on Kubernetes with KEDA scaling on lag (Kafka) or RPS (HTTP); behind Istio for mTLS and retries; with OpenTelemetry exporting to LGTM. Use Asp.Versioning for media-type evolution; never invent your own.
  - Six libraries get you 95% of the way: ASP.NET Core, EF Core, Confluent.Kafka, Temporalio, OpenTelemetry, Polly. Add NRules / Streamiz / HotChocolate / SignalR per workload — only when the use case earns them.

p. 186

> Close the appendix with an opinionated recipe. The order of the five steps is the point: instrument first (factor XI and observability), then choose the protocol surface (avoid the one-of-each trap), then settle data ownership (outbox plus DbContext), then choose the workflow tier (Temporal or Stateless), then deploy with the cluster doing the heavy lifting.
>
> The six-library sub-bullet is the one to leave up: a new .NET cloud-native service that starts with those packages, on the platform stack from the platform table, has most of the patterns in this deck working from day one. SignalR, Streamiz, NRules and HotChocolate are opt-in per workload. The audience leaves with a recipe and the reference tables.

## [212] Appendix K · Monolith to Microservices (sldId 467)

K

Patterns that survive the migration with the system still running.

> Appendix K covers the migration patterns. The thesis: you don't decompose a monolith by stopping it and rewriting; you decompose it incrementally, one bounded asset at a time, with the system serving users the whole way through. We'll walk through the monolith as the starting point, modular monoliths as a frequently-correct destination, the strangler-fig family for progressive extraction, content-based routing for fine-grained cutover, and the decorating collaborator for wrapping legacy code you can't touch. Code in this appendix uses ASP.NET Core 10 + typed HttpClients (IHttpClientFactory) + StackExchange.Redis + Confluent.Kafka, but the patterns are language-neutral.

## [213] APPENDIX K · MONOLITH · A monolith is a unit of deployment (sldId 468)

One process, one binary, one heartbeat. All modules live or die together. Often the right starting point — don't be ashamed of it.

p. 187

> Define the term before fixing it. A monolith is not a code-organisation problem — it's a deployment-organisation property. Even a well-organised ASP.NET Core codebase with clear Controllers, Services, and 1000 unit tests is a monolith if it ships as one image on one heartbeat. The defining property: change anywhere, redeploy everything; a bug in Reporting can take down Payments; one scaling unit for workloads that scale differently. Monoliths are not always wrong. For new products, small teams, or anything that fits in one team's head, they're often the simplest and fastest path to value — especially with .NET 10's fast cold-start. Premature decomposition is its own anti-pattern. The conversation is: when does this monolith start hurting more than it helps?

## [214] APPENDIX K · MODULAR MONOLITH · The modular monolith — often the right destination (sldId 469)

Still one deployable, but with strict in-process module boundaries enforced by build tooling — not by gentlemen's agreement.

p. 188

> The intermediate pattern that's often the right destination, not a stepping stone. Modules within one .NET process have clear public APIs and private internals that other modules cannot reach. In the .NET world, enforcement uses multi-project solutions: each module is a separate .csproj with explicit ProjectReference graphs in CI — ArchUnitNET tests the dependency rules. .NET 8+ also added internal-by-default semantics for new project templates which helps enforce module-internal types. The .NET ecosystem doesn't ship a runtime module-graph framework out of the box, but the discipline is identical — separate projects, internal types per assembly, ArchUnitNET in CI. Modules can share a database, but each owns a schema and no cross-schema joins are allowed.

## [215] APPENDIX K · DECOMPOSED DBS · Modular monolith with decomposed databases (sldId 470)

Data ownership becomes per-module — the hardest part of the split, done while still one process. The next step is mechanical.

p. 189

> Splitting the database is the hard part of decomposition. Do that work while you're still one .NET process. Each module gets its own EF Core DbContext, its own DataSource, its own EF Migrations history. ASP.NET Core makes this clean — multiple AddDbContext<TContext> registrations in Program.cs, each pointing at its own connection string from configuration (appsettings.json sections or environment variables), each module's repositories typed against the right DbContext. Cross-module data is now async or event-driven (an in-process event dispatcher such as Wolverine for module events, Confluent.Kafka for cross-service events). Once this is done, promoting a module to a separate service is a refactor of the deployment topology, not a data-migration project.

## [216] APPENDIX K · STRANGLER FIG · Identify → move → redirect (sldId 471)

Named after the strangler fig vine: grow the new system around the old until the old can be removed.

p. 190

> The Martin Fowler strangler-fig pattern. The three steps you repeat. Identify: pick a bounded asset — 'order creation' or 'order status query' specifically. The smaller the better. Move: build the new ASP.NET Core service alongside the monolith, replicate the behaviour, test it in parallel without production traffic (often by shadowing reads through the new service and comparing outputs in a side-by-side test harness). REDIRECT: switch callers to the new service. Each cycle is independently reversible — if the new service is wrong, redirect back. There are three ways to do the redirect: via a proxy, via a proxy plus partial routing, or via a shared database.

## [217] APPENDIX K · STRANGLER FIG · With a proxy — step zero of every migration (sldId 472)

Introduce the routing layer first, before extracting anything. Then redirection becomes a config change, not a release.

p. 191

> The pre-condition for incremental migration: clients hit the proxy, the proxy forwards to the monolith. Day zero, behaviour is unchanged. But you now have the lever — the proxy is where you'll later route 1% of /orders/* traffic to the extracted .NET service, then 5%, then 100%. Without this step, every cutover is a coordinated client release. With it, every cutover is a proxy config change. For .NET deployments this is typically nginx, Envoy, or Istio gateway as a Kubernetes Service ahead of your application Pods — or YARP (the Microsoft-built reverse proxy library, MIT licensed) as an in-app gateway if you prefer C# control of routing.

## [218] APPENDIX K · STRANGLER FIG · With proxy + redirection (sldId 473)

The proxy splits traffic between the new service and the shrinking monolith. Roll forward by widening the route; roll back by narrowing.

p. 192

> The proxy is what makes this work: by path, by header (X-Tenant: acme), by percentage (1% canary), or by feature flag (Microsoft.FeatureManagement). The new ASP.NET Core service handles its slice; the monolith handles everything else. Clients still see one URL. Roll forward by widening; roll back by narrowing. The new service can fail completely and the monolith picks up — bounded blast radius is the whole point. Instrument both paths via OpenTelemetry so you can verify the new service produces the same outcomes as the monolith before widening. For .NET deployments this typically lives in Istio VirtualService rules, nginx server blocks, or YARP RouteConfig + cluster predicates.

## [219] APPENDIX K · STRANGLER FIG · With a shared database — a deliberate intermediate state (sldId 474)

Process boundary first, data boundary later. Useful intermediate state, not a destination. Schema coupling will bite eventually.

p. 193

> Sometimes the data split is too risky to do at the same time as the process split. The new .NET service and the monolith share a database for a while. Both apps read and write the same tables; the new service owns the API but not the data. Useful for extracting reads first, or as a stepping stone. It is an intermediate state, not a destination: every EF Core migration now needs both apps to agree, and the coordination tax grows. The next step is to give the new service its own store: CDC out of the monolith's DB into the new service's via Debezium (running as a Kafka Connect connector), or dual-writing during a brief sync window, or event-sourcing the data into the new service via Marten / EventStore.

## [220] APPENDIX K · ROUTING · Content-based routing during migration (sldId 475)

[chip] csharp · ASP.NET Core 10 minimal API + IHttpClientFactory

```csharp
// ASP.NET Core minimal API + IHttpClientFactory — content-aware proxy that
// reads the request body and forwards to the new service or the monolith.
// Program.cs
builder.Services.AddHttpClient("monolith", c => c.BaseAddress = new("http://monolith.svc:8080"));
builder.Services.AddHttpClient("orders",   c => c.BaseAddress = new("http://orders.svc:8080"));
builder.Services.AddHttpClient("ordersEu", c => c.BaseAddress = new("http://orders-eu.svc:8080"));
app.MapPost("/orders", async (HttpContext ctx, IHttpClientFactory factory) =>
{
    var body = await ctx.Request.ReadFromJsonAsync<JsonObject>()
                  ?? throw new BadHttpRequestException("empty body");
    // decide by payload content, not URL
    var tenant = body["tenant"]?.GetValue<string>() ?? "";
    var region = body["region"]?.GetValue<string>() ?? "";
    var upstream = (tenant, region) switch
    {
        ("acme", _) => factory.CreateClient("orders"),    // new service
        (_, "EU")  => factory.CreateClient("ordersEu"),  // regional
        _           => factory.CreateClient("monolith")   // default: legacy
    };
    using var response = await upstream.PostAsJsonAsync("/orders", body);
    return Results.Stream(
        async stream => await response.Content.CopyToAsync(stream),
        response.Content.Headers.ContentType?.ToString());
});
```

Read the body, decide by content (tenant / region / feature flag), forward via IHttpClientFactory named clients.

p. 194

> The .NET shape. Three named HttpClients registered via IHttpClientFactory — the canonical pattern for managed HttpClient lifetimes in ASP.NET Core (per-request socket reuse, DNS refresh, Polly resilience policies, OpenTelemetry instrumentation all attach here). The minimal API reads the body as a JsonObject (System.Text.Json), inspects payload fields, and uses a C# switch expression to pick the upstream. PostAsJsonAsync is the one-line serialize+POST. The decision is by payload content: tenant, region, feature flag — not URL pattern. For .NET running behind a real proxy (nginx, Envoy, Istio, YARP), express the same logic in Lua / WASM filters at the gateway. The CPU cost of body parsing is the only real downside — over months it adds up; over a migration window of weeks it's irrelevant compared to the risk control it buys. Add Polly resilience pipelines (Microsoft.Extensions.Http.Resilience) on the AddHttpClient lines for retry / circuit-breaker / timeout on the upstream calls.

## [221] APPENDIX K · DECORATOR · The decorating collaborator (sldId 476)

The new service wraps the legacy one, adds capability, then becomes the API. Useful when you can't modify the legacy code.

p. 195

> Different from the proxy patterns: the decorator owns behaviour, not only routing. The new ASP.NET Core service sits in front of the legacy API and adds cross-cutting capability: a Redis cache, Kafka events with Confluent.Kafka, audit logging, validation, enrichment, rate limiting, OpenTelemetry metrics. The legacy service is unaware.
>
> Clients talk to the decorator's API, which delegates the underlying work and contributes everything else. It is most useful when the legacy system is a third-party product, a vendor system, or fragile code you may not touch. The decorator is a full .NET microservice with its own deploy, scaling and data; the running example builds it on StackExchange.Redis and Confluent.Kafka.

## [222] APPENDIX K · DECORATOR · A decorating collaborator in ASP.NET Core (sldId 477)

```
csharp · ASP.NET Core 10 + StackExchange.Redis + Confluent.Kafka
```

```
// Wraps the legacy /orders API: Redis cache, Kafka events.
app.MapGet("/orders/{id}", async (string id, HttpContext ctx) =>
{
    var cached = await redis.GetDatabase().StringGetAsync($"order:{id}");
    if (cached.HasValue)                                                  // 1. cache hit
        return Results.Content(cached!, "application/json");
    var resp = await legacyClient.GetAsync($"/orders/{id}");              // 2. legacy fallback
    var json = await resp.Content.ReadAsStringAsync();
    await redis.GetDatabase().StringSetAsync(
        $"order:{id}", json, TimeSpan.FromSeconds(60));                   // 3. populate
    return Results.Content(json, "application/json");
});
app.MapPost("/orders", async (HttpContext ctx) =>
{
    using var body = await JsonDocument.ParseAsync(ctx.Request.Body);
    var resp = await legacyClient.PostAsync("/orders",
        new StringContent(body.RootElement.GetRawText(), Encoding.UTF8, "application/json"));
    var json = await resp.Content.ReadAsStringAsync();
    using var order = JsonDocument.Parse(json);
    var orderId = order.RootElement.GetProperty("id").GetString()!;
    await producer.ProduceAsync("order.placed",                           // Confluent.Kafka
        new Message<Null, string> { Value = json });
    await redis.GetDatabase().KeyDeleteAsync($"order:{orderId}");         // invalidate cache
    return Results.Content(json, "application/json", statusCode: 201);
});
```

The decorator adds caching, event emission — capabilities the legacy service can't add on its own.

p. 196

> The running example's decorator: an ASP.NET Core minimal API in front of the legacy /orders API, with StackExchange.Redis for the cache and Confluent.Kafka for events.
>
> The GET path is cache-aside: try Redis, fall back to the legacy service on a miss, populate the key with a 60-second TTL. The POST path delegates to the legacy service, which stays the source of truth, then produces order.placed and deletes the cached entry so the next read is fresh.
>
> The legacy service has no idea it is wrapped. Over time you move more behaviour into the decorator (validation, idempotency keys, deduplication, multi-source reads); when the legacy service retires, the decorator owns the storage and the API clients see does not change.

## [223] APPENDIX K · DECISIONS · Choosing the right migration pattern (sldId 478)

- Modular monolith first, microservices later — with multi-project .NET solutions and ArchUnitNET enforcing module boundaries, the cheapest decomposition is often inside one ASP.NET Core process. Many systems never need to leave this state.
- Decompose the database before decomposing the deployment. The data split is the hard part; doing it with multiple AddDbContext<T> registrations is much cheaper than coordinating across services.
- Always introduce the proxy first (YARP, nginx, or Istio) — the routing layer is what makes incremental cutover possible. No proxy = no incremental migration.
- Strangler with shared database is a transition state. Plan its end before you start it. EF Core migration coordination is debt that accrues.
- Content-based routing when you need to cut over by tenant / region / segment instead of by URL. Costs CPU at the proxy; buys precise risk control.
- Decorating collaborator when you need to add behaviour to a system you can't modify. Most useful for vendor / 3rd-party / legacy-mainframe wrappers.
- Reversibility is the design property to optimise for. Every migration step should be undo-able by a config change, not a release.

p. 197

> Close the appendix with the decision rules. The first point is the most important and most often skipped — with multi-project solutions and good build discipline, a modular monolith is frequently a fine destination. Microservices have real operational cost. The second point is the most underrated: the database split is where projects get stuck for years; do it early, while still one .NET process. The third point: no proxy, no incremental migration. The fourth: shared-database strangler is OK as a means but never as an end. The bold final line is the architectural take-home: design for reversibility, so every step is a config change you can undo without coordinating a release. Migrations fail when they reach an irreversible step too early.

## [224] Appendix L · Caching patterns (sldId 479)

L

Six patterns for keeping a cache useful and your data correct.

> Appendix L is the caching reference. Five reasons to cache and six patterns to do it well. The patterns differ in who reads/writes the cache, when, and who owns the consistency story. We use Redis as the canonical cache because it's the default open-source choice on Kubernetes — same patterns apply to in-memory caches or any KV store. Code uses IDistributedCache (Microsoft.Extensions.Caching.StackExchangeRedis) for the standard patterns, IConnectionMultiplexer (StackExchange.Redis) for advanced operations, and HybridCache (Microsoft.Extensions.Caching.Hybrid) for the read-through pattern.

## [225] APPENDIX L · WHY CACHE · Five things a cache earns you (sldId 480)

- Application performance — a cache hit is microseconds; a database round trip is milliseconds. The hot path becomes ~100x faster on hits.
- Backend load — caching shields the database from repeated reads of unchanged data. Read-heavy workloads can offload 80-95% of queries with a sensible TTL.
- Throughput — the same Pod fleet serves dramatically more requests because it spends less time waiting on the DB. Vertical scaling without buying anything.
- Predictable performance — p99 latency stops being a function of DB load. Tail latencies flatten because the hot path doesn't contend on the same lock-bound resource as everyone else.
- Database cost — fewer queries means smaller (or fewer) DB instances, smaller IOPS budgets, less replication bandwidth. Cache is almost always cheaper than the DB tier it offloads.
  - Trade-off: every cache adds a consistency story, an invalidation story, and a failure-mode story. Pick the pattern that matches the consistency you need.

p. 198

> Five concrete reasons that justify the caching investment. Application performance is the user-facing win. Backend load matters more in steady state — shielding the database is what lets your DB tier stay smaller. Throughput follows from both. Predictable performance flattens p99. Database cost often pays for the caching infrastructure. The sub-bullet is what trips teams up: every cache adds complexity; pick the pattern that matches the consistency you need.

## [226] APPENDIX L · CACHE-ASIDE · Cache-aside (look-aside) — the default (sldId 481)

The application reads cache, falls back to DB, populates cache. Explicit and simple; the most common pattern.

p. 199

> The pattern everyone starts with. The ASP.NET Core application is in charge: try IDistributedCache first, on a miss query EF Core, populate the cache on the way back, return. Every other pattern in this appendix differs in who does the work. Pros: explicit, debuggable, no magic. Cons: every read has the if/else; cache miss costs two round trips; cache logic is repeated across services if you don't extract it. The TTL is the consistency knob — longer = fewer DB hits, more stale-read risk. Use when you want explicit control and reads dominate writes.

## [227] APPENDIX L · CACHE-ASIDE · Cache-aside in ASP.NET Core with Redis (sldId 482)

[chip] csharp · ASP.NET Core 10 + EF Core + Redis

```csharp
// Program.cs (excerpt), examples/25-caching/dotnet: cache-aside on a Redis client
app.MapGet("/cache-aside/products/{pid}", async (string pid, CacheContext db) =>
{
    var key = $"ca:product:{pid}";
    var cached = await SafeCacheGet(key);                  // 1. cache lookup
    if (cached is not null)
        return Results.Json(Merge("cache", JsonSerializer.Deserialize<JsonElement>(cached)));
    var product = await db.Products.AsNoTracking().Where(p => p.Id == pid)   // 2. DB on a miss
        .Select(p => ProductDto.From(p)).FirstOrDefaultAsync();
    if (product is null) return Results.NotFound(new { error = "not found" });
    await SafeCacheSet(key, JsonSerializer.Serialize(product, CacheJson.Options)); // 3. fill
    return Results.Json(Merge("db", product));
});
app.MapPut("/cache-aside/products/{pid}",
    async (string pid, ProductUpdate update, CacheContext db) =>
{
    await db.Products.Where(p => p.Id == pid).ExecuteUpdateAsync(s => s
        .SetProperty(p => p.Name, update.Name)
        .SetProperty(p => p.PriceCents, update.PriceCents));
    await SafeCacheDelete($"ca:product:{pid}");            // 4. invalidate
    return Results.Json(new { ok = true, pattern = "cache-aside", action = "invalidated" });
});
```

Try cache; on miss, EF query and populate. Invalidate on write. Three operations; the rest is naming conventions.

p. 200

> Cache-aside as Example 25 runs it: the handler owns the three steps on a StackExchange.Redis client, because the steps are the lesson. SafeCacheGet and SafeCacheSet swallow Redis failures, so a Redis outage falls back to the EF Core query and the read still works (the verify script stops Redis to prove it). The handler tries the cache first, queries EF Core on a miss, populates the cache with a 60-second TTL and tags the answer with its source. The PUT path updates the row with ExecuteUpdateAsync and then removes the cache entry: invalidate-on-write. IDistributedCache is the Microsoft.Extensions.Caching abstraction behind HybridCache on the read-through slide, which adds typed access and stampede protection. For high-cardinality keys, configure Redis with maxmemory-policy allkeys-lru so the cache doesn't grow unbounded.

## [228] APPENDIX L · READ-THROUGH · Read-through — the cache fetches on miss (sldId 483)

Application sees one interface; the cache library handles DB fallback transparently.

p. 201

> The variation where the cache library, not the application, calls the database on a miss. HybridCache (Microsoft.Extensions.Caching.Hybrid, MIT) is the in-box answer: it gives you GetOrCreateAsync with a factory function (the loader), built-in stampede protection and L1+L2 layering (in-memory plus a distributed cache such as Redis). Pros: cleaner application code, single read interface, built-in protection from cache stampedes (no thundering herd). Cons: you're adding a library; less control over what triggers a DB hit. Use when read paths are repetitive and you want declarative caching with safety nets. Alternative with more features: FusionCache (MIT, open-source) adds fail-safe stale fallback, eager refresh and a backplane.

## [229] APPENDIX L · READ-THROUGH · Read-through in ASP.NET Core with HybridCache (sldId 484)

[chip] csharp · ASP.NET Core 10 + HybridCache + Redis (L2)

```csharp
// Program.cs (excerpt), examples/25-caching/dotnet: HybridCache is read-through
// builder.Services.AddStackExchangeRedisCache(o => o.Configuration = redisUrl);   // L2
// builder.Services.AddHybridCache(o => o.DefaultEntryOptions = new HybridCacheEntryOptions
//     { Expiration = 60 s, LocalCacheExpiration = 60 s });
app.MapGet("/read-through/products/{pid}",
    async (string pid, CacheContext db, HybridCache cache) =>
{
    var key = $"rt:product:{pid}";
    var source = "cache";
    var product = await cache.GetOrCreateAsync<ProductDto?>(key, async ct =>
    {
        source = "db";                                     // the loader ran: a miss
        return await db.Products.AsNoTracking().Where(p => p.Id == pid)
            .Select(p => ProductDto.From(p)).FirstOrDefaultAsync(ct);             // loader
    });
    if (product is null) { await cache.RemoveAsync(key); return Results.NotFound(); }
    return Results.Json(Merge(source, product));
});
// A write invalidates both levels: await cache.RemoveAsync(key)
```

GetOrCreateAsync is read-through. The loader runs only on a miss. Built-in stampede protection.

p. 202

> HybridCache (Microsoft.Extensions.Caching.Hybrid, MIT) is the in-box answer for declarative read-through caching: a two-level cache with an in-process L1 and any IDistributedCache as L2, here Redis through AddStackExchangeRedisCache. The registration sets a 60-second expiry for both levels. The endpoint calls GetOrCreateAsync with a loader that runs only on a cache miss, and HybridCache's built-in concurrency control ensures that if 100 concurrent requests hit the same missing key, the loader runs once and the other 99 await the result: no thundering herd. The loader also sets a flag, so the response reports source db for the request that loaded the value and cache for the others. A missing product returns null, which the endpoint removes from the cache again so a later insert is visible at once. When Redis is unreachable, HybridCache logs the L2 failure and still runs the loader. The trade against a hand-written cache-aside: a library dependency, in exchange for typed values, serialization and stampede protection. Alternative: FusionCache (MIT) adds fail-safe stale fallback, eager refresh and a backplane for multi-Pod L1 invalidation.

## [230] APPENDIX L · WRITE-THROUGH · Write-through — cache and DB written synchronously (sldId 485)

Every write hits both the cache and the DB. Cache is never stale; writes pay both latencies.

p. 203

> When stale reads are not acceptable, write-through forces every write to update both stores. The ASP.NET Core handler calls SaveChangesAsync on the DbContext and SetStringAsync on the cache; both must succeed. Pros: a read immediately after a write sees the new value. Cons: write latency is the sum of both stores; you have to handle the case where the cache write succeeds but the DB write fails (or vice versa). The discipline: write the DB first inside a SaveChanges call, write the cache second, accept that a failure between them leaves a brief inconsistency. Short TTL self-heals.

## [231] APPENDIX L · WRITE-THROUGH · Write-through in ASP.NET Core (sldId 486)

[chip] csharp · ASP.NET Core 10 + EF Core + StackExchange.Redis

```csharp
// Program.cs (excerpt), examples/25-caching/dotnet: write-through, DB first then cache
app.MapPut("/write-through/products/{pid}",
    async (string pid, ProductUpdate update, CacheContext db) =>
{
    await db.Products.Where(p => p.Id == pid)               // 1. DB first
        .ExecuteUpdateAsync(s => s.SetProperty(p => p.Name, update.Name)
                                  .SetProperty(p => p.PriceCents, update.PriceCents));
    var product = await db.Products.AsNoTracking().Where(p => p.Id == pid)
        .Select(p => ProductDto.From(p)).FirstOrDefaultAsync();
    if (product is not null)                                // 2. cache second: set, not remove
        await SafeCacheSet($"wt:product:{pid}",
            JsonSerializer.Serialize(product, CacheJson.Options));
    return Results.Json(new { ok = true, pattern = "write-through", action = "set" });
});
// FusionCache flavour — SetAsync writes the value directly.
// L1 (memory) and L2 (Redis) both get updated; backplane invalidates other Pods' L1.
// ... await cache.SetAsync($"product:{id}", p, token: ct);
```

DB first (source of truth), cache second (set, not remove). FusionCache.SetAsync handles L1+L2 + backplane.

p. 204

> Two write-through flavours. The first is Example 25: update the row through EF Core, read it back, then SET the cache with the new value (set, not remove — the difference between write-through and cache-aside-with-invalidate). The second uses FusionCache.SetAsync, which has a significant advantage in multi-Pod deployments: FusionCache's backplane (Redis pub/sub by default) automatically invalidates the L1 (in-memory) cache on all other Pods when one Pod writes — critical because each Pod's L1 cache otherwise has its own stale view. For mission-critical durability, consider transactional outbox: write the cache invalidation event to an outbox table inside the SaveChanges transaction, then Debezium drains it to Kafka, then a consumer invalidates the cache — this guarantees the cache invalidation happens iff the DB transaction commits, at the cost of a brief invalidation delay.

## [232] APPENDIX L · WRITE-AROUND · Write-around — writes skip the cache (sldId 487)

Writes go to the DB only. The next read populates the cache lazily. Good for write-heavy, low-re-read workloads.

p. 205

> When data is written far more often than it's read (audit logs, event records, telemetry), caching every write is wasteful: most cached entries expire before being read again. Write-around solves this: write the DB, leave the cache alone. The next reader pays the cache-miss cost and populates the cache. Pros: no cache pollution by write-only data. Cons: the first read after every write is slow (cache miss); reads of recently-written data are slower than under cache-aside. Pair with cache-aside or HybridCache.GetOrCreateAsync on the read side. Common use: any 'append-only' or 'mostly-written' workload — audit entries, IoT telemetry.

## [233] APPENDIX L · WRITE-AROUND · Write-around in ASP.NET Core (sldId 488)

[chip] csharp · ASP.NET Core 10 + EF Core + Redis

```csharp
// Program.cs (excerpt), examples/25-caching/dotnet: writes skip the cache; reads cache-aside
app.MapPost("/write-around/events", async (EventRequest request, CacheContext db) =>
{
    db.Events.Add(new EventRecord { Id = request.Id, Type = request.Type,
        Payload = request.Payload ?? JsonSerializer.SerializeToElement(new { }) });
    await db.SaveChangesAsync();                           // DB only, cache untouched
    return Results.Json(new { ok = true, pattern = "write-around", action = "db-only" });
});
app.MapGet("/write-around/events/{eid}", async (string eid, CacheContext db) =>
{
    var key = $"wa:event:{eid}";
    var cached = await SafeCacheGet(key);
    if (cached is not null)
        return Results.Json(Merge("cache", JsonSerializer.Deserialize<JsonElement>(cached)));
    var evt = await db.Events.AsNoTracking().Where(e => e.Id == eid)
        .Select(e => EventDto.From(e)).FirstOrDefaultAsync();
    if (evt is null) return Results.NotFound(new { error = "not found" });
    await SafeCacheSet(key, JsonSerializer.Serialize(evt, CacheJson.Options)); // 1st read
    return Results.Json(Merge("db", evt));
});
```

Writes skip the cache; first read populates. Avoids cache thrash from one-time writes.

p. 206

> Write-around: the POST writes to the database only and leaves the cache alone; the GET is plain cache-aside, so the first read after a write populates the cache.
>
> The pattern fits workloads with a high write-to-re-read ratio. A security event log might take 10,000 writes a minute and 100 reads a day for active alerts; caching every write would only churn entries. Compare a product catalog, where every read is a likely hit and write-through makes more sense because readers should see the writer's update at once.

## [234] APPENDIX L · WRITE-BACK · Write-back (write-behind) — fast writes, eventual durability (sldId 489)

Writes return immediately after touching the cache; a background flusher persists to the DB asynchronously.

p. 207

> The fastest-write pattern, with the most caveats. The ASP.NET Core handler writes to Redis and returns immediately — the cache is the source of truth for that window. A background flusher drains the cache to the DB, batching writes for efficiency. Pros: write latency equals cache latency — microseconds, not milliseconds; massive throughput. Cons: a cache crash before the flusher catches up loses unflushed writes; Redis must be configured for persistence (AOF or RDB), and even then you might lose seconds of data. Use only when (a) write throughput is the constraint, (b) eventual durability is acceptable, and (c) you've thought about what 'lost the last 5 seconds of writes' means for your business.

## [235] APPENDIX L · WRITE-BACK · Write-back with a background flusher in ASP.NET Core (sldId 490)

[chip] csharp · ASP.NET Core 10 + StackExchange.Redis + EF Core

```csharp
// Program.cs and CacheWorkers.cs (excerpt), examples/25-caching/dotnet: write-back
app.MapPut("/write-back/metrics/{mid}", async (string mid, MetricRequest request) =>
{
    // ... HSET metric:<mid> {value, tags}; SADD metric:dirty <mid> (503 when Redis is down)
    return Results.Json(new { ok = true, pattern = "write-back", action = "cached-for-flush" },
        statusCode: StatusCodes.Status202Accepted);          // 202: queued, not yet durable
});
builder.Services.AddHostedService<MetricFlusher>();      // the flusher, started with the host
// MetricFlusher : BackgroundService, in ExecuteAsync(CancellationToken stoppingToken):
var failures = 0;
while (!stoppingToken.IsCancellationRequested)
{
    await Task.Delay(Math.Min(FlushPeriodMs << failures, MaxFlushBackoffMs), stoppingToken);
    var ids = await db.SetPopAsync("metric:dirty", 100);      // atomic batch dequeue
    if (ids.Length == 0) continue;
    var failed = new List<RedisValue>();  // Upsert: HGETALL, one ExecuteSqlAsync ON CONFLICT
    foreach (var mid in ids)
        try { await Upsert(mid); await db.HashDeleteAsync("metric:attempts", mid); }
        catch (Exception ex)
        { logger.LogError(ex, "flush failed for {Id}", (string?)mid); failed.Add(mid); }
    if (failed.Count == 0) { failures = 0; continue; }
    failures = Math.Min(failures + 1, 3);                    // back off: 2 s, 4 s, 8 s
    await Requeue(db, failed);   // HINCRBY metric:attempts: dirty again, failed after 5
}
```

A write answers 202 Accepted. A failed flush re-queues its ids with backoff; after five attempts an id is parked on metric:failed.

p. 208

> Write-back in .NET, as Example 25 runs it. PUT /write-back/metrics/{mid} writes the metric fields to a Redis hash, adds the id to a 'dirty set' that tells the flusher what to drain, and answers 202 Accepted in microseconds: the value is queued, not yet durable. The flusher is a BackgroundService registered with AddHostedService, so the host starts it and cancels it on shutdown; each cycle SPOPs up to 100 dirty ids at once. SPOP is the right primitive: it removes and returns elements in one call, so two flusher instances would each get a distinct subset of ids and horizontal scale works. Each id is upserted with one ExecuteSqlAsync statement, INSERT ... ON CONFLICT (id) DO UPDATE, so an id flushed twice stays one row. An id whose upsert fails is re-queued: HashIncrementAsync counts its attempts in metric:attempts and it goes back on the dirty set, or, after five attempts, onto metric:failed with its value still in the cache and the failure in the log; the loop then waits two, four and at most eight seconds between runs. Caveats: this is only safe with Redis persistence (AOF, appendonly yes); without it a Redis crash loses unflushed writes. For data that must not be lost, use write-through. For high-throughput telemetry where losing the last second is acceptable, write-back is what lets the service scale.

## [236] APPENDIX L · REFRESH-AHEAD · Refresh-ahead — keep hot keys warm (sldId 491)

A background task refreshes hot keys before their TTL expires. Users never see a cold miss on popular items.

p. 209

> The pattern for eliminating the cache-miss latency cliff on popular keys. Plain cache-aside has a sharp behaviour: while a key is cached, reads are fast; the moment its TTL expires, the next reader pays the slow DB-fetch path. Refresh-ahead pre-empts this: a BackgroundService watches the cache (or maintains a Redis sorted set of 'hot' keys) and refreshes their values from the DB before the TTL fires. Users always read warm cache. Pros: no user-visible misses on hot keys. Cons: extra DB load for keys that may not be requested again. FusionCache also has 'eager refresh' as a built-in feature — set EagerRefreshThreshold and it'll refresh on access when a value is close to expiry.

## [237] APPENDIX L · REFRESH-AHEAD · Refresh-ahead in ASP.NET Core (sldId 492)

```
csharp · BackgroundService + StackExchange.Redis sorted set or FusionCache eager-refresh
```

```
// Two approaches: (1) BackgroundService + sorted-set hot-key tracking,
// (2) FusionCache built-in EagerRefreshThreshold.
// ... ProductService.FindAsync: ZADD product:hot <now>, then cache-aside on product:{id}
public class HotKeyRefresher(
    IConnectionMultiplexer redis,
    IServiceScopeFactory scopes) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        var r = redis.GetDatabase();
        while (!ct.IsCancellationRequested)
        {
            await Task.Delay(5000, ct);
            // remove keys not touched in 5 minutes; refresh those with low TTL
            var cutoff = DateTimeOffset.UtcNow.AddMinutes(-5).ToUnixTimeMilliseconds();
            await r.SortedSetRemoveRangeByScoreAsync("product:hot", 0, cutoff);
            var hotIds = await r.SortedSetRangeByRankAsync("product:hot");
            // ... for each hot id with a TTL under 10 s: reload from ShopDb, SET with a fresh TTL
        }
    }
}
// Approach 2: FusionCache built-in eager refresh
// builder.Services.AddFusionCache().WithDefaultEntryOptions(o =>
//     o.Duration = TimeSpan.FromSeconds(60)
//      .SetEagerRefresh(0.8f));    // refresh when 80% of TTL elapsed
```

Hot keys live in a Redis sorted set scored by last-access time. Or use FusionCache's built-in EagerRefresh.

p. 210

> Two approaches. Approach 1 uses an explicit sorted-set (ZADD) to track hot keys, scored by last-access timestamp. The FindAsync method touches the hot-set on every read. A HotKeyRefresher : BackgroundService runs every 5 seconds: removes keys not accessed in 5 minutes, then for each remaining hot key checks its TTL via KeyTimeToLiveAsync, refreshes if TTL is below 10 seconds. Use DistributedLock.NET around the refresh loop if you want only one Pod refreshing at a time. Approach 2 is simpler: FusionCache has a built-in 'eager refresh' feature — set SetEagerRefresh(0.8f) and FusionCache will trigger an async background refresh when a value is accessed and has used 80% of its TTL. The user-facing read still returns the cached value (no waiting); the refresh happens in the background. Most production .NET shops use Approach 2 — it's one line of config and FusionCache handles all the locking and stampede prevention. This pattern shines for read-heavy workloads where a small set of keys serves most traffic and miss latency is user-visible.

## [238] APPENDIX L · ANTI-PATTERNS · When not to cache, and what to watch for (sldId 493)

- Don't cache by default. Caching adds a consistency story, an invalidation story, and a failure-mode story. If reads are already fast, just don't add a cache — the cheapest cache is no cache.
- Don't cache rarely-read data. Caching write-once-read-never data thrashes your cache and gains nothing. Profile read patterns first — OpenTelemetry's cache metrics give you hit/miss ratios per cache.
- Don't cache without a TTL. Unbounded caches grow until they evict at random, which gives you the worst type of failure: unpredictable. Always set explicit AbsoluteExpirationRelativeToNow or maxmemory-policy on Redis (allkeys-lru typical).
- Avoid cache stampedes (thundering herd): when a hot key expires and many concurrent ASP.NET Core Pods all miss at once, they all hit the DB. Mitigate with DistributedLock.NET per-key locks, or HybridCache (collapses concurrent misses per Pod), or refresh-ahead, or jittered TTLs.
- Watch for cache aside + write-around without invalidation — the write goes to the DB, but a stale cached value can persist for the full TTL. Always RemoveAsync on writes, or use a short TTL.
- Treat the cache as a performance optimisation, never as the source of truth. A Redis outage must mean slower reads, not data loss — always have an EF Core fallback path. Test this by stopping Redis in staging.

p. 211

> Six things that go wrong with caching. The first point is the most important: caching is a complexity tax, only worth paying when reads hurt. The second is the profile-first rule. The third is operational. The fourth is the cache stampede problem — HybridCache collapses concurrent misses within each Pod out of the box; across Pods, use DistributedLock.NET. The fifth is the most common stale-data bug. The bold final line is the architecturally important one: the cache is never the source of truth. If Redis dies, you must serve slower reads, not return errors. Test this by killing Redis in staging.

## [239] APPENDIX L · DECISIONS · Choosing the right caching pattern (sldId 494)

- Cache-aside — the default. Use when you want explicit control and reads dominate writes.
- Read-through (HybridCache.GetOrCreateAsync) — use when the read path is repetitive and you want declarative caching with built-in stampede protection. FusionCache adds fail-safe stale fallback and eager refresh.
- Write-through (HybridCache.SetAsync or IDistributedCache.SetStringAsync) — use when zero stale-read risk after a write matters more than write latency.
- Write-around — use when writes far outnumber re-reads. Avoids cache pollution by write-once data.
- Write-back (BackgroundService + dirty-set) — use only when extreme write throughput is the constraint and eventual durability is acceptable.
- Refresh-ahead (FusionCache eager-refresh, or BackgroundService) — use when a small set of hot keys serves most traffic and miss latency is unacceptable.
- HybridCache is the in-box default for read-through with stampede protection; FusionCache adds fail-safe, eager refresh and a backplane; use IDistributedCache directly where you need full control. Mix patterns; don't pick one as the rule.

p. 212

> Decision rules. HybridCache over the Redis IDistributedCache is the in-box stack: read-through with stampede protection via GetOrCreateAsync, write-through via SetAsync. FusionCache is the alternative when you need fail-safe stale fallback, eager refresh or a backplane for multi-Pod L1 invalidation. Drop to IDistributedCache directly when you want full control. Write-around for telemetry. Write-back is the niche extreme-throughput pattern. The bold final line is the take-home: don't pick one pattern as 'the' cache strategy; choose per read path.

## [240] Appendix M · Failure modes (sldId 495)

M

Where it all breaks — and the patterns that hold.

> Appendix M is the synthesis appendix — it brings together error handling, graceful shutdown, observability and the resilience patterns from across the deck, and points them at the specific ways distributed systems fail. If you can only take one slide from this appendix, take the matrix at the end: it maps each failure mode to the patterns that address it. This appendix references section 11 (Observability), section 12 (Security — bulkheads), and Appendix H (Graceful shutdown); it is the place where those threads are tied together. If this runs long in your session, it stands alone and can be presented on its own.

## [241] APPENDIX M · Distributed systems fail differently (sldId 496)

- In a single process, an operation succeeds or it throws. Across a network, a call can succeed, fail, hang forever, succeed-but-the-response-is-lost, or succeed-slowly — and you often cannot tell which.
- Partial failure is the defining trait: some dependencies are up, some down, some degraded, all at the same time. There is no global 'the system is up'.
- Failures are not independent: one slow component can exhaust a caller's resources and take down healthy services around it. Failure spreads.
- Some failures lie: a node passes its own health check while failing real traffic (gray failure). What the system believes about itself and what users experience diverge.
- The goal is not zero failures; that is impossible. The goal is to bound the blast radius and recover automatically. All management is risk management.
  - This appendix: six failure modes, the defensive patterns that address them (with code), Istio's mesh-level role, graceful shutdown, how to observe failures, and a mapping matrix.

p. 213

> Set the frame. The single most important conceptual shift for developers moving from monoliths is partial failure: in a monolith a function call either returns or throws, synchronously, in-process. Across a network there is a whole spectrum of failure, including the worst kind — the call that hangs, or the one that succeeded on the server but whose response was lost, leaving the client unsure whether to retry. Emphasise that failures are correlated (one failure causes others) and that some failures are actively deceptive (gray failures). Land the bold point hard: we are not trying to prevent failure, we are trying to bound it and recover. This reframes everything that follows from 'how do we stop failures' to 'how do we contain and survive them.'

## [242] APPENDIX M · A taxonomy of failure modes (sldId 497)

Network failures, component failures, load failures — and the defensive toolkit that addresses them.

p. 214

> The map for the appendix. Three families. NETWORK failures: partition (nodes alive but unreachable) and split-brain (both sides act as leader). COMPONENT failures: partial (some deps fail) and gray (some degrade and are perceived differently by different observers). LOAD failures: amplification (a failure feeds on itself) and cascading (failure spreads to neighbours). Underneath sits the defensive toolkit — timeouts and deadlines, retry with backoff and jitter, circuit breakers, bulkheads (section 12), load shedding, fallback/degradation, quorum/consensus, Istio mesh policies, graceful shutdown (Appendix H), and observability (section 11). Every pattern addresses specific failure modes; the closing matrix maps which to which. Reconnect to the section-1 maxim: all management is risk management — you manage the distribution of failures, not their existence.

## [243] APPENDIX M · NETWORK · Network partition (sldId 498)

Nodes are alive and healthy; they cannot reach each other. CAP forces a choice: consistency or availability.

p. 215

> See the diagram notes. The key teaching point: a partition is not a crash. Every node is healthy and running; the network between them is the thing that failed. This is what makes partitions so confusing to debug — every individual component looks fine. CAP theorem becomes concrete here: while partitioned, you choose to stay consistent (the minority side refuses writes, sacrificing availability) or available (both sides accept writes, sacrificing consistency, reconciling later). Most data systems let you tune this. Kubernetes itself uses etcd, which chooses consistency (the minority side of a control-plane partition stops accepting writes). Address with quorum/consensus, idempotent writes (so a retried write after heal is safe), and partition-tolerant design.

## [244] APPENDIX M · NETWORK · Split-brain (sldId 499)

A partition where both sides think they are the leader and both accept writes. State diverges; the worst partition outcome.

p. 216

> See the diagram notes. Split-brain is the specific catastrophic outcome of a partition in a system that elects a leader or primary. Both sides lose contact, each assumes the other died, each promotes itself, and now you have two primaries accepting conflicting writes. On heal you have divergent state and no clean way to merge. The prevention is quorum: an action requires a majority (N/2 + 1) of nodes to agree, so a minority partition mathematically cannot act — it knows it is the minority and steps down. This is why cluster sizes are odd (3, 5, 7): to always have a clear majority. Fencing tokens (monotonically increasing IDs that let resources reject a stale leader's writes) and leases are complementary. etcd/Raft give the Kubernetes control plane this property out of the box.

## [245] APPENDIX M · COMPONENT · Partial failure (sldId 500)

The defining trait of distributed systems: some dependencies fail while others keep working. Handle each leg.

p. 217

> See the diagram notes. This is the slide for developers moving from monoliths. In a monolith, the order service and the inventory service are function calls in the same process — if one is 'down' the whole process is down. Distributed, the order service calls inventory (healthy), payment (down), and shipping (slow) and must make a per-dependency decision for each: use the healthy result, fall back or fail for the down one, time out and fall back for the slow one. The mistake that causes most production incidents is treating a remote call like a local one, with no timeout, no fallback and no circuit breaker, so a single down dependency hangs the caller. Address with per-call timeouts, per-dependency circuit breakers, fallbacks, and bulkheads. The next several slides are exactly these patterns, with code.

## [246] APPENDIX M · COMPONENT · Gray failure (sldId 501)

The insidious one: a component is degraded and is perceived differently by different observers. Liveness is green; users suffer.

p. 218

> See the diagram notes. Gray failure is the failure mode that defeats naive health checking. The classic shape: a node is slow or dropping a fraction of requests, but its liveness probe (GET /healthz returning 200 from a trivial handler) still passes, so Kubernetes keeps it in rotation and the load balancer keeps sending it traffic. The system believes it is healthy; users experience errors and latency. This is 'differential observability' — the observer that matters (the client) sees something different from the observer that decides (the probe). The fixes are all about observing from the right vantage point: deep health checks that exercise real dependencies, RED metrics measured on live traffic, SLO burn-rate alerts, and, most important, Istio outlier detection, which ejects a host from the pool when it returns consecutive errors, regardless of what its health check claims. This ties directly to section 11.

## [247] APPENDIX M · LOAD · Amplification loops & retry storms (sldId 502)

A failure triggers retries, which add load, which cause more failures. Backoff, jitter and retry budgets break the loop.

p. 219

> See the diagram notes. Amplification is a positive feedback loop: the system's own defensive behaviour (retrying) becomes the attack. Two compounding effects. First, retry multiplication across layers: if the gateway retries 3x, and it calls a service that retries 3x, which calls a service that retries 3x, one user request becomes 27 requests to the bottom of the stack. Second, synchronisation: every client that failed at the same moment retries at the same moment, creating a thundering herd. The result can be metastable — the system stays collapsed even after the original trigger is gone, because the retry load alone sustains the failure. Breaking it: exponential backoff with jitter (de-synchronise), retry budgets (cap retries to a small percentage of live traffic so they can never multiply unboundedly), retry at exactly one layer, and circuit breakers to stop the doomed calls entirely. This is the failure mode most often caused by well-intentioned resilience code.

## [248] APPENDIX M · LOAD · Cascading failure (sldId 503)

One component's failure overloads its neighbours, which fail in turn — the domino effect up the call graph.

p. 220

> See the diagram notes. Cascading failure is how a single slow dependency takes down an entire system. The mechanism: a slow database causes the calling service's request threads (or async tasks, or connection pool) to fill up waiting; with its resources exhausted, that service now fails or slows for all callers, not just the ones touching the database; its callers' resources then fill up waiting on it; and so on up the graph until the user-facing edge is down. The amplifiers are synchronous call chains and unbounded resources (unbounded queues, unbounded thread pools, no timeouts). Each defensive pattern breaks one link: timeouts stop threads blocking forever; bulkheads isolate the pool so the database calls can't consume all of it; circuit breakers stop calling the slow dependency entirely; load shedding rejects excess work at the edge before it propagates. This is the failure mode bulkheads (section 12) were invented for.

## [249] APPENDIX M · The defensive toolkit — patterns and what they buy (sldId 504)

- Timeout + deadline propagation — never wait forever; pass the remaining budget downstream so nobody does doomed work. Defends: partial, cascading.
- Retry with backoff + jitter — ride out transient failures without building a storm; only for idempotent calls; use a retry budget. Defends: partial, amplification (if done right).
- Circuit breaker — stop calling a failing dependency; fail fast; test for recovery. Defends: cascading, amplification, gray.
- Bulkhead (§12) — isolate resources by tenant/call/priority so one failure can't starve the rest. Defends: partial, cascading.
- Load shedding — when overloaded, reject excess early (503) rather than collapsing. Defends: amplification, cascading.
- Quorum / consensus — majority-required action; the only real answer to split-brain. Defends: partition, split-brain.
- Fallback / graceful degradation — return a useful degraded response (cache, default, queue-for-later) instead of an error. Defends: partial, gray.
- Istio mesh policies + graceful shutdown + observability: the platform layer underneath all of these patterns. Each one gets code, and a matrix maps patterns to modes.

p. 221

> The toolkit overview before the deep dives. Each line names a pattern and the failure modes it defends against — this is the verbal version of the closing matrix. The thing to stress: no pattern is sufficient alone, and several patterns interact (retry without a circuit breaker amplifies; a circuit breaker without a fallback just fails faster; bulkheads without timeouts still let threads block within a pool). Production resilience is the composition of several of these, tuned together. Each gets its own diagram and per-language code so developers can implement them; the bold line flags that the platform-level pieces (Istio, shutdown, observability) sit underneath the application-level patterns.

## [250] APPENDIX M · TIMEOUTS · Timeouts + deadline propagation (sldId 505)

Every remote call needs a timeout; the remaining budget should travel downstream so nobody does doomed work.

p. 222

> See the diagram notes. Two ideas. First, every remote call must have a timeout — the default in many HTTP clients is infinite, which is how a single slow dependency hangs a whole service. Second, deadline propagation: the original deadline (say 1000ms) travels with the request, and each hop subtracts the time it has used and passes the remainder downstream. When the remaining budget is too small to plausibly finish, the downstream fails immediately rather than starting work that will be thrown away. gRPC does this natively with deadlines; for HTTP you pass a deadline header and honour it. The waste this prevents is real: without it, your database spends 500ms on a query for a request the user abandoned 450ms ago, and that wasted work is exactly what tips an overloaded system over. The code example shows the language-specific mechanics.

## [251] APPENDIX M · TIMEOUTS · Timeouts + deadlines (sldId 506)

[chip] csharp · ASP.NET Core 10 + HttpClient

```csharp
public class PaymentService(HttpClient http)   // http.Timeout set at registration
{
    public async Task<Receipt> Charge(Order o, TimeSpan deadline,
                                       CancellationToken ct)
    {
        if (deadline < TimeSpan.FromMilliseconds(50))
            throw new DeadlineExceededException();      // too little budget
        // link the caller's token with a deadline-bounded one
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(deadline);
        var req = new HttpRequestMessage(HttpMethod.Post, "/charge")
            { Content = JsonContent.Create(o) };
        req.Headers.Add("X-Deadline-Ms",                 // propagate budget
            deadline.TotalMilliseconds.ToString("0"));
        var resp = await http.SendAsync(req, cts.Token);  // throws on timeout
        return (await resp.Content.ReadFromJsonAsync<Receipt>(cts.Token))!;
    }
}
```

p. 223

> The .NET idiom is CancellationToken-based. HttpClient.Timeout is set when the typed client is registered (AddHttpClient). Per-call, link the caller's CancellationToken with a deadline-bounded one via CreateLinkedTokenSource + CancelAfter — so the call is cancelled when either the caller gives up or the deadline passes. The remaining budget is propagated in a header. CancellationToken flows all the way down through SendAsync and the JSON read, so cancellation is cooperative and prompt.

## [252] APPENDIX M · RETRY · Retry with exponential backoff + jitter (sldId 507)

Retry transient failures — but spread retries with exponential backoff + jitter, cap them, and only for idempotent calls.

p. 224

> See the diagram notes. Retry is the most abused resilience pattern because the naive version (retry immediately, a fixed number of times, at every layer) is precisely how you build the amplification storm from the amplification-loop discussion. The correct version has four properties: exponential backoff (each retry waits longer: 100ms, 200ms, 400ms), jitter (add randomness so clients don't synchronise), a cap on both attempts and total time, and a retry budget (retries may never exceed, say, 10% of live traffic). And it only applies to idempotent operations — retrying a non-idempotent POST without an idempotency key can double-charge a customer. Always pair retry with a circuit breaker so that once a dependency is clearly down, you stop retrying entirely. The code example shows the idiomatic library for each language.

## [253] APPENDIX M · RETRY · Retry with backoff + jitter (sldId 508)

[chip] csharp · ASP.NET Core 10 + Polly v8

```csharp
// Polly v8: exponential backoff with jitter is built in
private static readonly ResiliencePipeline _pipeline =
    new ResiliencePipelineBuilder()
        .AddRetry(new RetryStrategyOptions {
            ShouldHandle = new PredicateBuilder()
                .Handle<HttpRequestException>(),       // transient only
            MaxRetryAttempts = 3,                       // hard cap
            BackoffType = DelayBackoffType.Exponential,
            UseJitter = true,                           // de-synchronise
            Delay = TimeSpan.FromMilliseconds(100)
        })
        .AddCircuitBreaker(new CircuitBreakerStrategyOptions {  // pair it
            FailureRatio = 0.5, MinimumThroughput = 10,
            BreakDuration = TimeSpan.FromSeconds(5)
        })
        .Build();
public Task<Quote?> Quote(string symbol, CancellationToken ct) =>   // GET
    _pipeline.ExecuteAsync(async t =>
        await http.GetFromJsonAsync<Quote>($"/quote/{symbol}", t), ct).AsTask();
```

p. 225

> Polly v8's ResiliencePipelineBuilder composes strategies in order: the retry strategy with exponential backoff and UseJitter (built in — no manual jitter maths), handling only transient exceptions, capped at 3 attempts; then a circuit breaker wrapping it. Order matters — the breaker is added after retry so it sits outermost and short-circuits retries once tripped. Microsoft.Extensions.Http.Resilience can attach this pipeline to a named HttpClient via AddResilienceHandler. Idempotent calls only.

## [254] APPENDIX M · CIRCUIT BREAKER · Circuit breaker — the state machine (sldId 509)

Closed → Open (fail fast) → Half-Open (test) → Closed. Stops doomed calls; gives the dependency room to recover.

p. 226

> See the diagram notes. The circuit breaker is the pattern that most directly stops cascading and amplification. Three states. CLOSED: calls pass through, failures are counted over a rolling window. When the failure ratio crosses the threshold, the breaker trips to OPEN: calls fail immediately without even attempting the downstream, which both gives a fast answer to the caller and gives the struggling dependency room to recover instead of being hammered. After a reset timeout the breaker goes HALF-OPEN: it allows a few trial calls; if they succeed it closes (recovered), if they fail it re-opens. Crucial details: one breaker per dependency (never a single global breaker), and pair it with a fallback so that an open breaker degrades gracefully rather than just erroring faster. Libraries differ per language; the code example shows each.

## [255] APPENDIX M · CIRCUIT BREAKER · Circuit breaker + fallback (sldId 510)

[chip] csharp · ASP.NET Core 10 + Polly v8

```csharp
public class PaymentService(HttpClient http, IOutbox outbox)
{
    private readonly ResiliencePipeline<Receipt> _pipeline =
        new ResiliencePipelineBuilder<Receipt>()
            .AddCircuitBreaker(new CircuitBreakerStrategyOptions<Receipt> {
                FailureRatio = 0.5,                 // open at 50%
                MinimumThroughput = 10,             // over a window of 10
                BreakDuration = TimeSpan.FromSeconds(5),
                ShouldHandle = new PredicateBuilder<Receipt>()
                    .Handle<HttpRequestException>()
            })
            .AddFallback(new FallbackStrategyOptions<Receipt> {   // degrade
                ShouldHandle = new PredicateBuilder<Receipt>()
                    .Handle<BrokenCircuitException>(),
                FallbackAction = args => {
                    outbox.Enqueue(args.Context.GetOrder());
                    return Outcome.FromResultAsValueTask(Receipt.Pending());
                }
            })
            .Build();
}
```

p. 227

> Polly v8 composes a circuit breaker and a fallback into one typed pipeline. The breaker opens at a 50% failure ratio over a minimum throughput of 10 calls, stays open 5s, and handles HttpRequestException. The fallback strategy catches BrokenCircuitException (thrown while the breaker is open) and degrades: enqueue to the outbox, return a pending receipt. Adding fallback after the breaker means it wraps the breaker and catches its open-state exception. One pipeline per dependency.

## [256] APPENDIX M · BULKHEAD · Bulkhead — isolate so one failure can't sink the rest (sldId 511)

- Covered in depth in section 12 (Security) as a blast-radius pattern; it is equally a resilience pattern, so it appears here in the failure-mode context.
- Isolate resources (connection pools, thread pools, async semaphores, queues) by tenant, by call type, or by priority. A storm in one pool exhausts only that pool.
- Against cascading failure: if database calls have their own bounded pool, a slow database exhausts that pool and returns errors for DB-backed calls — but the service's other endpoints keep serving from their own pools.
- Against partial failure: a single misbehaving tenant or dependency is contained to its own compartment instead of consuming the shared resource.
- Implementation (from §12): Polly v8 AddConcurrencyLimiter strategy on a ResiliencePipeline, paired with AddTimeout. At the mesh: Istio DestinationRule connectionPool gives the same isolation at the network layer.
  - Pair with timeouts: a bulkhead bounds how many calls run concurrently, but without a timeout those calls can still block forever and keep the bulkhead full. The two patterns need each other.

p. 228

> Bulkhead got full treatment in section 12, so here we just re-frame it in the failure-mode context and cross-reference. The key insight to land: a bulkhead bounds concurrency, but concurrency-bounding alone doesn't help if the bounded calls block forever — you must combine bulkhead (limit how many) with timeout (limit how long). Point back to section 12 for the per-language code (we don't repeat it here to save slides), and forward to the Istio slide for mesh-level bulkheading via connectionPool limits.

## [257] APPENDIX M · SHEDDING & FALLBACK · Load shedding and graceful degradation (sldId 512)

- Load shedding — when you are over capacity, reject excess work immediately (HTTP 503 + Retry-After) at the edge, before it consumes resources. A system that sheds 20% of load stays up for the other 80%; a system that accepts everything collapses for 100%.
- Shed by priority: drop health-check-style or low-value traffic first, protect revenue-critical paths. Adaptive concurrency limits (e.g. Netflix's, or Envoy's) shed automatically based on observed latency.
- Graceful degradation — when a dependency is unavailable, return a useful reduced response instead of an error: serve stale cache, omit the personalised section, queue the write for later, show a default recommendation.
- Degradation turns a hard failure into a soft one the user may barely notice. A product page that can't reach the reviews service should still show the product — just without reviews.
- Both are the application-level complement to the circuit breaker: the breaker decides to stop calling; the fallback decides what to return instead; load shedding decides what not to accept in the first place.
  - Reference §11: you cannot shed or degrade intelligently without observability — you shed based on measured saturation, and you alert when degradation rates climb.

p. 229

> Two related patterns that often get skipped. Load shedding is counter-intuitive to engineers, because rejecting requests feels like giving up, but it is the difference between a system that degrades and one that collapses. The maths is simple: if you are at 120% of capacity and accept everything, everything is slow and timing out (0% goodput); if you shed the excess 20%, the 80% you accept is served well. Adaptive limiters do this automatically based on latency. Graceful degradation is the product-level decision about what to return when you can't return everything — it requires the product/design team's input on what's essential vs nice-to-have. The bold line ties shedding, breakers and fallback together as a system: stop accepting (shed), stop calling (break), return something useful (fall back).

## [258] APPENDIX M · ISTIO · Istio — resilience at the mesh layer (sldId 513)

Timeouts, retries, outlier detection (gray-failure ejection) and circuit breaking — uniform, config-driven, no app code.

p. 230

> See the diagram notes. The service mesh gives you a large slice of the resilience toolkit without writing code in every service, in every language. VirtualService configures per-route timeouts and retries (with Envoy adding backoff and jitter automatically, and retryOn conditions controlling which failures are retried). DestinationRule configures connectionPool limits (mesh-level bulkheading) and outlierDetection — which is the mesh's answer to gray failure: it watches each host, and when one returns consecutive errors it ejects that host from the load-balancing pool for a cooldown period, regardless of what the host's own health check claims. That is exactly the gray-failure defence the health-check can't provide. The important discipline: don't double up. If Istio is retrying, don't also retry in the app (that's amplification). Decide where each concern lives — typically: timeouts and outlier detection at the mesh, business-aware retries and fallbacks in the app.

## [259] APPENDIX M · SHUTDOWN · Graceful shutdown (see App. H) (sldId 514)

[chip] csharp · ASP.NET Core 10

```csharp
// OrderService (excerpt, example 21): the default ConsoleLifetime plus one hosted service
builder.Services.AddSingleton<ShutdownState>();
builder.Services.AddHostedService<DrainService>();     // StoppingAsync runs first
builder.Services.Configure<HostOptions>(o => o.ShutdownTimeout = TimeSpan.FromSeconds(20));
builder.Services.AddHealthChecks()
    .AddCheck<ShutdownHealthCheck>("shutdown", tags: ["ready"])     // 503 once draining
    .AddDbContextCheck<OrdersContext>("database", tags: ["ready"]);
// DrainService.StoppingAsync, on the single SIGTERM:
state.MarkShuttingDown();                  // 1. readiness → 503: the Service stops routing
await Task.Delay(delay, cancellationToken);           // 2. endpoints update (5 s)
// 3. Kestrel stops in StopAsync and drains in-flight (ShutdownTimeout 20 s)
app.MapHealthChecks("/healthz", ...);                // liveness stays 200
app.MapHealthChecks("/readyz", ...);                 // ready tag: shutdown + database
app.MapPost("/orders", async (OrderRequest request, OrdersContext db, ShutdownState state) =>
{
    if (state.ShuttingDown)
        return Results.Json(new { error = "shutting down" }, statusCode: 503);
    // ... in-flight requests finish before the host stops; 4. the context is disposed, exit 0
});
```

p. 231

> The application half of graceful shutdown, from the running example's .NET order-service. The default ConsoleLifetime turns the single SIGTERM into a graceful stop, and DrainService, a hosted service, runs first: its StoppingAsync flips a flag so /readyz answers 503 and Kubernetes takes the Pod out of the Service, while /healthz stays 200 so the kubelet does not restart a Pod that is winding down.
>
> New requests get 503. After DRAIN_DELAY_SECONDS StoppingAsync returns and Kestrel stops accepting and finishes in-flight requests within HostOptions.ShutdownTimeout (20 s), the host disposes its services and the process exits 0, inside terminationGracePeriodSeconds. Appendix H covers the hosted-service drain hooks, the preStop hook and the grace period.

## [260] APPENDIX M · OBSERVE · Observing failure modes (see §11) (sldId 515)

- Network partition — watch peer-connectivity and cross-zone error metrics; alert on quorum-loss events from etcd / your datastore.
- Split-brain — alert on more-than-one-leader conditions, divergent-replica metrics, and fencing-token rejections in logs.
- Partial failure — RED metrics per dependency (rate, errors, duration), not just per service. A spike in errors to one downstream is the early signal.
- Gray failure — the hard one: compare health-check status against real-traffic SLOs. Latency percentiles (p99) diverging from the average, and Istio outlier-ejection counts, are your tells.
- Amplification — watch request-rate against user-action-rate (if requests >> actions, retries are multiplying), retry-count metrics, and goodput falling while load rises.
- Cascading — a distributed trace shows the error spreading service-to-service; saturation metrics (thread pools, queue depth, connection pools) climb together across services.
  - The unifying tool is the trace_id from §11: when an alert fires, pivot from the metric to an exemplar trace to its logs to find which leg failed first and how it spread.

p. 232

> Tie the appendix back to section 11. Each failure mode has characteristic signals, and you must instrument for them explicitly: a default dashboard of CPU and memory will not show you a gray failure or an amplification loop. The most important specific guidance: measure RED per dependency (so partial failures are visible), compare health-check status to real-traffic SLOs (so gray failures are visible), and watch request-rate vs user-action-rate (so amplification is visible). The sub-bullet is the workflow: the trace_id is what lets you pivot from 'something is wrong' (a metric) to 'here is the request that shows it' (a trace) to 'here is what failed' (the logs on that trace), the correlation story from section 11 applied to incident response.

## [261] APPENDIX M · Which pattern addresses which failure mode (sldId 516)

Read a row to defend a failure mode; read a column to see what a pattern buys you. Production layers several.

p. 233

> The synthesis slide — if the audience keeps one thing, keep this. Reading across a row tells you the portfolio of patterns that defend a given failure mode (e.g. cascading failure is addressed by timeouts, circuit breakers, bulkheads, load shedding, and graceful shutdown together). Reading down a column tells you what a given pattern buys you across failure modes. Two observations: first, quorum/consensus is the only real answer to split-brain; no amount of retrying or circuit-breaking helps when the problem is two leaders, so you need a majority rule. Second, almost every other cell is about assembling a portfolio — there is no single pattern that handles partial, gray, amplification and cascading failures; you layer timeouts, retries-with-budget, breakers, bulkheads, shedding and fallbacks, and you observe the result. Defence in depth, exactly as in the security section, applied to reliability.

## [262] APPENDIX M · Take-aways and references (sldId 517)

- Design for partial failure from the start: every remote call can succeed, fail, hang, or lie. Timeout everything; the default is often infinite.
- Retry only idempotent calls, with backoff + jitter + a budget, at one layer, always paired with a circuit breaker. Naive retries cause the outages they were meant to prevent.
- Bound the blast radius: bulkheads isolate, circuit breakers stop the bleeding, load shedding protects capacity, fallbacks keep the user served.
- Quorum is the only cure for split-brain. Let etcd / Raft / your datastore handle consensus; don't invent your own.
- Push uniform concerns (timeouts, outlier detection, mesh bulkheads) to Istio; keep business-aware concerns (fallbacks, idempotency) in the app. Don't double-retry.
- Observe from the client's vantage point (RED per dependency, SLOs, outlier ejections) — gray failures are invisible to naive health checks. Drain on shutdown (App. H).
  - References: Google SRE Book (chapters on Addressing Cascading Failures, Handling Overload); 'Release It!' (Nygard — circuit breaker, bulkhead origin); the gRPC retry design, gRFC A6 (retry policy, backoff with jitter, retry throttling); Istio traffic-management docs; the metastable-failures research (Bronson et al., 2021).

p. 234

> Close the appendix and, since it's the last appendix, effectively close the deck's technical content. The take-aways are the imperatives: design for partial failure, timeout everything, retry carefully, bound the blast radius, use quorum for consensus, split concerns between mesh and app, and observe from the client's perspective. The references are the canonical sources: the Google SRE book's cascading-failures and overload chapters are the single best free resource; Michael Nygard's 'Release It!' is where the circuit breaker and bulkhead patterns were named for software; the gRPC retry design (gRFC A6) writes retry policy, backoff with jitter and retry throttling down as a protocol; and the metastable failures paper (Bronson et al.) is the modern formalisation of amplification loops. Encourage the audience to read the SRE cascading-failures chapter as the next step.

## [263] Feature Flags (sldId 518)

N

Progressive delivery, decoupled from deploy — OpenFeature + flagd

> This appendix adds the runtime switch that separates shipping code from releasing a feature. It is a deep-dive you keep open when you are about to roll something out gradually. The whole section is built on two CNCF, open-source projects - OpenFeature for the vendor-neutral SDK and flagd for the backend - so it runs on plain Kubernetes with no managed SaaS, like every other example in the book. The arc: why deploy is not release, the four kinds of flag, how evaluation works, the code to evaluate and target and roll out, flags as a control plane over patterns we already covered, and the lifecycle discipline that keeps flags from becoming debt.

## [264] APPENDIX N · FEATURE FLAGS · Deploy is not release (sldId 519)

p. 235

the artifact ships dark; releasing is a runtime flag flip — and so is rollback

> The reframe that makes everything else work: deploying an artifact and releasing a feature are different events, and a flag is what splits them. The artifact ships to production with the new path turned off - a non-event, visible only in the deploy log. Releasing is then a runtime flag flip: on for one percent, then a wider cohort, then everyone, each step reversible by narrowing the flag rather than rolling back a deployment. This is what lets a team merge to main many times a day yet release on its own cadence, and it is the mechanism behind every canary and every safe cutover in the book. Rollback stops being a redeploy and becomes a config change measured in seconds.

## [265] APPENDIX N · FEATURE FLAGS · Four kinds of flag (sldId 520)

p. 236

by lifetime and owner — each wants different defaults and lifecycle

> Feature flag covers four different tools, and conflating them is the root of most flag messes. They differ along two axes - how long the flag lives, and who decides to flip it. Release flags are temporary and developer-owned: they ship new code dark, ramp it, and are then removed. Experiment or A/B flags are temporary and data-owned: they split traffic across variants so a metric can be measured, and they require sticky assignment. Ops or kill-switch flags are long-lived and SRE-owned: a permanent control to disable a feature or dependency fast under load or incident. Permission or entitlement flags are long-lived and product-owned: they gate functionality by plan, tier, or region. The defaults differ too - a release flag fails off, so half-shipped code stays dark, while a kill-switch usually fails on, so the feature survives a flag-system outage.

## [266] APPENDIX N · FEATURE FLAGS · Evaluating a flag: OpenFeature + flagd (sldId 521)

p. 237

local evaluation, vendor-neutral SDK, fail-safe to the default

> Evaluation should not couple your code to a vendor. OpenFeature is the CNCF vendor-neutral API standard - one SDK surface across languages - and flagd is its lightweight open-source backend that evaluates flags from a file, ConfigMap, or synced source, in-cluster. Together they keep the whole feature-flag story open-source and running on plain Kubernetes, with no managed SaaS, and swapping flagd for another provider later is a configuration change, not a code change. Two properties matter most. First, evaluation returns the default if the provider is unreachable - a flag-system outage must never take the application down. Second, the SDK is vendor-neutral: the app calls getBooleanValue with a flag key, a default, and an evaluation context, and never names the backend. The context carries the targeting inputs - a stable key plus attributes like plan and region - that the rules act on.

## [267] APPENDIX N · FEATURE FLAGS · Evaluating a flag (sldId 522)

p. 238

[chip] csharp · .NET

```csharp
// Program.cs — set the provider once at startup (OpenFeature + flagd provider)
await Api.Instance.SetProviderAsync(new FlagdProvider(new Uri("http://flagd:8013")));

app.MapPost("/checkout", async (Cart cart, [FromHeader(Name = "X-User")] string user) =>
{
    var flags = Api.Instance.GetClient();
    var ctx = EvaluationContext.Builder()
        .SetTargetingKey(user)                     // sticky key
        .Set("plan", cart.Plan).Set("region", cart.Region).Build();
    var useNew = await flags.GetBooleanValueAsync("new-checkout", false, ctx);
    return useNew ? NewCheckout(cart) : LegacyCheckout(cart);
});
```

The same one line of code serves an on/off, a per-plan entitlement, or a 25% rollout.

> The provider is registered once at startup; from then on the application asks the client for a value. The crucial thing to notice is that the application code is the same one line regardless of whether the flag is a simple on/off, a per-plan entitlement, or a 5 percent rollout. All of that lives in the flag's configuration, not the code. The default is what gets returned if flagd is unreachable, so the new path stays dark on a flag-system outage rather than erroring. The targeting key is the user id, which is what makes a percentage rollout sticky. Across every language the shape is identical: register a flagd provider, get a client, build an evaluation context with a targeting key and attributes, and call getBooleanValue with a safe default.

## [268] APPENDIX N · FEATURE FLAGS · Targeting and rollout live in config (sldId 523)

p. 239

[chip] json · flagd

```json
{
  "$schema": "https://flagd.dev/schema/v0/flags.json",
  "flags": {
    "new-checkout": {
      "state": "ENABLED",
      "variants": { "on": true, "off": false },
      "defaultVariant": "off",
      "targeting": {
        "if": [
          { "==": [ {"var": "plan"}, "enterprise" ] }, "on",
          { "fractional": [ {"var": "targetingKey"},
              ["on", 25], ["off", 75] ] }
        ]
      }
    }
  }
}
```

Enterprise plans always on (entitlement); everyone else split 25/75 (sticky rollout) — no code change.

> Because the rules live in flagd, changing who sees a feature never touches the application. A flag definition is a set of variants, a default, and a targeting expression. Two operators do most of the work: a conditional for segmentation - here, the enterprise plan always gets the new checkout, an entitlement - and the fractional operator for percentage rollouts, here splitting everyone else 25/75. The fractional operator buckets on the targeting key, which is what gives sticky assignment: the same user hashes to the same bucket every time. Ramping the rollout is editing the 25 upward; rolling back is editing it down - both take effect in the running fleet within flagd's sync interval, with no redeploy. A kill switch is the same file: set a flag's state to DISABLED and it stops evaluating entirely.

## [269] APPENDIX N · FEATURE FLAGS · Percentage rollout via sticky bucketing (sldId 524)

p. 240

consistent per-user assignment; instant ramp and rollback

> Sticky bucketing matters for two reasons. For a rollout, it prevents flicker - a user who got the new checkout on their first visit keeps getting it, rather than bouncing between variants on refresh. For an experiment, it is a correctness requirement: a user must stay in one arm of the test for the measurement to mean anything. The mechanism is simple - hash a stable key, the user id, into a bucket from 0 to 99, and compare it to the rollout threshold. Because the hash is stable, the same user always lands in the same bucket. Ramping the rollout is moving the threshold up; rolling back is moving it down, and both take effect in the running fleet within the sync interval with no deploy on the path of either.

## [270] APPENDIX N · FEATURE FLAGS · A kill switch (sldId 525)

p. 241

[chip] csharp · .NET

```csharp
// ops kill-switch - default true (fail open): on until an operator kills it
public async Task<Recommendations> Recommend(string user)
{
    if (!await flags.GetBooleanValueAsync("recommendations-enabled", true, Ctx(user)))
        return Recommendations.Empty;        // degrade - still serve the page
    return await _recs.FetchAsync(user);     // pairs with a circuit breaker
}
```

Default true = fail open: only an operator flipping the flag disables it. The default flips with the flag type.

> A kill switch is the operational flag you reach for during an incident: wrap a risky or expensive dependency in a flag so it can be disabled instantly without a deploy. It is the human-driven complement to the circuit breaker from the Failure Modes appendix - the breaker trips automatically on errors; an operator flips the kill switch by hand. The default flips with the flag type: a release flag defaults off so half-shipped code stays dark, while this kill switch defaults true, fail-open, so the feature survives a flag-system outage and only an explicit flip removes it. When it is killed, the page still renders - just without the recommendations - which is graceful degradation, the same idea as the load-shedding discussion in the Failure Modes appendix.

## [271] APPENDIX N · FEATURE FLAGS · Flags over the patterns you already have (sldId 526)

p. 242

a flag is a runtime control surface

> Feature flags are not a new subsystem so much as a runtime control plane over patterns already in this book. A canary is a percentage flag deciding which build a request exercises, often paired with the L7 routing from the routing appendix. A strangler-fig cutover is a flag, or the proxy's percentage, steering a widening slice from the monolith to the extracted service. A saga step can be guarded by a flag to switch a new compensation path on cautiously. And an experiment is a sticky-bucketed variant flag with a metric attached. Recognising flags as the control surface for all of these keeps you from building a bespoke mechanism for each - the same decoupling, expressed four ways.

## [272] APPENDIX N · FEATURE FLAGS · The flag lifecycle (sldId 527)

p. 243

a release flag is born with a removal ticket

> The failure mode of feature flags is not technical, it is organisational: flags that are never removed. Every flag is a branch in your code and a dimension in your test matrix, and a stale one is dead code, a hidden conditional, and a live risk surface that nobody remembers the meaning of. The discipline that keeps it healthy: give every release flag an owner and an expiry from the moment it is created, and treat removing it as part of finishing the feature, not optional cleanup. Long-lived ops and entitlement flags are exempt - they are permanent by design - which is exactly why distinguishing the four types matters. A short-lived flag that has been at 100 percent for two weeks should be deleted along with the branch it guarded.

## [273] APPENDIX N · FEATURE FLAGS · Testing, observing, and anti-patterns (sldId 528)

p. 244

  - Test both sides of every flag you depend on - a suite that only hits the default path misses the bug behind the flag.
  - Put the resolved variant on your telemetry - a span attribute and a metric label - so a latency or error change attributes to a specific flag and cohort.
- Anti-patterns: flags as a config store; release flags that never die; stacks of flags whose combinations no one reasons about; experiments without sticky assignment; business logic buried in flag rules.

> A flag multiplies the states your system can be in, so test both sides of every flag you depend on; a test suite that only exercises the default path will not catch a bug behind the flag. Keep the number of simultaneously interacting flags small, and default flags off in test environments unless a test sets them explicitly. Observability ties flags back to the Observability section: record the resolved variant as a span attribute and a metric label, so a latency or error change can be attributed to a specific flag and cohort. The recurring anti-patterns: using flags as a general configuration store - they are for release control, not for tuning timeouts; letting release flags become permanent; stacking many flags whose combinations no one reasons about; running experiments without sticky assignment, which makes the data meaningless; and putting real business logic inside flag rules instead of in code.

## [274] APPENDIX N · FEATURE FLAGS · Take-aways (sldId 529)

p. 245

- Decouple deploy from release: ship dark, release gradually, roll back by narrowing a flag.
- Distinguish the four flag types - they want different owners, defaults, and lifecycles.
- Evaluate through a vendor-neutral SDK (OpenFeature) against an OSS backend (flagd), always with a safe default.
- Keep targeting and rollout in configuration, not code, and make percentage rollouts sticky.
- Treat release flags as debt with a removal ticket; put the resolved variant on your telemetry.

References: OpenFeature spec & flagd docs (CNCF) · Hodgson, “Feature Toggles” · Accelerate / DORA · Unleash (OSS alternative).

> Close on the imperatives. Decouple deploy from release: ship dark, release gradually, roll back by narrowing a flag. Distinguish the four flag types, because they want different owners, defaults, and lifecycles. Evaluate through a vendor-neutral SDK against an open-source backend, always with a safe default so a flag outage cannot take the app down. Keep targeting and rollout rules in configuration, not code, and make percentage rollouts sticky. Treat release flags as debt with a removal ticket attached, and put the resolved variant on your telemetry so you can attribute a regression to a cohort. The canonical references are the OpenFeature specification and the flagd documentation, Pete Hodgson's Feature Toggles article for the taxonomy of flag types, and the Accelerate and DORA research for the deploy-versus-release distinction; Unleash is a capable open-source alternative backend behind the same OpenFeature SDK.

## [275] API Testing with Newman (sldId 530)

O

Postman collections as an automated gate on Docker Engine

> This appendix turns the Postman collections the team already pokes at by hand into an automated test gate, using Newman, Postman's command-line runner. It is a deep-dive you keep open when you are wiring API tests into CI. The key idea that makes it cheap: Newman tests the API as a black box over HTTP, so one collection is the conformance suite for every implementation in the book, and the only language-specific step is bringing the service under test up. The arc: why Newman, the anatomy of a collection, one collection against six backends, running it and shaping the output, data-driven cases, the CI gate on Docker Engine, and where Newman sits in the test pyramid.

## [276] APPENDIX O · API TESTING · Why Newman (sldId 531)

p. 246

the headless runner turns a Postman collection into CI-readable results

> A Postman collection is an executable contract, not just a saved list of requests. Newman runs it without the GUI and emits machine-readable results: a cli reporter for a human watching, a junit reporter that CI turns into a test report, and an html reporter to share. There is no new test framework to learn - the tests are the JavaScript assertions already supported inside Postman, and Newman is the bridge from works-when-I-click-it to verified-on-every-pull-request. The same file serves three audiences: a developer in Postman, a reviewer reading the tests, and a pipeline failing the build when an assertion breaks.

## [277] APPENDIX O · API TESTING · Anatomy of a collection (sldId 532)

p. 247

folders of requests, each with assertions; the environment supplies the variables

> A collection nests folders and requests; each request can carry a pre-request script, the HTTP call itself, and a block of tests that run against the response. The tests are small JavaScript blocks using Postman's pm API - asserting the status, the response time, the shape of the body. Environment variables supply the parts that change between runs, like the base URL and an auth token, resolved at run time. Storing a value from one response - a new order id - in a variable lets a later request chain off it, which is how a collection models a whole flow rather than isolated calls.

## [278] APPENDIX O · API TESTING · Tests live in the request (sldId 533)

p. 248

[chip] json · Postman

{% raw %}
```json
{
  "name": "Create order",
  "request": {
    "method": "POST",
    "header": [{ "key": "Idempotency-Key", "value": "{{$guid}}" }],
    "url": "{{base_url}}/orders",
    "body": { "mode": "raw", "raw": "{\"sku\":\"A-1\",\"qty\":2}" }
  },
  "event": [{
    "listen": "test",
    "script": { "exec": [
      "pm.test('201 Created', () => pm.response.to.have.status(201));",
      "pm.test('under 300ms', () => pm.expect(pm.response.responseTime).to.be.below(300));",
      "const body = pm.response.json();",
      "pm.test('returns an id', () => pm.expect(body).to.have.property('id'));",
      "pm.collectionVariables.set('order_id', body.id);"
    ] }
  }]
}
```
{% endraw %}

Assertions run after the response; the saved order_id chains into later requests.

> Here is a request that creates an order and asserts on the result. The test block asserts a 201 Created, parses the body, asserts it carries an id, and stores that id in a collection variable so a later request - fetch, cancel, or pay for the order - can use it. Beyond status codes, a test can validate the response shape against a JSON Schema, which is how you turn the metadata and error-format work from earlier appendices into an enforced contract: assert that an error body matches the Problem Details schema rather than checking exact strings, so the test stays stable as data changes but still catches a removed field or a wrong type.

## [279] APPENDIX O · API TESTING · One collection, six backends (sldId 534)

p. 249

Newman tests over HTTP, so one collection validates every implementation

> Because Newman exercises the API as a black box over HTTP, the collection does not know or care which language implements the service. The same collection is the conformance suite for every implementation in this book - point it at whichever service is running and the assertions are identical. The collection is the API specification made executable. Bringing the service under test up is the only language-specific step; the Newman command that follows is the same everywhere.

## [280] APPENDIX O · API TESTING · Launch the service under test (sldId 535)

p. 250

[chip] bash · .NET

```bash
# .NET — run the service, then the same collection
dotnet run &                       # http://localhost:8080
newman run orders.postman_collection.json -e local.postman_environment.json
```

Only this step is language-specific; the Newman command is identical for all six.

> The only per-language step is starting the service. Each implementation exposes the same HTTP API on the same port, so the base URL in the environment file is identical and the Newman command that follows does not change. That is the point of black-box testing: bring up Spring Boot, Quarkus, .NET, Python, C++ or Go, and run the same collection against it. In CI the services start with docker compose up -d --build --wait instead of a foreground command; locally, a background process and a newman run is the fastest loop.

## [281] APPENDIX O · API TESTING · Running Newman & shaping output (sldId 536)

p. 251

[chip] bash

{% raw %}
```bash
# install once (Node.js):
#   npm install -g --prefix ~/.local newman@6.2.3 newman-reporter-htmlextra@1.23.1
newman run orders.postman_collection.json \
  --environment local.postman_environment.json \
  --reporters cli,junit,htmlextra \
  --reporter-junit-export results/newman.xml \
  --timeout-request 5000 \
  --bail
# --timeout-request: per-request ceiling (ms); --bail: stop at the first failure

# data-driven: one iteration per CSV row; the columns become {{variables}}
newman run orders.postman_collection.json -e local.postman_environment.json \
  --iteration-data cases.csv
```
{% endraw %}

Reporters target the audience; --bail gates fast; --iteration-data drives edge cases.

> The runner takes the collection and an environment file, and you choose reporters for the audience: cli for a human, junit for the XML CI turns into a report, htmlextra for a shareable page. --bail stops at the first failed assertion, which is what you usually want in a gate; drop it to see every failure in one run. A single set of requests can be run repeatedly over a table of inputs with --iteration-data, which is how you cover boundary values, bad input, and edge cases without duplicating requests - and the expected status can travel in the data too, so one request becomes a table of positive and negative cases.

## [282] APPENDIX O · API TESTING · Data-driven tests (sldId 537)

p. 252

one request set, many inputs — boundary values and negative cases from a table

> Data-driven testing runs the same requests once per row of a CSV. The columns become variables in the requests, and a column can carry the expected status so a single assertion checks status against the row's expectation. This is how a handful of requests becomes broad coverage: the happy path, a zero-quantity order that must be rejected with a 422, an over-stock order that must also be rejected - all without copy-pasting requests. Keeping the cases in data rather than in duplicated requests is what makes the suite maintainable as the API grows.

## [283] APPENDIX O · API TESTING · Newman in CI (sldId 538)

p. 253

[chip] yaml · GitHub Actions

```yaml
# .github/workflows/api-tests.yml (any runner with Docker Engine and Node.js)
jobs:
  api-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - run: docker compose up -d --build --wait   # order, payment, inventory, ...
      - run: ./scripts/wait-for-ready.sh           # poll /readyz before testing
      - run: npm i -g newman@6.2.3 newman-reporter-htmlextra@1.23.1
      - run: |
          newman run orders.postman_collection.json \
            -e ci.postman_environment.json \
            --reporters cli,junit \
            --reporter-junit-export results/newman.xml
      - uses: actions/upload-artifact@v7          # keep the report even on failure
        if: always()
        with: { name: newman-results, path: results/ }
```

Bring the stack up with docker compose, wait for readiness, run the collection: a failed assertion fails the build.

> Newman exits non-zero when any assertion fails, which is all a pipeline needs to gate a merge. The services come up on Docker Engine as they do locally, with no managed cloud, and Newman runs against them. The readiness poll matters: start testing only once the services report ready, using the readiness endpoint from the Observability and Graceful Shutdown material, or the first requests race the boot and fail spuriously. Upload the junit report as an artifact even on failure so the failing assertion is visible in the run.

## [284] APPENDIX O · API TESTING · The gate on Docker Engine (sldId 539)

p. 254

the same stack you run locally, gating every pull request

> The full gate: a pull request builds the image, docker compose brings the order, payment, and inventory services up, Newman runs the collection against them, and the result gates the merge: pass merges, fail blocks. The important property is parity: the stack in CI is the stack you run locally, on the same Docker Engine, so a green run in CI means the contract holds against the running services rather than a mock.

## [285] APPENDIX O · API TESTING · Where Newman fits (sldId 540)

p. 255

the API/contract tier: on top of unit tests, under a thin end-to-end layer

> Newman does not replace unit tests; it is the layer on top of them. It owns the API/contract tier: real HTTP against a running service, fast enough to run on every pull request. Keep the base of fast unit tests broad, use Newman for the contract and integration behaviour that only shows up over real HTTP, and reserve a thin layer of full end-to-end tests for the few user flows that need the whole system. Pushing everything into Newman makes a slow, brittle suite; ignoring it leaves the contract untested. Test the failure paths as carefully as the happy path: a 401 with WWW-Authenticate, a 403, a 409 or 422 on a business rule, a 429 with RateLimit headers, and idempotency by sending the same key twice. Those cases tie this appendix back to the error-format, security, idempotency, and rate-limiting material.

## [286] APPENDIX O · API TESTING · Take-aways (sldId 541)

p. 256

- Treat the Postman collection as the executable specification - Newman runs it headlessly to guard every change.
- One collection is the conformance suite for all six implementations: Newman tests over HTTP, as a black box.
- Validate response shape against a schema, not just status codes; drive edge cases from data, not duplicated requests.
- Assert the failure paths - 401, 403, 409/422, 429, idempotency - as carefully as the happy path.
- Gate CI on plain Docker Engine so the build fails on a broken contract; keep Newman in the API/contract tier.

References: Postman docs & Newman CLI docs (reporters, --iteration-data, --bail) · Postman Learning Center (pm API, JSON-schema validation).

> Close on the imperatives. Treat the Postman collection as the executable specification of your API, and let Newman run it headlessly so the same assertions guard every change. Because Newman tests over HTTP, one collection is the conformance suite for all six implementations. Validate response shape against a schema, not just status codes; drive edge cases from data rather than duplicated requests; and assert the failure paths as carefully as the happy path. Wire it into CI on plain Docker Engine so the build fails on a broken contract, and keep Newman in its lane: the API/contract tier, on top of unit tests and under a thin end-to-end layer. The references are the Postman documentation and the Newman command-line documentation, and the Postman Learning Center guides on writing tests with the pm API and on JSON-schema validation.

## [287] Appendix P · .NET on Linux (sldId 542)

P

Runtime, Kestrel, and Containers — what changes when Windows goes away.

> Appendix P is for the audience moving from .NET Framework on Windows: what the runtime does on Linux, what replaces IIS, and what ships in the container. Four parts: the platform and the language, compilation and the runtime, Kestrel, and the container image.
>
> It is reference material; pull it up when someone asks what changes when Windows goes away.

## [288] APPENDIX P · RUNTIME · C# is a language. .NET is a platform. (sldId 543)

C# is a statically-typed, garbage-collected language — one of several that target .NET. F# and VB.NET are the others. All three compile to the same intermediate representation.

.NET (since .NET 5) is the platform: CoreCLR runtime, Base Class Library (System.*, Microsoft.Extensions.*), the Roslyn compiler, NuGet, and the dotnet CLI. The platform is cross-platform.

When this book says “.NET 10,” it means the platform. When it says “C#,” it means the language. A .csproj targets a .NET version (net10.0), not a C# version, because the platform version determines what APIs are available.

The distinction matters because conflating them causes architectural confusion — the runtime is language-agnostic.

p. 257

> C# is the language, .NET is the platform. C#, F# and VB.NET all compile to the same intermediate language; the platform is the CoreCLR runtime, the Base Class Library, the Roslyn compiler, NuGet and the dotnet CLI, cross-platform since .NET 5.
>
> A .csproj targets a platform version, net10.0, not a language version, because the platform version decides which APIs exist. The examples target .NET 10.0.12 with SDK 10.0.112, and the C# version follows from the SDK. Keeping the two words apart avoids design confusion: the runtime is language-agnostic.

## [289] APPENDIX P · COMPILATION · CIL: what dotnet build produces (sldId 544)

Roslyn compiles C# to CIL bytecode — RyuJIT compiles CIL to native code method-at-a-time at runtime.

p. 258

> The compilation pipeline. Roslyn compiles C# to CIL bytecode in an assembly; dotnet build and dotnet publish produce .dll files, not native executables. At run time RyuJIT compiles each method to native x86-64 or ARM64 code on its first call, and tiered compilation recompiles hot methods with more optimization.
>
> The practical consequence: start-up pays a JIT cost, and steady-state code runs as native code. NativeAOT trades that start-up cost for restrictions on dynamic code; the CoreCLR slide covers it.

## [290] APPENDIX P · RUNTIME · CoreCLR on Linux: libcoreclr.so (sldId 545)

JIT compilation (RyuJIT) — CIL to native x86-64 or ARM64, one method at a time, first call only.

Garbage collection — generational, concurrent GC. Server GC mode (default in ASP.NET Core) allocates one heap per CPU core.

Type system — reflection, generics, interface dispatch.

Threading — maps .NET threads to pthreads; Task and async/await run on the thread pool.

P/Invoke — call native C libraries directly (libpq, librdkafka, openssl).

NativeAOT alternative: ahead-of-time compilation to a single native binary. Faster startup, less memory, but no Reflection.Emit — JIT is the default for full library compatibility.

After JIT, a .NET method is indistinguishable from one compiled by GCC. The runtime stays for GC and exceptions, but the hot path is native code.

p. 259

> On Linux the runtime is libcoreclr.so, a native shared library. It owns JIT compilation, garbage collection (generational and concurrent; ASP.NET Core defaults to Server GC with one heap per core), the type system, threading (managed threads map to pthreads, and async work runs on the thread pool) and P/Invoke into native libraries such as libpq, librdkafka (which Confluent.Kafka wraps) and OpenSSL.
>
> NativeAOT compiles ahead of time to one native binary: faster start-up and less memory, but no runtime code generation, so some reflection-heavy libraries do not work. JIT stays the default for full library compatibility. After the JIT, a hot .NET method is native code like any other; the runtime remains for GC and exceptions.

## [291] APPENDIX P · KESTREL · Kestrel: the web server that replaced IIS (sldId 546)

Built into ASP.NET Core — no IIS, no nginx needed. Listens on TCP, handles TLS via OpenSSL, parses HTTP, runs the middleware pipeline.

p. 260

> Kestrel is the web server built into ASP.NET Core. It listens on a TCP socket, handles TLS through OpenSSL on Linux, parses HTTP/1.1, HTTP/2 and HTTP/3, and hands each request to the middleware pipeline. There is no IIS and no w3wp.exe worker process.
>
> Walk the figure from the socket to your endpoint: connection, protocol parsing, middleware (routing, authentication, health checks, OpenTelemetry), then the handler. Every example in the deck runs on Kestrel inside the container.

## [292] APPENDIX P · KESTREL · Why not nginx or Apache in front? (sldId 547)

In Kubernetes, the service mesh handles TLS termination, load balancing, and retries. Kestrel handles everything else.

Adding nginx as a sidecar adds latency, memory, and operational complexity for features Kestrel already provides.

Every example in this book: builder.WebHost.UseUrls("http://+:8080")

For gRPC (HTTP/2 only): builder.WebHost.ConfigureKestrel(k => k.ListenAnyIP(50051, o => o.Protocols = HttpProtocols.Http2))

Port 8080 because ports below 1024 require root, which containers should not run as.

Kestrel supports HTTP/1.1, HTTP/2, HTTP/3 natively — gRPC, WebSockets, and REST share the same host.

p. 261

> Teams moving from IIS often put nginx or Apache in front of Kestrel out of habit. On Kubernetes the service mesh or the ingress already terminates TLS, balances load and retries, so a reverse proxy sidecar adds latency, memory and another component to operate for features Kestrel and the platform already provide.
>
> The examples bind with builder.WebHost.UseUrls("http://+:8080"), and gRPC services listen on an HTTP/2-only endpoint configured through ConfigureKestrel. Port 8080 because ports under 1024 need root, and the containers run as a non-root user. REST, gRPC and WebSockets share one Kestrel host.

## [293] APPENDIX P · CONTAINERS · Multi-stage container build (sldId 548)

SDK compiles (∼780 MB image), only the runtime + app DLLs ship (∼200 MB image). The SDK never reaches production.

p. 262

> The multi-stage Containerfile. The build stage uses the SDK image, ubi9/dotnet-100 (about 780 MB), to restore and publish; the runtime stage uses ubi9/dotnet-100-aspnet (about 170 MB) and copies only the published output, owned by UID 1001 with group-0 permissions. The final image is about 200 MB, and the SDK, the NuGet cache and the source never reach production.
>
> Restore and publish run in one RUN step with a BuildKit cache mount for NuGet packages, so rebuilds are fast and a stale layer cannot point at packages that are gone. What to show: docker image inspect on an example image and the number of layers.

## [294] APPENDIX P · CONTAINERS · Red Hat UBI: what ships to production (sldId 549)

UBI9 base (∼70 MB) — glibc, openssl, ca-certificates, tzdata, libicu.

ASP.NET Core runtime (∼100 MB) — libcoreclr.so, libclrjit.so, BCL assemblies, ASP.NET shared framework.

Your application (∼5–80 MB) — compiled .dll files, NuGet package DLLs, appsettings.json.

Not in the image: SDK, MSBuild, Roslyn, NuGet, source code, obj/ and bin/ intermediates, test projects.

UBI images are freely redistributable, based on RHEL 9, and run on any Kubernetes cluster. Red Hat publishes no UBI 10 .NET image, so .NET stays on UBI 9 while the other languages use UBI 10. They contain the same .NET runtime bits as Microsoft’s images — the difference is the base OS layer.

ubi9/dotnet-100:9.8-1791421718 (SDK, build only) → ubi9/dotnet-100-aspnet:9.8-1791363520 (runtime, ships), both from registry.access.redhat.com.

p. 263

> What ships in the runtime image, layer by layer: the UBI 9 base (glibc, OpenSSL, CA certificates, tzdata, libicu), the ASP.NET Core runtime (libcoreclr.so, the JIT, the BCL and the ASP.NET shared framework), and your application's assemblies and configuration. The SDK, MSBuild, Roslyn, sources and test projects are not in it.
>
> The examples pin ubi9/dotnet-100:9.8-1791421718 for the build and ubi9/dotnet-100-aspnet:9.8-1791363520 for the runtime. They stay on UBI 9 because Red Hat publishes no UBI 10 .NET image; every other language in the deck builds on UBI 10. UBI images are freely redistributable, run on any Kubernetes cluster, and carry the same .NET runtime as Microsoft's images; the difference is the base OS layer.

## [295] APPENDIX P · LIFECYCLE · Container runtime lifecycle (sldId 550)

1. CoreCLR initializes — loads libcoreclr.so, starts the GC, initializes the thread pool.
2. Host builder runs — registers services (DI), configures logging, sets up OpenTelemetry.
3. Kestrel binds to port 8080 — begins accepting HTTP connections.
4. Application is ready — Kubernetes starts sending liveness and readiness probes.
5. On shutdown, SIGTERM arrives — .NET host catches it and begins graceful shutdown: stops accepting new requests, drains in-flight, flushes telemetry, disposes services.

The entire lifecycle is the same as any Linux process. No IIS app pool recycle, no w3wp.exe, no application domain.

The container is the process boundary — SIGTERM is your shutdown signal, HostOptions.ShutdownTimeout is your budget.

p. 264

> The life of a .NET container, in order: CoreCLR loads and starts the GC and the thread pool; the host builder registers services, logging and OpenTelemetry; Kestrel binds port 8080; Kubernetes starts its probes. On SIGTERM the host stops accepting requests, drains in-flight work, flushes telemetry and disposes services, within HostOptions.ShutdownTimeout.
>
> It is an ordinary Linux process: no application-pool recycling, no w3wp.exe, no application domains. The container is the process boundary, SIGTERM is the shutdown signal, and the grace period is the budget, which Appendix H covers in detail.

## [296] APPENDIX P · TAKE-AWAYS · Take-aways (sldId 551)

C# compiles to CIL bytecode, not native code. The CoreCLR JIT (RyuJIT) compiles to native at runtime, method-at-a-time. After that first call, performance is identical to C or C++.

Kestrel is the built-in web server — it handles TLS (via OpenSSL), HTTP/1.1+2+3, gRPC, and WebSockets natively. No reverse proxy layer is needed inside the Pod.

Multi-stage Containerfiles separate the SDK (∼780 MB) from the runtime (∼170 MB). Only the published DLLs and the ASP.NET runtime ship to production.

Red Hat UBI 9 images (no UBI 10 .NET image exists) are the same .NET runtime on a RHEL 9 base — freely redistributable, and run on any Kubernetes cluster.

References: .NET runtime architecture (docs.microsoft.com) · Kestrel web server (ASP.NET Core docs) · Red Hat UBI .NET images (access.redhat.com)

p. 265

> The four points to keep. C# compiles to CIL and the JIT produces native code method by method, so steady-state performance is native. Kestrel is the web server, with TLS through OpenSSL and HTTP/1.1, HTTP/2, HTTP/3, gRPC and WebSockets, and needs no reverse proxy inside the Pod.
>
> Multi-stage builds keep the SDK out of the shipped image. The Red Hat UBI 9 images carry the same .NET runtime on a RHEL 9 base, freely redistributable and run on any Kubernetes cluster; .NET stays on UBI 9 because no UBI 10 .NET image exists yet.

## [297] Appendix Q · Blazor Server + SignalR (sldId 552)

Q

Real-time .NET — server-rendered UI, push updates, and the Redis backplane.

> Appendix Q covers real-time .NET: Blazor Server for server-rendered UI, SignalR for push, and the Redis backplane that lets several Pods serve one audience. It builds on the WebSocket scaling problem from Appendix C and is backed by Example 30, an order dashboard that updates live when an order is placed.

## [298] APPENDIX Q · BLAZOR SERVER · What Blazor Server is (sldId 553)

Blazor Server is a hosting model where all C# component logic runs on the server. The browser runs a thin JavaScript runtime that sends UI events (clicks, keystrokes) over a persistent WebSocket and applies DOM diffs returned by the server.

The WebSocket is a SignalR “circuit” — one per browser tab. The server keeps a component tree in memory for each circuit, re-renders on state change, and sends only the diff (a binary serialized RenderBatch).

No WASM, no client-side .NET. The trade-off: latency per interaction (each event round-trips), but zero download size and full access to server-side resources (databases, internal APIs, secrets).

Blazor Server requires a persistent WebSocket per tab — the scaling challenge from Appendix C applies directly.

p. 266

> Blazor Server runs all component logic on the server. The browser loads a thin JavaScript runtime that sends UI events over a persistent connection and applies the DOM diffs the server sends back.
>
> Each browser tab is one SignalR circuit, and the server keeps that tab's component tree in memory, re-renders on state change and sends only the diff. There is no WebAssembly download and full access to server-side resources; the cost is a round trip per interaction and memory per connected tab. Because every tab holds a persistent connection, the Pod-pinning problem from Appendix C applies directly.

## [299] APPENDIX Q · SIGNALR · SignalR: the transport underneath (sldId 554)

SignalR is ASP.NET Core’s real-time communication library. It abstracts WebSockets (preferred), Server-Sent Events, and long-polling behind a single Hub API.

A Hub is a server-side class with methods that clients can call (client → server), and the server can invoke methods on connected clients (server → client). Groups let you broadcast to subsets of connections.

Blazor Server uses SignalR internally for its circuit, but you can also use SignalR directly in any ASP.NET Core app for push notifications, live feeds, or collaborative editing — independent of Blazor.

The Hub pattern: clients call server methods by name, server invokes client methods by name. No manual frame parsing, no custom protocol — SignalR handles serialization (JSON or MessagePack), reconnection, and connection lifecycle.

SignalR is not Blazor-specific — it is a general-purpose real-time library that Blazor Server happens to use as its transport.

p. 267

> SignalR is ASP.NET Core's real-time library. It negotiates WebSockets first, with Server-Sent Events and long polling as fallbacks, behind one Hub API. Clients call server methods by name, the server invokes client methods by name, and groups broadcast to subsets of connections. Serialization (JSON or MessagePack), reconnection and the connection lifecycle are handled for you.
>
> Blazor Server uses SignalR for its circuit, but SignalR stands on its own: push notifications, live feeds and collaborative editing in any ASP.NET Core app. Example 30 uses it both ways.

## [300] APPENDIX Q · SCALING · Scaling with the Redis backplane (sldId 555)

The same per-pod pinning problem from Appendix C appears here: a SignalR connection is pinned to the pod that accepted it. If pod A calls Clients.Group("dashboard").SendAsync(), only clients connected to pod A receive the message.

SignalR’s built-in Redis backplane solves this. One line of configuration, AddSignalR().AddStackExchangeRedis(redisConn), and every hub invocation is published to Redis Pub/Sub. All pods subscribe, so all connected clients receive the update.

builder.Services.AddSignalR().AddStackExchangeRedis(redisConn) — that is the entire backplane setup.

p. 268

> The Pod-pinning problem again: a SignalR connection stays on the Pod that accepted it, so a broadcast from Pod A reaches only Pod A's clients. The Redis backplane fixes it: AddSignalR().AddStackExchangeRedis(...) publishes every hub invocation to Redis pub/sub, every Pod subscribes, and each delivers to its own connections.
>
> Example 30 runs two dashboard instances, on ports 8080 and 8081, against one Redis, and verify.sh checks that an order pushed through one instance reaches a client connected to the other, including after one instance restarts. Redis 8 is used under its AGPLv3 open-source option.

## [301] APPENDIX Q · CODE · The order dashboard: how the pieces connect (sldId 556)

OrderHub.cs — a SignalR Hub with a JoinDashboard method. Clients call it to join the “dashboard” group. The hub itself has no push logic — it is just a group-management entry point.

POST /orders — the REST endpoint creates an order in Postgres, then calls hub.Clients.Group("dashboard").SendAsync("OrderPlaced", order). This pushes the order to every connected dashboard client.

Dashboard.razor — a Blazor Server component. On initialization, it connects a HubConnection to /hubs/orders, calls JoinDashboard, and registers a handler for “OrderPlaced” that prepends the order to the list and calls StateHasChanged().

The result: POST an order via curl, and the Blazor dashboard updates in real time with no polling. The SignalR circuit carries both the Blazor DOM diffs and the explicit OrderPlaced messages.

The example runs on docker compose: two Blazor app instances (ports 8080 and 8081) on one Redis backplane, plus Postgres and the LGTM stack.

p. 269

> How Example 30 fits together. OrderHub has one method, JoinDashboard, which adds the caller to the dashboard group; the hub holds no push logic. POST /orders stores the order in Postgres and calls Clients.Group("dashboard").SendAsync("OrderPlaced", order) through IHubContext. Dashboard.razor connects a HubConnection to /hubs/orders, joins the group, and on OrderPlaced prepends the order and re-renders.
>
> What to show: open the dashboard on port 8080 and on port 8081, place an order with curl, and watch both update with no polling. Fallback: run verify.sh, which checks the health endpoints, the orders API, the SignalR negotiate endpoint and cross-instance delivery.

## [302] APPENDIX Q · COMPARISON · When to use what (sldId 557)

Raw WebSockets (Appendix C): full control, cross-language, works anywhere. Use when you need a custom binary protocol (protobuf frames), or when clients are not .NET.

SignalR: managed reconnection, groups, Hub RPC pattern, MessagePack serialization. Use when the server is ASP.NET Core and you want push without managing WebSocket lifecycle.

Blazor Server: server-rendered UI with no client-side framework. Use for internal tools, dashboards, admin panels — where the user count is low and server-side access matters more than offline support.

Blazor WebAssembly: client-side .NET in the browser. Use when you need offline support or want to reduce server load. Not covered here — the scaling model is different (no persistent circuit).

Choose the lowest abstraction that meets your requirements — raw WS for cross-language, SignalR for .NET push, Blazor Server for .NET UI.

p. 270

> Choose the lowest abstraction that meets the requirement. Raw WebSockets, as in Appendix C: full control, any client language, custom binary framing such as protobuf. SignalR: managed reconnection, groups, hub RPC and MessagePack when the server is ASP.NET Core and you want push without owning the WebSocket lifecycle.
>
> Blazor Server: server-rendered UI with no client framework, for internal tools, dashboards and admin consoles where user counts are modest and server-side access matters more than offline use. Blazor WebAssembly runs .NET in the browser, holds no persistent circuit and scales like static content; it is not covered here.

## [303] APPENDIX Q · TAKE-AWAYS · Take-aways (sldId 558)

Blazor Server runs all UI logic on the server — the browser is a thin terminal connected by a SignalR circuit. No WASM download, full server access, but every interaction round-trips.

SignalR abstracts WebSockets behind a Hub API with groups, automatic reconnection, and serialization. It is a general-purpose real-time library, not Blazor-specific.

The Redis backplane (AddStackExchangeRedis) lets multiple pods broadcast to all connected clients — the same per-pod pinning solution from Appendix C, built into SignalR.

For internal dashboards with low user counts and high data freshness, Blazor Server + SignalR is a pragmatic choice. For public-facing, high-scale, or cross-language scenarios, use raw WebSockets.

References: ASP.NET Core Blazor hosting models (docs.microsoft.com) · SignalR documentation · Appendix C: WebSocket scaling

p. 271

> The take-aways. Blazor Server runs the UI on the server and the browser is a thin terminal on a SignalR circuit: no download, full server access, a round trip per interaction. SignalR is a general real-time library, not only Blazor's transport.
>
> The Redis backplane lets several Pods broadcast to every connected client, the same answer to Pod pinning as in Appendix C, built into SignalR. For internal dashboards with modest user counts, Blazor Server with SignalR is a pragmatic choice; for public, high-scale or cross-language clients, use raw WebSockets.

## [304] Example 05 on minikube (sldId 559)

R

The same services and the same verify.sh on a single-node Kubernetes cluster

> Appendix R takes Example 05, the event-driven fan-out, from docker compose to a single-node Kubernetes cluster on minikube, in all six languages, and records what changed. Compose proves the code; a cluster adds questions compose never asks: where configuration and credentials live, how a service finds a broker that an operator manages, what restarts a process that exits, and how a request from the host reaches a pod.
>
> The arc: the runtime, the topology, the compose-to-Kubernetes mapping, one overlay per language, how images get into the node, how to run it, and the recorded results.

## [305] APPENDIX R · MINIKUBE · From compose to a cluster (sldId 560)

p. 272

- Compose proves the code; a cluster adds configuration, credentials, discovery, restarts and ingress.
- Scope: Example 05 (event-driven fan-out), three services, all six languages, one node.
- One Kafka broker, one Postgres instance, no service mesh: a local topology, not production.
- The contract carries over: Service names, the Secret, environment variables, the health endpoint.
- The same verify.sh runs against compose and the cluster: ten checks per language.

Site: Appendix R · Code: examples/05-event-driven/k8s/

> What the appendix covers and what it leaves out. The scope is one example on one node: one Kafka broker, one Postgres instance, no service mesh. High availability, network policy and autoscaling are outside it.
>
> What it fixes is the contract between an application and its platform: the Service names, the Secret that holds the database credential, the environment variables each language reads, and the health endpoint. That contract is what carries over to any conformant Kubernetes cluster, and it is why the application code is unchanged.
>
> The test is the one compose uses: verify.sh, ten checks, with its container operations switched to kubectl exec.

## [306] APPENDIX R · MINIKUBE · The minikube runtime (sldId 561)

p. 273

- Profile cndp-k8s: Docker driver on Docker Engine, containerd, Kubernetes v1.36.5.
- 8 GB memory, 4 CPUs, 40 GB disk for Kafka, Postgres, LGTM and three services.
- NodePorts 30080 (order-service) and 30300 (Grafana), published on 127.0.0.1 at creation.
- No kubectl port-forward, minikube tunnel or minikube service: forwarded connections drop.
- Every command passes --context cndp-k8s; setup-profile.sh restores the prior context.

minikube v1.39.0 · kubectl v1.36.5 · Helm v4.3.0 · Strimzi 1.2.0

> minikube runs the control plane and the workload in one container on Docker Engine, the same engine compose uses, with containerd as the container runtime inside the node. Kubernetes v1.36.5 matches the pinned kubectl, so client and server are the same version.
>
> Host access uses two NodePorts published on the loopback address when the profile is created. Port-forwarding, minikube tunnel and minikube service are not used: forwarded connections drop under load and on idle, and a drop looks like a broken service. setup-profile.sh checks with docker port that both ports bind to 127.0.0.1.
>
> The kubectl context never changes: every command names --context cndp-k8s, minikube start runs with --keep-context, and setup-profile.sh restores the prior context because minikube's restart path can override that flag.

## [307] APPENDIX R · MINIKUBE · One node, two namespaces (sldId 562)

p. 274

The node container holds two namespaces; the host reaches two loopback NodePorts and uses kubectl exec

> The topology. The node container cndp-k8s holds two namespaces: strimzi runs the Strimzi operator, and cndp-05 runs order-service, the shipping and notification consumers, a single-node KRaft Kafka cluster, Postgres 18, the LGTM stack and the Postgres Secret.
>
> From the host, curl and verify.sh reach order-service on 127.0.0.1:30080, a browser reaches Grafana on 127.0.0.1:30300, and kubectl exec runs the Kafka and Postgres checks inside their pods. Other minikube profiles stay stopped while this one runs.

## [308] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldId 563)

p. 275

- kafka → Strimzi Kafka + KafkaNodePool, bootstrap cndp-kafka-bootstrap:9092 (Kafka 4.3.1).
- postgres → StatefulSet cndp-postgres, schema ConfigMap, Service cndp-postgres-rw.
- Credential → Secret cndp-postgres-app, read through secretKeyRef.
- build: → docker build, then minikube image load; imagePullPolicy: Never.
- healthcheck → startup and readiness probes on the order-service /healthz.
- ports: 8080:8080 → NodePort 30080.

The schema file and the OTLP endpoint http://lgtm:4318 are the same ones compose uses.

> Each compose element has a Kubernetes counterpart, and each counterpart changes something. Kafka becomes a Kafka resource that the Strimzi operator turns into a broker; the plain listener on port 9092 is in-cluster only. Postgres becomes a StatefulSet that mounts the same schema file compose mounts.
>
> The demo credential moves out of every service's environment into one Secret. Only order-service has an HTTP surface, so it alone has startup and readiness probes, with a 150-second startup window for the JVM and .NET images. The consumers have no HTTP surface: the cluster restarts them if they exit, and they start from the earliest offset, so a restart loses nothing.

## [309] APPENDIX R · MINIKUBE · One overlay per language (sldId 564)

p. 276

[chip] yaml · kustomize

```yaml
# k8s/overlays/dotnet/kustomization.yaml (excerpt)
images:
  - name: order-service
    newName: localhost/cndp-05/dotnet-order-service
    newTag: v1
  # shipping-consumer and notification-consumer map the same way
# appended to each Deployment's environment by a JSON patch
- name: DATABASE_URL
  value: "Host=cndp-postgres-rw;Port=5432;Database=appdb;\
    Username=$(PG_USER);Password=$(PG_PASSWORD)"
- name: KAFKA_BOOTSTRAP
  value: "cndp-kafka-bootstrap:9092"
# order-service only
- name: SERVICE_VERSION
  value: "1.0.0"
```

base/ is language-neutral; each overlay maps the images and appends the variables its language reads.

> The .NET overlay. The base Deployments are language-neutral: they run with a restricted security context (non-root, no privilege escalation, all capabilities dropped, RuntimeDefault seccomp, no fixed user ID), read PG_USER and PG_PASSWORD from the Secret, and point OTEL_EXPORTER_OTLP_ENDPOINT at the LGTM Service.
>
> Each overlay maps the three image names to localhost/cndp-05/<language>-<service>:v1 and appends the variables that language already reads in compose, so the application code is untouched. Kubernetes expands $(PG_PASSWORD) only if PG_PASSWORD is defined earlier in the list, which is why the credential variables sit in the base.

## [310] APPENDIX R · MINIKUBE · Images built on the host (sldId 565)

p. 277

docker build on the host, minikube image load into the node; pods never pull

> The cluster does not build images. Each service is built on the host with docker build, which keeps the host's BuildKit caches (a cold C++ build takes about half an hour), then copied into the node's containerd store with minikube image load.
>
> The Deployments set imagePullPolicy: Never, so a missing image fails fast with ErrImageNeverPull instead of trying a registry that does not have it. Tags are always v1; nothing uses latest.

## [311] APPENDIX R · MINIKUBE · Run it (sldId 566)

p. 278

[chip] bash · minikube

```bash
# from examples/05-event-driven/, with no other profile or container running
k8s/setup-profile.sh        # create cndp-k8s; check the published ports
k8s/build-images.sh dotnet  # docker build, then minikube image load
k8s/deploy.sh dotnet        # Strimzi, Kafka, Postgres, LGTM, then the overlay
RUNTIME=kubernetes BASE=http://127.0.0.1:30080 ./verify.sh

# all six languages, a fresh namespace for each
OUT=/tmp/cndp-k8s-matrix k8s/verify-matrix.sh

# clean up: the namespace, the Strimzi release and its CRDs; then stop the profile
k8s/teardown.sh --operator
minikube stop -p cndp-k8s
```

With RUNTIME=kubernetes, verify.sh runs its container checks through kubectl exec; the ten checks are unchanged.

> The run, from the example directory. setup-profile.sh creates the profile and refuses to start while another profile or a container is running. build-images.sh builds and loads the three .NET images, and deploy.sh installs Strimzi, then Kafka, Postgres and LGTM, then the overlay.
>
> verify.sh is the file compose uses. Its container operations go through helper functions, and RUNTIME=kubernetes swaps them: the Kafka checks run in pod cndp-dual-role-0 and the Postgres checks in cndp-postgres-0.
>
> What to show: the ten check marks and the Results line, then Grafana on 127.0.0.1:30300. Fallback: the recorded results. teardown.sh never deletes the profile; minikube stop frees the memory and keeps the images.

## [312] APPENDIX R · MINIKUBE · Recorded results (sldId 567)

p. 279

- 10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0).
- Spring Boot 361 s · Quarkus 135 s · .NET 134 s · Python 116 s · C++ 103 s · Go 104 s.
- Tempo received traces from order-service, shipping-consumer and notification-consumer in every language.
- shipping-consumer scaled to 0: no shipment; back to 1: the group resumes from its committed offset.
- Stop the profile before starting compose or another cluster; the scripts refuse to run alongside them.

Times cover the image build and load, the deploy, the checks and the namespace teardown.

> The recorded run, 2026-10-11: every language passed all ten checks with a fresh namespace per language. After each run, verify-matrix.sh asked Tempo through the lgtm pod which services had sent traces, and all three services reported in every language.
>
> The scale-down check was run by hand: with the shipping consumer at zero replicas a new order produces no shipment; scaled back to one, the consumer group resumes from its last committed offset and the shipment appears. That is the event-driven contract from the Event-Driven section, observed on a cluster.
