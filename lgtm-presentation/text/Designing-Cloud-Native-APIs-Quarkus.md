# Designing-Cloud-Native-APIs-Quarkus

Source: Designing-Cloud-Native-APIs-Quarkus.pptx · 282 slides

## [001] CLOUD-NATIVE ARCHITECTURE · Designing Cloud-Native APIs (sldId 256)

From principles to a running system on Kubernetes — communication, composition, data, events, and the platform that governs them.

Robert Sedor

Chief Architect, Application Development

> Welcome and framing. This is a working architect's tour of designing cloud-native APIs on Quarkus 3.40.1 (LTS, Java 25) — not a survey of buzzwords. Set expectations: we build one realistic system (five services and a gateway) and re-examine it from twelve angles, then the appendices go deep on protocols, versioning, WebSockets, sagas, errors, caching, failure modes and API testing, and run Example 05 on minikube. Tell the audience the whole deck is a reference they can keep. Mention the running stack up front: Java with Quarkus (Quarkus REST, gRPC, SmallRye GraphQL, Reactive Messaging, Kafka Streams, WebSockets Next, Quarkus Flow), on Kubernetes with Kafka, Istio and KEDA. The platform around the code (Strimzi, Apicurio, OpenMetadata, the LGTM stack) is the same for every language; Quarkus is how we write the services.

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
- Appendices K–L · Monolith → Microservices, Caching Patterns
- Appendices M–O · Failure modes, Feature Flags, API Testing
- Appendix R · Example 05 on minikube
- Glossary of acronyms

p. 1

> The agenda: a short setup, thirteen sections, and the deep-dive appendices. The setup motivates why patterns matter in the age of AI. Sections 1 to 6 build the system from principles up through data and streaming; sections 7 to 13 cover the operational platform around it (workflows, management, registry, metadata, observability), then security, and close on anti-patterns.
>
> The appendices are reference material for the questions that come up: protocols, versioning, WebSockets, sagas, errors, DDD, coupling, shutdown, L7 routing, monolith-to-microservices decomposition, caching, failure modes, feature flags and API testing. Appendix R runs Example 05 on minikube with the same verify.sh as compose. A glossary of acronyms closes the deck.
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

> Transition into section one. The core message: cloud-native is not a stack you buy, it is a set of runtime properties your service must exhibit. Tools (Kubernetes, Istio, KEDA) exist to make those properties cheap to obtain — but if your service isn't written to lean on them, no platform can rescue it.

## [008] CLOUD-NATIVE PRINCIPLES · Cloud-native is a set of runtime properties (sldId 263)

If your API isn't disposable, observable, resilient, elastic, automatable and loosely coupled, the platform can't help it.

p. 6

> Six pillars. Spend a sentence on each: disposable (12-factor, fast start, clean stop, no local state), observable (traces/metrics/logs, health probes), resilient (timeouts, retries, circuit breakers, graceful degradation), elastic (scale to load and to zero), automatable (declarative config, GitOps, self-healing), loosely coupled (contracts not calls, async where it fits). The pillars are the rubric for the whole talk: every design decision in it either earns or spends one of these properties.

## [009] CLOUD-NATIVE PRINCIPLES · The platform makes the properties the default (sldId 264)

- Kubernetes gives you the disposable process model: liveness/readiness probes, rolling deploys, self-healing.
- KEDA (and the http-add-on) make elasticity real — scale on lag or RPS, all the way to zero.
- Istio supplies resilience and security at the wire: timeouts, retries, circuit breaking, mTLS.
- OpenTelemetry + Tempo / Mimir / Prometheus / Grafana / Kiali make every request observable.
- Your job is to write services that lean on these — not to reimplement them per service.

p. 7

> The punchline is the bold line: your job is to lean on the platform, not reimplement it. Concretely — don't write your own retry library when Istio does it at the wire; don't build a bespoke autoscaler when KEDA scales on lag and RPS; don't hand-roll metrics plumbing when OpenTelemetry plus the LGTM stack gives it to you. Every line of resilience code you write per service is a line you maintain forever and that drifts between teams. The platform makes the good behaviour the default.

## [010] CLOUD-NATIVE PRINCIPLES · Design-first: the contract precedes the code (sldId 265)

- Agree the interface before implementing it — OpenAPI for REST, .proto for gRPC, AsyncAPI for events.
- The contract is a versioned artifact in the registry, gated in CI, owned by the producing domain.
- Consumers code against the contract and generated stubs, never against your database or internals.
- This is what makes services independently deployable — the promise the contract encodes is the boundary.
  - Tooling: Maven with the quarkus-bom for reproducible builds; Quarkus REST emits OpenAPI (SmallRye); buf / protoc for gRPC; SmallRye GraphQL exports SDL.

p. 8

> Design-first is the cultural prerequisite for everything that follows. The contract (OpenAPI, .proto, AsyncAPI) is agreed and registered before code is written, owned by the producing domain, and gated in CI. Consumers code against the contract and generated stubs, never against your database. Make the point that this is what delivers independent deployability: the promise the contract encodes is the service boundary. If you skip this, you get distributed coupling that's worse than a monolith because it fails over the network. In the Quarkus world the contract artifacts come naturally: SmallRye OpenAPI emits the REST spec, protoc/buf compile the .proto, and SmallRye GraphQL exports the SDL — all checked into the registry.

## [011] CLOUD-NATIVE PRINCIPLES · The twelve-factor app, revisited (sldId 266)

- The twelve-factor app (2011) is the original recipe for software that's disposable, scalable and portable — the discipline beneath the runtime properties we just saw.
- It predates Kubernetes but maps onto it almost one-to-one: most factors are now things the platform provides, not code you write.
- So read the factors by ownership — a few you still author (config from the environment, statelessness, clean start/stop, logs as streams) and the rest the platform hands you (scaling, build/release/run, attached backing services).
- In a microservices, event-driven system they get richer: “backing services” means Postgres, Kafka and the schema registry as swappable URLs; “logs” becomes correlated traces, metrics and logs.
- Treat it as a pre-flight check: “will this survive the platform?” The twelve factors are listed and mapped to where each lives in our architecture.

p. 9

> Frame the twelve-factor app for the audience: it's the 2011 Heroku methodology that first codified what we now call cloud-native, and it's worth revisiting because it predates Kubernetes yet maps onto it almost perfectly. The key reframing here is ownership: don't recite the list; split it into the few factors you still write (config from the environment, stateless processes, fast clean startup and shutdown, logs as event streams) versus the many the platform now provides by default (build/release/run via images and GitOps, concurrency via KEDA, attached backing services). In a microservices/event-driven world several factors deepen: backing services now includes Kafka and the registry, and 'logs' has become full observability. End by teeing up the list and the mapping diagrams.

## [012] CLOUD-NATIVE PRINCIPLES · What the twelve factors are (sldId 267)

The original 2011 checklist — most are now platform concerns; only a few are yours to write.

p. 10

> A lot of people nod along to ‘twelve-factor’ without being able to name the twelve, so here they are at a glance, one line each. Don't read them aloud — let people scan. Two takeaways to say: first, this 2011 list predicted cloud-native a decade early; second, many factors are now handled by the platform (build/release/run, concurrency, disposability, port binding, backing services) versus the few you still actively write (config from the environment, statelessness, logs as streams). That sets up the map of each factor onto our architecture.

## [013] CLOUD-NATIVE PRINCIPLES · Twelve factors, mapped to our system (sldId 268)

Most factors are now platform defaults you adopt; a few are discipline you still write.

p. 11

> This is the payoff: not the traditional twelve-factor table, but a map of where each factor lives in the system we're building. Read it left to right: the twelve factors cluster into five things they ask of you, and each maps to a concrete piece of our stack and the section that covers it. Build & ship (codebase, dependencies, build/release/run, parity) becomes one repo, one image per release, the same image everywhere (§1). Configure becomes environment config (§1). Run on the platform (stateless processes, concurrency, disposability, port binding) becomes stateless pods, KEDA scaling, fast start/stop, and services behind Istio (§1, 2, 6). Attach resources becomes Postgres, Kafka and Apicurio as swappable URLs (§4–5). Operate (logs, admin processes) becomes OpenTelemetry into the LGTM stack and admin work as Jobs/CronJobs (§7, 11). The caption is the message: most of these are now defaults you adopt, not code you write — which is exactly what 'cloud-native' buys you.

## [014] CLOUD-NATIVE PRINCIPLES · A 12-factor Quarkus service, ready for the platform (sldId 269)

[chip] java · Quarkus + SmallRye Health

```java
# application.properties (excerpt), examples/01-cloud-native-principles/quarkus
# SmallRye Health: readiness includes the datasource check (503 when the database is down)
quarkus.smallrye-health.liveness-path=/healthz
quarkus.smallrye-health.readiness-path=/readyz
# db/init owns the schema: Hibernate only validates
quarkus.hibernate-orm.schema-management.strategy=validate
// Order.java: active record over the existing table
@Entity @Table(name = "orders")
public class Order extends PanacheEntityBase {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) public Integer id;
    @Column(nullable = false) public String customer;
    @Column(nullable = false, precision = 10, scale = 2) public BigDecimal total;
}
// OrderResource.java (excerpt)
@ConfigProperty(name = "service.version") String serviceVersion;      // env, factor III
@POST @Path("orders") @Transactional
public OrderDto createOrder(@RestQuery String customer, @RestQuery BigDecimal total) {
    var order = new Order(); order.customer = customer;
    order.total = total.setScale(2, RoundingMode.HALF_UP);
    order.persist();                         // INSERT in the request transaction
    return OrderDto.of(order);               // the DTO, never the entity
}
```

Probes, env-config and an explicit version are the price of admission for a Kubernetes Deployment.

p. 12

> Walk the code: config comes from the environment via MicroProfile Config (factor III): QUARKUS_DATASOURCE_JDBC_URL, the username and password and SERVICE_VERSION override application.properties, never a baked-in file. The two probes come from SmallRye Health (quarkus-smallrye-health), mapped to /healthz and /readyz in application.properties. /healthz is liveness (am I alive? if not, restart me) and never checks a dependency. /readyz is readiness (can I serve?) and includes the datasource check, so when the database is unreachable it answers 503 with status DOWN, which takes the pod out of rotation without killing it. The probe reads the status code, not the body: Kubernetes treats any answer from 200 to 399 as ready. Custom checks are @Liveness and @Readiness beans; Example 21 adds one for the drain.
>
> Persistence is Hibernate ORM with Panache. The Order entity maps the table that db/init creates, and quarkus.hibernate-orm.schema-management.strategy=validate makes Hibernate check the mapping instead of owning the schema. The resource returns a DTO record, never the entity. Getting liveness vs readiness wrong is a top cause of cascading restarts, so stress the distinction. Maven with the quarkus-bom (platform 3.40.1) pins every dependency reproducibly.

## [015] Communications (sldId 270)

02

Match the interaction style to the call.

> Section two. The thesis: there is no single right protocol — there is a right protocol per interaction. Resist the urge to standardize on one wire for everything. The section gives a decision rule and then shows each protocol in code against the running system.

## [016] COMMUNICATIONS · Pick the protocol for the interaction (sldId 271)

REST for reach, gRPC for internal speed, GraphQL for client-driven reads, async for decoupled facts.

p. 13

> Four interaction styles, four defaults. REST for the public/edge surface where reach and caching matter; gRPC for internal service-to-service where latency and streaming matter; GraphQL for client-driven reads that compose many sources in one round trip; async events for decoupled facts that fan out. Most real systems use all four — the skill is matching each call to the right one. Note the sync/async chips at the bottom. This slide is the map for the whole section.

## [017] COMMUNICATIONS · REST at the edge with Quarkus REST (sldId 272)

[chip] java · Quarkus REST

```java
@Path("/orders")
@Produces(MediaType.APPLICATION_JSON)
public class OrderResource {                  // Quarkus REST
    record OrderIn(@NotBlank String sku, @Positive int quantity) {}  // validated
    @POST
    @Transactional
    public RestResponse<Order> place(@Valid OrderIn body) {
        Order o = orders.create(body);
        events.publish("order.placed", o);    // emit the fact (the outbox makes it safe)
        return RestResponse.status(Response.Status.CREATED, o);   // 201, not 200
    }
    @GET                                       // cursor pagination, not offset
    public Page<Order> list(@RestQuery String after,
                            @RestQuery @DefaultValue("50") int limit) {
        return orders.page(after, limit);
    }
}
```

Resource-shaped URLs, Bean-Validation contracts, correct status codes, cursor pagination — the edge surface other teams depend on.

p. 14

> This is the edge surface. Point out four things teams routinely get wrong: (1) resource-shaped URLs (nouns, not verbs); (2) request contracts validated declaratively: here a Java record with Bean Validation annotations (@NotBlank, @Positive, @Valid), the Quarkus equivalent of Pydantic models, so bad input never reaches your logic; (3) correct status codes — 201 on create, not 200; (4) cursor pagination, not offset, because offset breaks under concurrent writes and gets slow at depth. The method is blocking and Quarkus REST runs it on a worker thread; return Mutiny's Uni, Quarkus's reactive type, when the endpoint should be non-blocking. SmallRye OpenAPI generates the spec from the resource, and that spec is what we register and gate. Test this surface with curl and Postman.

## [018] COMMUNICATIONS · gRPC for internal service-to-service calls (sldId 273)

[chip] protobuf + java · Quarkus gRPC

```protobuf+java
// inventory.proto — the contract, registered in Apicurio
syntax = "proto3";
service Inventory {
  rpc ReserveStock (ReserveRequest) returns (ReserveReply);
}
message ReserveRequest { string sku = 1; int32 quantity = 2; }
message ReserveReply   { bool reserved = 1; int32 remaining = 2; }
// Quarkus gRPC generates the Mutiny service interface from the .proto at build time
@GrpcService
public class InventoryService implements Inventory {   // generated interface
    @Override
    public Uni<ReserveReply> reserveStock(ReserveRequest req) {
        return stock.reserve(req.getSku(), req.getQuantity())
            .map(r -> ReserveReply.newBuilder()
                .setReserved(r.ok()).setRemaining(r.remaining()).build());
    }
}
```

Schema-first, binary, multiplexed over HTTP/2 — the right default for chatty internal paths. Test with ghz.

p. 15

> gRPC for the internal paths. The .proto is the contract, and it lives in the registry like OpenAPI. Quarkus gRPC compiles the .proto with protoc at build time and you implement the generated Mutiny interface, annotated @GrpcService so Quarkus wires it up — no manual server bootstrap. Highlight that the field numbers (=1, =2) are the wire contract — we return to exactly why in Appendix B. It's binary and multiplexed over HTTP/2, so it's fast and supports streaming, and the reactive Uni keeps it non-blocking. The right default for chatty service-to-service calls where you control both ends. Load-test it with ghz.

## [019] COMMUNICATIONS · Synchronous coupling vs. asynchronous facts (sldId 274)

A synchronous call shares fate; an event shares a fact. Reach for async wherever immediacy isn't required.

p. 16

> The central trade-off of the whole talk in one picture. Top row: a synchronous call couples caller to callee in time and availability — if payment-service is down, the order request fails too, and availability multiplies downward across a chain. Bottom row: emitting order.placed as a fact lets the order succeed immediately; consumers catch up from the log if they were down. The rule: reach for async wherever immediacy isn't strictly required. This sets up the entire event-driven section later.

## [020] COMMUNICATIONS · The mesh handles the wire, not your code (sldId 275)

Istio sidecars give you mTLS, retries, timeouts and telemetry — uniformly, without per-service code.

p. 17

> Service mesh in one picture. Your app speaks plain HTTP or gRPC to localhost; the Istio sidecar (Envoy) intercepts and adds mTLS, retries, timeouts and telemetry on the wire — uniformly, for every service, with zero application code. istiod is the control plane distributing policy and identity (SPIFFE). The key insight ties back to principles: resilience and security become platform defaults, not per-service reimplementations. The configuration itself is an Istio VirtualService.

## [021] COMMUNICATIONS · Resilience as configuration, not per-call code (sldId 276)

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

p. 18

> Resilience as configuration. This VirtualService gives inventory a 2-second timeout, two retry attempts with an 800ms per-try timeout, retrying only on connect-failure and unavailable. The critical word is bounded — attempts: 2, not infinite. Tell the war story: unbounded client-side retries are how a brief blip becomes a full outage, because every caller piles on the struggling service (a retry storm). Putting this in the mesh means it's consistent across every service and tunable without redeploying code.

## [022] Composition (sldId 277)

03

Aggregate at the edge, not inside services.

> Section three. The question: when a client needs data from several services, where does the joining happen? The answer that keeps services decoupled: at the edge, in a gateway or BFF — never by services calling each other in deep chains. That chaining is how you accidentally rebuild a monolith over the network.

## [023] COMPOSITION · One query, many services (sldId 278)

The gateway presents one schema and fans out to REST and gRPC back-ends, then joins and shapes the result.

p. 19

> GraphQL federation against the running system. The gateway presents one schema to clients and fans out to REST and gRPC back-ends, then joins and shapes the result. The client makes one round trip and asks for exactly the fields it needs. The services stay unaware of each other; the gateway owns the composition. Contrast this with services calling services, which we'll warn against on the patterns slide. The resolver code shows how the gateway composes the calls.

## [024] COMPOSITION · A composing resolver in SmallRye GraphQL (sldId 279)

[chip] java · SmallRye GraphQL

```java
@GraphQLApi                                  // the gateway's schema (SmallRye GraphQL)
public class OrderApi {
    @Query                                   // REST call to order-service
    public Order order(String id) {
        return orderClient.get(id);
    }
    // @Source adds a 'stock' field to Order, fetched only when queried
    public Integer stock(@Source Order order) {           // via gRPC
        return inventory.reserveStockView(order.sku()).getRemaining();
    }
}
// SmallRye GraphQL exports the SDL to the registry automatically.
```

The gateway owns aggregation; each field resolves against the owning service. @Source attaches a field fetched from elsewhere.

p. 20

> The resolver makes federation concrete. The top-level order query calls order-service over REST; the stock method, annotated with @Source Order, adds a stock field to the Order type that resolves on demand by calling inventory-service over gRPC. Each field resolves against its owning service — the gateway is just the composition layer. Mention the N+1 risk: naive per-field resolution can explode into many back-end calls, so production gateways batch (SmallRye GraphQL supports a BatchSource for exactly this). SmallRye GraphQL is the JVM-standard, MicroProfile GraphQL implementation Quarkus ships; it exports the SDL to the registry automatically.

## [025] COMPOSITION · Three ways to compose — and where each belongs (sldId 280)

Push aggregation to a gateway or BFF. Chaining calls inside services rebuilds the monolith over the network.

p. 21

> Three composition patterns: an API gateway (one composed schema for everyone), a backend-for-frontend (a tailored aggregate per client type — web vs mobile), and GraphQL federation (a distributed graph). All three push aggregation outward to the edge. The anti-pattern to call out explicitly: service-to-service call chains, where order calls inventory calls pricing calls... — synchronous, deeply coupled, and impossible to reason about. That rebuilds the monolith with network latency between the pieces.

## [026] Data (sldId 281)

04

Own your data; share it through contracts.

> Section four, and the hardest discipline to hold. The rule: each service owns its data and shares it only through APIs and events — never through a shared database or by reaching into another service's tables. This is what makes independent deployment and independent scaling real. The slides cover ownership, the dual-write trap, and the saga.

## [027] DATA · A database per service (sldId 282)

Each service owns its schema and storage engine; no other service touches its tables directly.

p. 22

> Database-per-service. Each service owns its schema and even its storage engine — order and payment on Postgres, something else on a document store if that fits. No other service touches those tables directly; the only doors in are the API and the events. The hard part is social, not technical: someone will always want to 'just join across two services' databases' for a report. That shortcut is the single most common way microservice independence dies. Reporting needs go through the metadata/lineage layer or a dedicated read model, not direct table access.

## [028] DATA · CQRS — Command Query Responsibility Segregation (sldId 283)

Separate the write model from the read model. They have different shapes, scales and even different stores.

p. 23

> CQRS (Command Query Responsibility Segregation) is the pattern of using different models for writes and reads. The write side optimises for invariants and consistency: a normalised schema in a transactional store (Postgres, MySQL). The read side optimises for query shape: denormalised wide tables, an Elasticsearch index, a Mongo document, or whatever fits the question being asked. The two are linked by a stream of events: either domain events emitted by the write side, or the database commit log itself via CDC, the log-tailing pattern. The cost: eventual consistency, a small lag between the write committing and the read model catching up. The benefit: each side can scale, schema-evolve and even be stored independently. Use this pattern when reads and writes have different shapes and access patterns. Avoid it when a single store handles both; CQRS adds operational complexity that isn't free. The classic motivating case: a service that takes thousands of writes per second but is read by analytics, dashboards and search — the write model serves the writes, the read model serves the rest. CQRS pairs naturally with event sourcing on the write side and event streaming for projections; the Event-Driven section draws both distinctions.

## [029] DATA · CQRS in practice (sldId 284)

[chip] java · Quarkus REST + Panache + SmallRye Reactive Messaging

```java
@Path("/orders")                        // write side: command handler
public class OrderWriteResource {
    @Inject WriteOrderRepository writes;
    @Inject @Channel("order-placed") Emitter<OrderEvent> events;
    @POST @Transactional                                    // blocking: worker thread
    public Order create(OrderIn body) {
        Order order = new Order(body);
        writes.persist(order);                              // write model
        events.send(new OrderCreatedEvent(order));          // → projection
        return order;
    }
}
@Path("/orders")                        // read side: query handler, denormalised store
public class OrderReadResource {
    @Inject ReadOrderSummaryRepository reads;               // hits read DB
    @GET @Path("/{id}/summary")
    public OrderSummary summary(@RestPath String id) {
        return reads.findByIdOptional(id)                   // never the write store
            .orElseThrow(() -> new WebApplicationException(404));
    }
}
@ApplicationScoped                      // projection: events upsert the read model
public class OrderSummaryProjection {
    @Inject ReadOrderSummaryRepository reads;
    @Incoming("order-placed") @Transactional               // topic order.placed
    public void on(OrderCreatedEvent ev) { reads.upsert(OrderSummary.from(ev)); }
}
```

p. 24

> The Quarkus shape. Two separate JAX-RS resources: OrderWriteResource handles commands, OrderReadResource handles queries. They could even be in different services/processes. The write side uses an Emitter<OrderEvent> bound to an outgoing Reactive Messaging channel — the SmallRye runtime publishes to Kafka. The projection is a separate @ApplicationScoped bean with an @Incoming("order-placed") method (topic order.placed) that consumes the stream and updates the read store via a separate ReadOrderSummaryRepository (different Panache datasource). The read model can be a wide denormalised table, an Elasticsearch index, or a Mongo document — chosen by query shape. Different scaling for the read side and write side; different team ownership possible.

## [030] DATA · Log tailing — the database commit log is the event stream (sldId 285)

Debezium tails the WAL and publishes every committed row as a Kafka event. No dual-write.

p. 25

> The mechanism that makes CQRS projections and the outbox pattern work: Change Data Capture, or CDC. The application writes ordinary SQL. The database commits and the change lands in the write-ahead log (WAL on Postgres, redo log on Oracle, binlog on MySQL, transaction log on SQL Server). Debezium, an Apache 2.0 open-source project running as a set of Kafka Connect connectors, tails that log via the database's native replication protocol (logical replication slots on Postgres, etc.), translates row-level deltas into Kafka events, and publishes them with commit ordering preserved. The application doesn't know Debezium exists. There is no dual-write — the commit is the single source of truth, and the event is a strictly downstream consequence. This is why log tailing matters before the outbox: the outbox is a targeted use of CDC for a specific case (publishing events that aren't naturally row-level), and CQRS projections are the other big use. Debezium supports Postgres, MySQL, MariaDB, SQL Server, Oracle, MongoDB, Db2, Cassandra, and Vitess out of the box. Run mode: deploy as Kafka Connect workers, or use Debezium Server (standalone) if you don't want a Kafka Connect cluster. WAL = Write-Ahead Log: the database's commit-ordered durable log that already exists for replication and crash recovery; Debezium just subscribes to it.

## [031] DATA · Dual-write is unsafe — use the outbox (sldId 286)

Write state and the outbox row in one transaction; CDC relays the committed fact to Kafka.

p. 26

> This is the slide that prevents a class of production bugs. The dual-write problem: if you write to your database and then publish to Kafka as two separate operations, a crash between them leaves you inconsistent — the order exists but the event was never sent, or vice versa. The fix is the transactional outbox: write the state change and an outbox row in one local transaction, then a change-data-capture tool (Debezium) tails the database log and relays the committed row to Kafka. The database commit is the single source of truth. The outbox write itself is one database transaction, shown in code.

## [032] DATA · The outbox write — one transaction, no lost events (sldId 287)

[chip] java · Hibernate Panache + Debezium

```java
// OutboxEvent.java + OrderResource.java (excerpt), examples/04-data/quarkus
@Entity @Table(name = "outbox")
public class OutboxEvent extends PanacheEntityBase {       // the table Debezium tails
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) public Long id;
    @Column(name = "aggregate_id") public String aggregateId;
    @Column(name = "event_type") public String eventType;
    @JdbcTypeCode(SqlTypes.JSON) public OrderPlacedPayload payload;   // jsonb column
}
@POST @Transactional                          // one JTA transaction around both rows
public Response createOrder(CreateOrderRequest request) {
    var order = new OrderEntity();
    order.id = UUID.randomUUID().toString();
    // ... sku and quantity from the request; status = "confirmed"
    order.persistAndFlush();                   // the state change; created_at read back
    var event = new OutboxEvent();
    event.aggregateId = order.id;
    event.eventType = "order.placed";
    event.payload = new OrderPlacedPayload(order.id, order.sku, order.quantity, order.status);
    event.persist();                           // same transaction: the outbox row
    return Response.status(Response.Status.CREATED).entity(order.toView()).build();
}
// No Kafka call on the request path: Debezium tails the WAL and publishes order.placed.
```

The database commit is the source of truth. The outbox + CDC turns it into a guaranteed, ordered event.

p. 27

> The whole trick is the @Transactional method: the insert of the order row and the insert of the outbox row run in one JTA transaction, so they commit or roll back together. Both rows are Panache entities over tables that db/init creates, and the outbox payload is a record stored in a jsonb column with @JdbcTypeCode(SqlTypes.JSON). There is no Kafka call inside the request path: if the broker is down, the order still commits and the event ships later when Debezium tails the write-ahead log and relays the outbox row in commit order. This decouples request latency and availability from Kafka's.
>
> Example 04 needs no outbox extension: the outbox is a small table (aggregate id, event type, JSON payload, created_at) mapped by a plain OutboxEvent entity, and a standard Debezium Postgres connector handles the CDC. The Debezium Outbox Event Router single-message transform unwraps the row into the event envelope on the connector side. The Debezium Quarkus outbox extension is not used: it brings its own table layout, and one table and one connector serve every language. The same commit-together discipline reappears in the saga appendix.

## [033] DATA · Consistency without distributed transactions: the saga (sldId 288)

A chain of local transactions; failures trigger compensating actions, never a cross-service rollback.

p. 28

> The saga is how you get consistency across services without a distributed transaction (there is no two-phase commit here, and you don't want one). It's a sequence of local transactions, each emitting the event that triggers the next: order created, payment taken, stock reserved, shipment booked. When a step fails (payment fails), you don't roll back; you run compensating actions for the steps that already committed (cancel the order). Flag that Appendix D goes deep on saga state, compensation and a tricky data-dependency case, for anyone who wants the mechanics.

## [034] Event-Driven (sldId 289)

05

Emit facts; let consumers decide.

> Section five — the asynchronous backbone we kept pointing at. The mental shift: a producer emits a fact about something that happened (order.placed) and does not know or care who consumes it. Consumers decide what to do. This inverts the dependency direction, and it is what decouples services in time and ownership.

## [035] EVENT-DRIVEN · The event backbone — one fact, many reactions (sldId 290)

order.placed fans out to consumers the producer never names. Add a consumer without touching the producer.

p. 29

> order.placed fans out to payment, shipping and notification — and the producer names none of them. The power move: you can add a new consumer (say, a fraud-check service) without touching or redeploying the producer. Contrast with the synchronous world, where adding a dependency means changing the caller. This is the open/closed principle at the architecture level. Kafka (run by Strimzi on Kubernetes) is the backbone; Pulsar is an alternative with similar semantics.

## [036] EVENT-DRIVEN · Producing and consuming with Reactive Messaging (sldId 291)

[chip] java · SmallRye Reactive Messaging

```java
// producer — order-service emits the fact; channel order-placed → topic order.placed
@ApplicationScoped
public class OrderEvents {
    @Inject @Channel("order-placed") Emitter<Order> emitter;   // Reactive Messaging
    public void publish(Order o) {
        emitter.send(KafkaRecord.of(o.id(), o));   // keyed; schema-aware serde
    }
}
// consumer — notification-service, Kafka-only by design
@ApplicationScoped
public class Notifier {
    @Incoming("order-placed")                       // offset tracked per group
    public Uni<Void> onOrder(Message<Order> msg) {
        return sendEmail(msg.getPayload())
            .chain(msg::ack);          // ack after the side-effect — at-least-once
    }
}
```

Ack after the side-effect, and make handlers idempotent — at-least-once delivery is the contract.

p. 30

> SmallRye Reactive Messaging is the Quarkus equivalent of aiokafka, but declarative. The producer injects an Emitter on a named @Channel mapped to a Kafka topic in application.properties; sending a KafkaRecord keys the message by order id. The consumer is a method annotated @Incoming. Two points: the channel is configured for manual ack, and we ack only once the side-effect (sendEmail) has succeeded. Ack first and then crash, and the work is lost. Because we ack after, a crash mid-handler means redelivery, so delivery is at-least-once and your handlers must be idempotent (dedupe by message key or an idempotency key). Exactly-once is mostly at-least-once plus idempotency. The serde is wired to Apicurio, the schema registry.

## [037] EVENT-DRIVEN · Schemas are the contract — the registry enforces them (sldId 292)

Apicurio holds versioned schemas; compatibility is checked at publish time so breaking changes are rejected early.

p. 31

> Events need contracts as much as REST and gRPC do, or more, because consumers are anonymous and you can't call them to coordinate. The schema (Avro, Protobuf or JSON Schema) lives in Apicurio. Producers and consumers fetch it; compatibility is checked at publish time so a breaking change is rejected before it ever reaches the topic. This is what makes adding a consumer safe. We come back to event versioning rules in Appendix B.

## [038] EVENT-DRIVEN · Event sourcing vs. event streaming (sldId 293)

Two patterns, often confused. Sourcing: the events are the state. Streaming: events are the transport.

p. 32

> The vocabulary clarification most teams need before they go further with events. Event sourcing means events are the database — there is no 'current state' row anywhere; current state is computed by folding the entire event history. Adding a credit to an account isn't UPDATE balance SET balance = balance + 100; it's INSERT INTO events VALUES ('credit', 100), and reading the balance means summing every event for that account (with snapshots for performance). Strong fit for audit-heavy systems (banking, healthcare records, regulatory), temporal queries ("what was the balance on March 3rd?"), and any domain where the history is itself a primary asset. Tools: Marten (Postgres-backed, .NET), EventStoreDB, Axon (JVM). Event streaming means events are how facts move between services — each service still keeps its current state in a normal database, but emits events ("order.placed", "payment.processed") that other services subscribe to. The event is a transport mechanism, not a storage mechanism. Strong fit for integration, fan-out, decoupling. Tools: Kafka, Pulsar, NATS JetStream. These are not mutually exclusive. A common combination is full CQRS: the write side is event-sourced (so you have an audit trail of state changes), and the read-side projections are fed by streaming those events to consumers that build denormalised views. The acid test: is the event itself the source of truth (sourcing), or is it a propagated fact about a change that happened in a store (streaming)? In most enterprise architectures, streaming is far more common than sourcing; sourcing fits domains where audit and replay are core.

## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka, Pulsar, Flink, NiFi (sldId 294)

Different jobs, often together: substrate (Kafka, Pulsar), compute (Flink), movement (NiFi, Debezium).

p. 33

> Each of the four tools does a different job. Kafka is the substrate: a partitioned, ordered, durable log. Consumers track their own offsets and can replay. It's the de facto event spine for cloud-native architectures; Strimzi runs it natively on Kubernetes. Pulsar is also substrate, in the same broad category as Kafka but with native pub/sub plus queue semantics in the same product, tiered storage that pushes cold data to cheap object stores automatically, and multi-tenancy built into the broker. Pulsar has a Kafka-protocol shim so consumers can speak Kafka while writing to Pulsar. Flink is compute: not a transport layer, but a stateful stream-processing engine. Flink sits on top of Kafka or Pulsar, consumes streams, applies operators (windowed aggregations, joins, filters, stateful transformations) with exactly-once semantics via checkpointing, and produces new streams. Alternatives: Kafka Streams (lighter, JVM-only, embedded library), Spark Structured Streaming (heavier, batch-mindset). NiFi is movement: a visual dataflow / ETL tool with 200+ source-and-sink connectors and back-pressure built in. Think of it as the answer to 'I need to get data from SFTP to Kafka to an object store with these transforms in the middle' — you draw the flow in the UI rather than writing a pipeline. Debezium (covered in the Data section) is the CDC variant of movement. Together they compose: typical pipeline is source DB → Debezium or NiFi → Kafka or Pulsar → Flink for windowed aggregations → sink. The mistake is treating these as competitors. They complement each other; pick by the question your team is asking: durably hold events (substrate), compute over them (Flink), move them around (NiFi/Debezium).

## [040] EVENT-DRIVEN · The log is the source of truth (sldId 295)

Consumers track their own offset; replay is just rewinding. Kafka (Strimzi) and Pulsar are logs, not queues.

p. 34

> The mental model correction most people need: Kafka is a log, not a queue. Messages are retained after they are read, and each consumer group tracks its own offset. That means replay is just rewinding an offset: a new consumer can process all of history, and a buggy consumer can be fixed and replayed. This is the foundation for event sourcing and for rebuilding stream-processing state, the subject of stream processing. Strimzi runs Kafka on Kubernetes; Pulsar offers similar log semantics with tiered storage.

## [041] Stream Processing (sldId 296)

06

Streams in, derived streams out.

> Section six builds directly on the log. Once events are a durable, replayable stream, you can compute over them continuously (filtering, joining, windowing, aggregating) and emit new derived streams. This is where real-time analytics, materialized views and complex event reactions live.

## [042] STREAM PROCESSING · Derive new streams from streams (sldId 297)

A streaming app is a topology of sources, stateful processors and sinks — joins, windows and aggregates.

p. 35

> A stream-processing app is a topology: sources (input topics), stateful processors (filter, join, window, aggregate) and sinks (output topics or stores). The output of one topology is just another stream that other services consume. Emphasize stateful — unlike a simple consumer, these processors keep local state (running totals, window buffers) that must survive restarts. That state-management problem is what the next code slide and KEDA slide address.

## [043] STREAM PROCESSING · A windowed aggregation with Kafka Streams (sldId 298)

[chip] java · Quarkus Kafka Streams

```java
// stream-processor RevenueTopology.java (excerpt), quarkus-kafka-streams
@ApplicationScoped
public class RevenueTopology {
    @Produces
    public Topology topology() {
        var builder = new StreamsBuilder();
        var orderSerde = new ObjectMapperSerde<>(OrderEvent.class);    // typed JSON in and out
        var accSerde = new ObjectMapperSerde<>(Acc.class);
        var outSerde = new ObjectMapperSerde<>(RevenueWindow.class);
        builder.stream(ORDERS, Consumed.with(Serdes.String(), orderSerde))
            .filter((key, order) -> order != null && order.merchantId() != null)
            .groupBy((k, o) -> o.merchantId(), Grouped.with(Serdes.String(), orderSerde))
            .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofSeconds(windowSeconds)))
            .aggregate(() -> new Acc(0, BigDecimal.ZERO),             // local state
                (merchant, order, acc) -> acc.add(order.total()),
                Materialized.with(Serdes.String(), accSerde))
            .toStream().map((window, acc) -> KeyValue.pair(window.key(),
                new RevenueWindow(/* start, end, merchant, count, revenue */)))
            .to(REVENUE, Produced.with(Serdes.String(), outSerde));
        return builder.build();
    }
}
```

Local state + a changelog topic gives fault-tolerant aggregation. The output is itself a stream other services can consume.

p. 36

> Kafka Streams is the JVM-native stream processor and the natural Quarkus counterpart to faust-streaming in the Python deck. The Topology is just a CDI-produced bean — Quarkus manages its lifecycle. The key idea is the Materialized state store: the per-merchant running total is local state, but it's backed by a Kafka changelog topic, so if the pod dies the state rebuilds by replaying the changelog — fault-tolerant local state with no external database in the hot path. The tumbling window (window.seconds, 10 seconds by default) buckets the aggregation by time; the accumulator, a count and a BigDecimal total, is serialized with ObjectMapperSerde, as are the input event (OrderEvent) and the output row (RevenueWindow), so nothing is parsed by hand, and each update is written to the output topic as a JSON row (window, merchant_id, order_count, revenue). The output revenue.by-merchant topic is itself a stream other services consume. If you'd rather express this as routing/EIP than a topology, Quarkus + Camel is the alternative; Flink is the heavyweight option.

## [044] STREAM PROCESSING · KEDA scales workers on the signal that matters (sldId 299)

Scale Kafka workers on consumer lag and HTTP services on request rate — both down to zero when idle.

p. 37

> KEDA closes the elasticity loop. The right scaling signal for an event consumer is consumer lag, how far behind the log it is, not CPU. KEDA reads that lag and scales workers up, and down to zero when there's no lag. For synchronous HTTP services, the KEDA http-add-on scales on request concurrency/rate. One mechanism, two signals. Scale-to-zero is a real cost lever for spiky workloads. The KEDA configuration covers both: lag for events and RPS for HTTP.

## [045] STREAM PROCESSING · Scale on lag (events) and on RPS (HTTP) (sldId 300)

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
# HTTP: scale the Quarkus service on concurrent requests (KEDA http-add-on)
apiVersion: http.keda.sh/v1alpha1
kind: HTTPScaledObject
metadata: { name: order-service }
spec:
  hosts: [orders.example.com]
  scaleTargetRef: { name: order-service, service: order-service, port: 8080 }
  replicas: { min: 0, max: 30 }
```

One mechanism, two signals: queue depth for async workers, concurrency for synchronous APIs.

p. 38

> Two manifests, one idea. The ScaledObject scales payment-consumer on Kafka lag for the order.placed topic, with minReplicaCount: 0 — true scale to zero when the topic is quiet, springing back when lag builds. The HTTPScaledObject does the same for the synchronous order-service based on request load via the http-add-on. The lagThreshold of 100 is the tuning knob: how many messages of backlog before adding a worker. Point out that scale-to-zero plus a cold-start budget is the trade-off to discuss with the audience for latency-sensitive paths.

## [046] Workflows and Jobs (sldId 301)

07

Not every unit of work is a request.

> Section seven. A lot of real work is not a synchronous request at all: it's a multi-step business process, or batch and scheduled work. Two topics: how to coordinate multi-step flows (orchestration vs choreography) and where long-running and periodic work belongs on Kubernetes. For orchestration in this stack, Quarkus Flow (a CNCF Serverless Workflow engine that runs inside your Quarkus app) is the natural choice; Appendix D uses it for the saga orchestrator.

## [047] WORKFLOWS AND JOBS · Orchestration vs. choreography (sldId 302)

A coordinator that commands keeps the flow in one place; events that trigger each other decouple but hide the flow.

p. 39

> The two ways to coordinate a multi-step process. Orchestration: a central coordinator explicitly commands each service in turn, so the flow is visible and observable, but the coordinator can become a god-service. Choreography: each service reacts to the previous one's event with no central brain — maximally decoupled, but the end-to-end flow is emergent and hard to see. Neither is universally right; choose by the selection criteria in the comparison. This connects straight to the saga discussion and Appendix D.

## [048] WORKFLOWS AND JOBS · Choosing between the two (sldId 303)

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

p. 40

> The decision heuristic: use orchestration for complex, long-lived business processes where you need auditability and a clear owner (order fulfillment, loan approval). Use choreography for simple, additive reactions where decoupling matters more than visibility (send a welcome email when a user signs up). The failure modes are mirror images: orchestration risks a god-service; choreography risks nobody owning the process and no one able to answer 'where is order 42 stuck?'. Observability (section 11) is what makes choreography survivable.

## [049] WORKFLOWS AND JOBS · Jobs, CronJobs and queue workers (sldId 304)

Long, batch or periodic work belongs in Jobs/CronJobs or a scaled queue worker — never on the request path.

p. 41

> Where non-request work lives on Kubernetes. A Job runs a task to completion (a data migration, a nightly export). A CronJob schedules Jobs (the reconciliation that runs at 2am). A queue worker continuously drains a topic and is scaled by KEDA on lag. The anti-pattern: doing long or heavy work inside an HTTP handler, blocking the request and timing out the client. The rule of thumb on screen — long, batch or periodic work never belongs on the request path. Hand it to a Job or a worker and return immediately, ideally with a status URL the client can poll. In-app, the Quarkus Scheduler (@Scheduled) and quarkus-flow-scheduler cover recurring work without leaving the JVM, while Kubernetes Jobs/CronJobs own the heavier or isolated batch runs.

## [050] API Management (sldId 305)

08

Treat the API surface as a platform.

> Section eight zooms out from individual services to the API surface as a whole. Management is four cooperating concerns, not a product you buy: runtime control (gateway and mesh), contracts (registry), discovery (metadata), and signals (observability). The next three sections each take one of these in depth.

## [051] API MANAGEMENT · Four cooperating planes (sldId 306)

Gateway and mesh at runtime; registry for contracts; metadata for discovery; observability for signals.

p. 42

> The four planes, and they map exactly to the rest of the platform sections. Runtime plane: the gateway and Istio mesh handle traffic, auth, rate-limiting and resilience. Contract plane: the registry (section 9) holds every API and event schema, versioned and gated. Discovery plane: metadata/catalog (section 10) lets people find and trust APIs. Signal plane: observability (section 11) tells you what is happening. The point: these are distinct responsibilities with distinct owners, not one monolithic 'API gateway product' that tries to do everything.

## [052] API MANAGEMENT · Versioning and evolution are part of management (sldId 307)

- Evolve additively — new optional fields and endpoints; never repurpose or remove without a new version.
- Carry a major version in the path (/v2) or media type; deprecate with headers and a sunset date.
- The registry's compatibility rules (BACKWARD / FORWARD / FULL) enforce this mechanically at publish time.
- Run old and new side by side; migrate consumers off the old contract before you retire it.
- Lifecycle: design → register → publish → consume → deprecate → retire — each step has an owner and a gate.

p. 43

> Versioning is a management concern, not an afterthought. The core discipline: evolve additively; add optional fields and new endpoints, never repurpose a field or remove one without a deprecation period. When you must break, carry a major version (in the path or media type) and run old and new side by side with a published sunset date, migrating consumers off before retiring. The registry's compatibility rules enforce the additive discipline mechanically at publish time. The bold lifecycle line is the takeaway: every contract moves design → register → publish → consume → deprecate → retire, and each transition has an owner and a gate. Appendix B drills into how REST, gRPC and GraphQL each handle this differently.

## [053] API Registry (sldId 308)

09

One versioned home for every contract.

> Section nine. If contracts are the boundary, they need one authoritative home. The registry is where every OpenAPI spec, .proto, AsyncAPI doc and event schema lives — versioned, compatibility-checked, and gated in CI. This is the difference between 'we have contracts somewhere in git' and 'contracts are enforced before code ships'.

## [054] API REGISTRY · Apicurio: contracts, versioned and gated (sldId 309)

OpenAPI, AsyncAPI, proto and Avro/JSON schemas live in one registry with compatibility rules and CI gating.

p. 44

> Apicurio is the concrete registry in this stack. Every contract type lands here: REST OpenAPI, GraphQL SDL, gRPC .proto, and event schemas (Avro/JSON). Each artifact has versions and a compatibility rule (BACKWARD, FORWARD, FULL). At publish time the registry checks the new version against the rule and rejects incompatible changes. Producers register; consumers fetch and generate stubs. The serde libraries for Kafka pull schemas from here by ID at runtime. A CI gate turns this into an automatic guardrail.

## [055] API REGISTRY · Gate breaking changes in CI with Maven (sldId 310)

[chip] xml · Maven + Apicurio

```xml
<!-- pom.xml: the apicurio-registry-maven-plugin checks the rule in CI -->
<plugin>
  <groupId>io.apicurio</groupId>
  <artifactId>apicurio-registry-maven-plugin</artifactId>
  <version>3.3.3</version>
  <executions><execution>
    <goals><goal>register</goal></goals>
    <configuration>
      <registryUrl>http://apicurio.registry.svc/apis/registry/v3</registryUrl>
      <dryRun>true</dryRun>   <!-- check the rule, store nothing -->
      <artifacts><artifact>
        <groupId>orders</groupId>
        <artifactId>order-placed</artifactId>
        <artifactType>AVRO</artifactType>
        <ifExists>CREATE_VERSION</ifExists>   <!-- a new version -->
        <file>src/main/avro/order-placed.avsc</file>
      </artifact></artifacts>
    </configuration>
  </execution></executions>
</plugin>
```

The dry-run register fails the build on an incompatible change — the contract is enforced before code ships, not after.

p. 45

> This is the guardrail that makes the whole contract story real, done the Maven way. The apicurio-registry-maven-plugin's register goal with dryRun set checks the new schema against the artifact's compatibility rule in the registry without storing it, and fails the build (and the merge) if it is incompatible. The older test-update goal still exists in 3.3.3 but is deprecated in favour of dryRun. The point to make: the contract is enforced before code ships, not discovered broken in production by a downstream team. The rule (e.g. BACKWARD — new consumers can read old data) is set once per artifact and enforced automatically forever; a separate register goal publishes on the main branch after merge. Tie it back: this is design-first from section 1, now mechanized in the build.

## [056] API Metadata (sldId 311)

10

If they can't find it, it doesn't exist.

> Section ten. A contract that's enforced but undiscoverable is half useless. Metadata is the discovery and trust layer: a searchable catalog of every API, topic and table, with ownership, lineage and quality signals. If a consumer can't find your API and trust it, they'll build their own or screen-scrape — and your boundary erodes.

## [057] API METADATA · Discovery, lineage and ownership (sldId 312)

OpenMetadata ingests from services, the registry and Kafka to build a searchable catalog with lineage.

p. 46

> OpenMetadata is the catalog in this stack. It ingests from many sources (OpenAPI specs, the Apicurio registry, Kafka topics, Postgres schemas) and builds one searchable catalog. The differentiator over a wiki is automated lineage: it knows that this topic feeds that table feeds this API, so it can answer 'if I change this field, who breaks?' before you change it. Ingestion is a scheduled connector, so the catalog stays current without manual upkeep. What consumers get from the catalog is the point of running it.

## [058] API METADATA · What the catalog gives every consumer (sldId 313)

- Discovery — search across APIs, topics and tables; find the owning team and how to get access.
- Trust — published SLOs, data-quality test results, freshness, and a tier/criticality rating.
- Lineage — column- and topic-level lineage answers 'if I change this, who breaks?' before you change it.
- Ownership & governance — tags, classifications (PII), and accountable owners attached to every asset.
  - Ingestion runs as a scheduled connector against OpenAPI specs, the registry, Kafka and Postgres.

p. 47

> Four concrete payoffs for consumers. Discovery: search across APIs, topics and tables, and find the owning team and how to get access — no more asking around in Slack. Trust: published SLOs, data-quality results, freshness and a criticality tier tell you whether to depend on it. Lineage: column- and topic-level impact analysis answers the change-safety question proactively. Ownership and governance: tags, PII classifications and accountable owners on every asset — which is also what your compliance team needs. The throughline of sections 9–10: a contract is only as good as your ability to find it, trust it, and know who owns it.

## [059] Observability (sldId 314)

11

Instrument once; correlate everything.

> Section eleven, and the one that makes everything else operable. In a distributed system you cannot debug by reading one log file — a single user action touches five services. Observability is how you reconstruct that story. The key word is correlate: traces, metrics and logs become useful together only when they share a trace_id so you can pivot between them.

## [060] OBSERVABILITY · Three signals, one correlated story (sldId 315)

OpenTelemetry emits traces, metrics and logs; the LGTM-style stack stores them and Grafana joins them.

p. 48

> Three signals, each answering a different question. Traces: where did the time go and which service failed in this one request? Metrics: what are the aggregate rates, errors and latencies over time? Logs: what exactly happened in this component? OpenTelemetry is the vendor-neutral way to emit all three from your code. The LGTM-style stack stores them (Tempo for traces, Mimir/Prometheus for metrics, Loki for logs), and Grafana joins them. The magic is the shared trace_id linking a metric spike to the exact traces and logs behind it. The instrumentation comes first, then the trace.

## [061] OBSERVABILITY · The signals in depth — traces, metrics, logs, baggage, profiles (sldId 316)

Three classic pillars plus two that matter more every year. OpenTelemetry emits all five; one trace_id correlates them.

p. 49

> Expand the 'three pillars' framing into the five signals modern observability uses. Traces answer where the time went and which hop failed in one request. Metrics answer the trend question — aggregate rates, errors, latencies over time (the RED method: Rate, Errors, Duration; the USE method: Utilisation, Saturation, Errors). Logs answer what exactly happened in one component. Baggage is the signal most people miss — it's key-value context (tenant_id, user_tier, feature_flag) that propagates along the whole trace, so a value set at the edge is readable in a Kafka consumer three hops downstream. Profiles are the newest signal — continuous CPU / memory / lock sampling per service, answering which function is burning the CPU (Pyroscope, Parca, Grafana Phlare). The correlation bar at the bottom is the whole point: traces, metrics, logs, baggage and profiles all share trace_id + span_id + resource attributes (service.name, k8s.pod.name, deployment.version), so you can pivot — a metric spike leads to an exemplar trace, which leads to its logs, which leads to its CPU profile. OpenTelemetry is the vendor-neutral SDK and wire format for all five; traces/metrics/logs are GA, baggage is stable, profiling is the newest (the OTel profiling signal reached the ecosystem in 2024).

## [062] OBSERVABILITY · What each signal answers — and when to reach for it (sldId 317)

- Traces — 'where did the time go in this request, which hop failed?' Reach for it when debugging latency or a specific failed request. Stored in Tempo / Jaeger.
- Metrics — 'what is the aggregate rate / error / latency trend, is it getting worse?' Reach for it for dashboards, alerting, capacity. RED (Rate, Errors, Duration) for request-driven services; USE (Utilisation, Saturation, Errors) for resources. Stored in Prometheus / Mimir.
- Logs — 'what exactly happened in this component at this instant?' Reach for it for detail the trace doesn't carry. Structured (JSON), keyed by trace_id. Stored in Loki / ELK.
- Baggage — 'carry a value (tenant_id, user_tier) along the whole request so downstream services and their telemetry can use it.' Set once at the edge, readable everywhere downstream. W3C Baggage spec.
- Profiles — 'which function is burning CPU / allocating memory / holding locks, continuously, in production?' Reach for it for the latency the trace shows but doesn't explain. Pyroscope / Parca.
  - The discipline: emit traces + metrics + logs always; add baggage when downstream needs request-scoped context; add profiling when you have CPU/memory mysteries a trace can't resolve.

p. 50

> Walk each signal and the question it answers — the framing 'what question does this answer' is more useful to an engineer than 'what is this signal.' Traces are per-request; metrics are aggregate; logs are detail. The two newer ones deserve emphasis. Baggage is underused: most teams propagate trace context but never realise they can also propagate their own key-values (tenant, user tier, AB-test cohort) along the same mechanism, and then filter traces and logs by tenant. Profiling is the frontier: continuous profilers (Pyroscope, Parca, Grafana Phlare) run in production at low overhead and answer the 'the trace says this span took 200ms but why' question by showing the actual call stack burning the CPU. The sub-bullet is the practical guidance on which to adopt when.

## [063] OBSERVABILITY · Auto-injection vs. instrumentation — three distinct things (sldId 318)

- Manual instrumentation — you write the spans. tracer.spanBuilder(...).startSpan(), span.setAttribute(...), span.addEvent(...). Needed for business operations the libraries can't know about ('reserve_stock', 'score_fraud'). The most signal per line, the most effort.
- Auto-instrumentation — a library / agent wraps known frameworks for you. HTTP servers and clients, gRPC, JDBC / database drivers, Kafka, Redis — each becomes spans with zero code change. Covers the plumbing; misses your domain.
- Auto-injection — the platform puts the auto-instrumentation agent into the pod for you. The OpenTelemetry Operator watches for an annotation (instrumentation.opentelemetry.io/inject) and mutates the pod at admission — no agent in your image, no Dockerfile change, no redeploy of the app to add tracing.
- How they layer: auto-injection delivers the agent → the agent provides auto-instrumentation of frameworks → you add manual spans for business logic on top. All three coexist in the same trace.
  - Trade-off: auto-instrumentation is convenient but can be noisy (every framework call becomes a span) and slightly slower. Manual is precise but is work you own. Most teams: auto for the plumbing, manual for the domain, injection to roll it out fleet-wide.

p. 51

> Auto-injection, auto-instrumentation and manual instrumentation are three things people conflate. Manual: you call the tracer API yourself; necessary for domain operations. Auto-instrumentation: the OTel instrumentation libraries (or a language agent) wrap known frameworks: your HTTP handler, your DB driver, your Kafka client all emit spans without you touching them. Auto-injection: a Kubernetes-level mechanism; the OpenTelemetry Operator sees a pod annotation and injects the language agent + config as an init container / env vars at admission time, so you don't even put the agent in your image. Per-language specifics: Python: 'opentelemetry-instrument' wrapper or the operator injects it; instrumentation packages per library. Java/Quarkus: the OTel Java agent (-javaagent) auto-instruments everything; Quarkus also has build-time OTel extension. Spring: Micrometer Tracing + the OTel bridge, or the Java agent. .NET: OTel auto-instrumentation via the OpenTelemetry.AutoInstrumentation package or the operator's .NET injection; manual via System.Diagnostics.ActivitySource. The bold line is the mental model: injection delivers the agent, the agent instruments frameworks, you add manual spans on top — they layer into one trace.

## [064] OBSERVABILITY · Auto-instrument with Quarkus OpenTelemetry (sldId 319)

[chip] java · Quarkus OpenTelemetry

```java
# application.properties — add quarkus-opentelemetry; REST, gRPC and
# Reactive Messaging are instrumented automatically. Just point it at the Collector:
quarkus.otel.exporter.otlp.endpoint=http://otel-collector:4317
// Only custom business spans need code — @WithSpan does it declaratively
@ApplicationScoped
public class OrderService {
    @Inject @GrpcClient("inventory") Inventory inventory;
    @WithSpan("reserve_stock")               // custom span on this method
    public Uni<ReserveReply> reserve(String sku, int qty) {
        return inventory.reserveStock(req(sku, qty));
    }
    // trace_id flows REST -> gRPC -> Kafka -> consumer, automatically
}
```

The OTEL exporter sends traces to Tempo, metrics to Mimir/Prometheus, logs to Loki — all keyed by trace_id.

p. 52

> The payoff line is how little code this takes. Adding the quarkus-opentelemetry extension auto-instruments every REST endpoint, gRPC call and Reactive Messaging hop — spans are created and context is propagated onto events with zero code. You only hand-write spans for custom business operations worth measuring, and even that is declarative: @WithSpan on a method. The crucial behaviour is the last comment: the trace_id flows REST → gRPC → Kafka → consumer with no manual plumbing, because the Quarkus instrumentation injects and extracts context at each hop. The OTLP exporter ships everything to the Collector keyed by that trace_id. Instrument once, correlate everything.

## [065] OBSERVABILITY · How correlation works — context propagation (sldId 320)

The trace context rides in-band with the request (W3C traceparent). The same trace_id at every hop is what stitches the story.

p. 53

> Demystify the magic word 'correlation.' It is not a backend join — it's the trace context physically travelling with the request, in-band, at every hop. The W3C traceparent header is the standard: version-traceid-parentspanid-flags. The trace_id (16 bytes) is constant across every hop of the request — that constancy is literally what stitches the distributed story into one trace. The span_id is new per operation, and each span records its parent span_id, which is how the backend rebuilds the tree. The flags byte carries the sampling decision (01 = sampled) so every hop honours the same decision. Alongside traceparent rides tracestate (vendor-specific) and baggage (your key-values). The transport differs per hop but the mechanism is identical: HTTP uses the traceparent header, gRPC uses metadata, Kafka uses message headers. The SDK injects the context on the way out and extracts it on the way in — automatically, which is why auto-instrumentation 'just works' across services. This propagated context is exactly why the same trace_id shows up on the trace waterfall, on every structured log line, and as an exemplar on your metrics — they all read it from the same in-band context.

## [066] OBSERVABILITY · Baggage in practice — carry request context downstream (sldId 321)

[chip] java · Quarkus + OpenTelemetry baggage API

```java
import io.opentelemetry.api.baggage.Baggage;
import io.opentelemetry.api.trace.Span;
// Set baggage at the edge (a JAX-RS request filter)
@Provider
public class BaggageFilter implements ContainerRequestFilter {
    public void filter(ContainerRequestContext ctx) {
        Baggage.current().toBuilder()
            .put("tenant_id", ctx.getHeaderString("X-Tenant"))
            .put("user_tier", lookupTier(ctx))
            .build()
            .makeCurrent();                       // rides the whole trace
    }
}
// Read baggage anywhere downstream  —  even in a Reactive Messaging consumer
@Incoming("order-placed")                // topic order.placed
public void handle(OrderEvent ev) {
    String tenant = Baggage.current().getEntryValue("tenant_id");
    Span.current().setAttribute("tenant_id", tenant);   // filterable in trace UI
}
```

Set once at the edge; read anywhere downstream. Pin to the span to filter traces by tenant_id.

p. 54

> Quarkus uses the OpenTelemetry Java API directly for baggage. A JAX-RS ContainerRequestFilter sets tenant_id and user_tier at the edge; .makeCurrent() puts them in the active context, and the Quarkus OTel extension propagates them on every downstream call (REST Client, gRPC, Reactive Messaging to Kafka) via the W3C baggage header. A downstream @Incoming consumer reads Baggage.current().getEntryValue('tenant_id') with no explicit plumbing. Pin it to the span with Span.current().setAttribute(...) so it's queryable in Jaeger/Tempo. Caution: baggage is on the wire to every downstream hop — never put secrets or PII in it.

## [067] OBSERVABILITY · A single trace stitches the whole request (sldId 322)

One trace_id propagates from the edge REST call through gRPC, Kafka and the consumer — five services, one story.

p. 55

> This is what the instrumentation buys you, visually. One trace_id propagates from the edge REST POST through the gRPC ReserveStock call, onto the published order.placed event, and into the consumer that sends the notification. Five services, one readable waterfall. Point at the time axis: you can see exactly which span dominated latency. That same trace_id appears as an exemplar on your metrics and on every log line, so a latency alert is one click from the offending trace and its logs. This is what makes the choreographed, event-driven design from earlier sections debuggable.

## [068] OBSERVABILITY · Sampling — head vs. tail (sldId 323)

You can't store every trace at scale. Head decides at the start (cheap, blind); tail decides at the end (smart, costly).

p. 56

> The cost-control reality: at scale you cannot store every trace, so you sample. The key question is when the keep/drop decision is made. Head sampling decides at the start, in the SDK, before the trace even completes — typically 'keep 1 in N' (probabilistic) or 'keep N per second' (rate-limiting). It's cheap and low-overhead, but it is blind at decision time: it can't keep a trace because it errored or was slow, because it decides before knowing. Tail sampling decides at the end, in the Collector, after the whole trace has been seen — the Collector buffers spans, waits for the trace to complete, then applies rules: keep all errors, keep all traces over 500ms, keep rare routes, sample the boring successful ones at 1%. Tail is smart but costs memory (buffering in-flight traces) and CPU (the Collector does real work). The strategies, named: probabilistic (keep X%), rate-limiting (cap per second), parent-based (follow the upstream's decision so a trace isn't half-sampled), and tail rules (error / latency / attribute based). The common production setup is both: a parent-based head sample for a representative baseline, plus tail sampling at the Collector to guarantee every error and every slow trace is captured regardless of the baseline rate. Two rules to drill home: always sample by trace, not by span (a half-sampled trace is worse than no trace), and propagate the sampling flag (the 01 in traceparent) so every service agrees. Metrics and logs are usually not sampled the same way: metrics aggregate everything (you don't sample a counter), and logs are typically kept in full with retention limits or sampled on their own policy.

## [069] OBSERVABILITY · Choosing a sampling strategy (sldId 324)

- Probabilistic (head) — keep a fixed percentage (e.g. 10%). Simplest; predictable volume; blind to errors. Good baseline for high-traffic, low-stakes services.
- Rate-limiting (head) — keep at most N traces/sec per service. Protects your backend from traffic spikes; good when load is bursty.
- Parent-based (head) — honour the upstream service's sampling decision (carried in the traceparent flags). Essential in distributed systems: it stops a trace being sampled at service A but dropped at service B, which would give you broken half-traces.
- Tail-based (Collector) — buffer the whole trace, then keep by rule: all errors, all traces over a latency threshold, rare routes, plus a small % of the rest. The gold standard for keeping what matters, at the cost of Collector memory + CPU.
- Recommended production setup: parent-based head sampling at a modest baseline (1-10%) for representativeness, plus tail sampling at the Collector to guarantee every error and slow trace is kept.
  - Don't sample metrics the way you sample traces (metrics aggregate everything). Keep logs in full with retention limits, or sample them on their own policy keyed by trace_id so a kept trace keeps its logs.

p. 57

> The decision guide for sampling. Probabilistic is the simplest and the most common starting point — keep 10%, predictable volume. Rate-limiting is better when traffic is bursty because it caps absolute volume. Parent-based is non-negotiable in a distributed system: without it, service A samples a trace but service B independently drops it, and you get a broken trace with holes — worse than no trace. Tail-based sampling gives the most control: because the Collector sees the whole trace before deciding, it can guarantee you keep every error and every slow request, which are the traces you want during an incident. The cost is the Collector must buffer in-flight traces (memory) and evaluate rules (CPU), and it must see all spans of a trace (which constrains how you load-balance the Collector — use a trace-ID-aware load balancer). The recommended setup combines head (for a cheap representative baseline) and tail (for guaranteed capture of the interesting traces). The sub-bullet is the reminder: traces, metrics and logs are sampled differently — you never sample a metric counter, and logs typically follow their own retention or are sampled to match their parent trace.

## [070] OBSERVABILITY · Prove it with simple tools before you ship (sldId 325)

- curl / Postman — exercise REST contracts and inspect status codes, headers and pagination.
- hey — quick HTTP load to watch latency, error rate and the KEDA http-add-on scale the service.
- ghz — load-test gRPC endpoints and confirm timeouts and retries behave under pressure.
- GraphQL UI (GraphiQL) — explore the composed schema and watch the gateway fan out in Tempo.
- Kiali — read the live service-mesh topology, mTLS status and request flow during a load test.

p. 58

> Keep testing pragmatic: you don't need a heavy framework to validate this architecture. curl and Postman exercise REST contracts and check status codes and pagination. hey throws quick HTTP load so you can watch latency and error rate and see the KEDA http-add-on add replicas. ghz is the gRPC load tester: confirm your Istio timeouts and retries behave under pressure. The GraphQL UI (GraphiQL, which Quarkus serves in dev) explores the composed schema and, with tracing on, shows the gateway fanning out in Tempo. Kiali visualizes the live mesh: topology, mTLS status and real-time request flow during a load test. The message: prove the behaviour with simple tools before you ship, not after an incident.

## [071] Security (sldId 326)

12

Defence in depth, in layers.

> Section 12 — security. The Anti-Patterns section that used to be 12 has shifted to 13. We organise this section around two ideas: the 4 C's of cloud-native security (concentric layers, each protecting what is inside it), and the seven patterns that you'll meet over and over in practice. The bias of this section: security is not a single product or a single team. It's a property of how the system is designed and run, owned at every layer. Each pattern here exists because no single layer is enough on its own.

## [072] SECURITY · The 4 C's of cloud-native security (sldId 327)

Cloud → Cluster → Container → Code. Concentric layers, each layer protects what is inside.

p. 59

> The mental model from the CNCF security paper. Four concentric layers of responsibility, each enforcing controls appropriate to its scope. Cloud is the outermost layer (IAM, VPC, KMS, audit logs, region selection), owned by the platform team or cloud admin. Cluster is the Kubernetes layer (RBAC, NetworkPolicy, Pod Security Standards, admission control), owned by platform/SRE. Container is the workload (minimal base images, non-root users, signed images, vulnerability scanning, secret mounting), owned jointly by app teams and platform. Code is the innermost layer (secure defaults, input validation, dependency scanning, secrets handling), owned by app teams. The point of the concentric metaphor: a weakness in any layer leaks into the inner ones. Strong code on a weak container is still vulnerable. Strong container on a weak cluster is still vulnerable. We design controls at all four. The 4 C's table lists each layer's controls and its owner.

## [073] SECURITY · The 4 C's — what each layer enforces, and who owns it (sldId 328)

- Cloud — IAM (principles of least privilege), VPC isolation, KMS for keys, audit logging, region & data-residency controls. Owner: platform / cloud admin.
- Cluster — Kubernetes RBAC, NetworkPolicy (default-deny + targeted allows), Pod Security Standards (restricted profile), admission control (OPA Gatekeeper / Kyverno), secret encryption at rest, etcd encryption. Owner: platform / SRE.
- Container — minimal base images (distroless, UBI-minimal), non-root users, read-only root filesystems, image signing (Sigstore / Cosign), vulnerability scanning (Trivy, Grype) on every build, secret mounting via projected volumes (never bake secrets into images). Owner: app team + platform.
- Code — secure defaults (parameterised queries, output encoding), input validation at the trust boundary, dependency scanning (Dependabot, Snyk, OSV-Scanner), secrets handling (no plaintext in source, no logging secrets), CSRF / SSRF / XXE awareness, threat modeling. Owner: app team.
- Cross-cutting: observability (audit who did what when), incident response runbooks, threat modeling per service, regular dependency updates.
  - The pattern: a control at the wrong layer is the most common source of false confidence. Network ACLs cannot save you from an SQL injection. Code-level input validation cannot save you from a compromised image. Defence in depth is real.

p. 60

> Walk each layer. The Cloud layer is where you control the perimeter and the identities and the keys; failures here often look like 'someone left a storage bucket open to the internet' or 'an over-permissive IAM role enabled lateral movement to another account.' The Cluster layer is the Kubernetes operating system for your workloads; failures look like 'the developer Pod could reach the database Pod' (no NetworkPolicy) or 'a privileged container was admitted' (no Pod Security Standards). The Container layer is about the image and runtime; failures look like 'a CVE in the base image' or 'the container ran as root and got out via a kernel exploit' or 'a secret was in the image.' Code is where most developer focus already lives. The sub-bullet is the take-home: a control at the wrong layer is false confidence. The pattern catalog holds seven patterns that show up across these four layers.

## [074] SECURITY · Seven patterns to know (sldId 329)

- Sidecar — move security concerns out of the app into a companion process. mTLS, JWT, audit, rate-limiting belong there.
- Valet Key — hand the client a short-lived signed token to access a resource directly. Less app proxying, less attack surface.
- Strangler Fig (for security modernisation) — encapsulate legacy auth behind an API gateway, replace pieces over time.
- Zero-Trust / Identity-Aware Proxy — every request authenticated and authorised. Perimeter trust is dead.
- Policy-as-Code — security gates declared in Git, evaluated at admission and at build. No human runs a checklist.
- Bulkhead — isolate resources so one failure (or compromise) cannot starve or cascade into others.
- Claim-Check — send a reference, not the payload. Keeps PII out of message bus history and limits the blast radius if a topic leaks.
  - The seven appear in different layers and combine. Each slide that follows shows the pattern, then implementation — platform config where it's mostly YAML, code where it's mostly code.

p. 61

> The roadmap for the next fourteen slides. These patterns span the 4 C's: Zero-Trust and Policy-as-Code are cluster-layer; Sidecar straddles cluster and container; Valet Key, Bulkhead, and Claim-Check are mostly code-layer; Strangler Fig is architecture-layer (modernisation). You'll see each pattern with a diagram explaining how it works, then either a YAML configuration block (for the platform-heavy patterns) or language-specific code (for the code-heavy patterns). Use the sub-bullet to set audience expectation that the section alternates between pattern-and-implementation pairs.

## [075] SECURITY · SIDECAR · Sidecar pattern — push security out of the app (sldId 330)

mTLS, JWT validation, rate limiting, audit logging — a companion process in the same Pod handles them all.

p. 62

> The sidecar pattern — a separate container running in the same Pod as the application, sharing localhost. The sidecar handles cross-cutting security concerns: terminates mTLS, validates JWTs, rate-limits, audits, enforces policy. The app receives only authenticated, authorised requests with trusted headers attached (X-Forwarded-Client-Cert, the validated JWT claims, the request ID). Why this matters: one security policy applied uniformly across every workload regardless of language. Same Envoy sidecar protects your Java app, your Python app, your Go app. App teams write business code, not crypto code. The sidecar is enforced by the platform (Istio injects them automatically) so it can't be disabled by accident. Examples in the field: Istio Envoy sidecars (the dominant choice), Linkerd2-proxy, OPA Sidecar for policy decisions, Cilium L7 with per-endpoint policy.

## [076] SECURITY · SIDECAR · Reading the sidecar's trusted headers (sldId 331)

- The sidecar handles mTLS, JWT validation, and policy decisions — the app trusts the headers the sidecar attaches and reads them as plain values.
- X-Forwarded-Client-Cert — the validated client identity from mTLS. Includes the SPIFFE ID (spiffe://cluster.local/ns/orders/sa/order-service) or the X.509 Subject. Set only by the sidecar; the app must reject requests that don't have it.
- JWT claims — the sidecar validates the signature, then passes the claims forward as a header or sets request.auth.claims via an envoy filter. The app reads sub, aud, scope, custom claims; it never re-validates the signature.
- Request ID — the sidecar attaches X-Request-Id for traceability. Log it; propagate it to downstream calls; correlate it with audit logs.
- Mode: only trust these headers when the sidecar is in front. In direct-to-Pod traffic (port-forward, debugging, mistakes), they could be spoofed. Use a NetworkPolicy to ensure traffic only enters via the sidecar's mTLS port.
  - Examples: Istio Envoy sidecars (auto-injected), Linkerd2-proxy, OPA Sidecar (policy decisions), Cilium L7 policy. License: all Apache 2.0.

p. 63

> The audience point: the sidecar pattern works only if the app uses the headers the sidecar attaches. The most common failure mode is an app that ignores X-Forwarded-Client-Cert and falls back to 'allow if you got here.' Make the headers required, not optional. The second-most-common failure mode is forgetting that traffic can sometimes bypass the sidecar (port-forward for debugging, host networking, direct pod-to-pod calls within the same node). NetworkPolicy is what closes that gap — only allow inbound traffic on the sidecar's mTLS port, never the app's container port directly. With both the sidecar and the NetworkPolicy, the app can fully trust the headers and become much simpler — no crypto code, no JWT parsing library, just header reads.

## [077] SECURITY · VALET KEY · Valet key pattern — short-lived signed token, direct access (sldId 332)

App mints a scoped, time-bound token; client uses it directly against the resource. App never proxies the bytes.

p. 64

> The valet key pattern: instead of streaming a large file through your application, the application mints a scoped, time-bound, operation-restricted token (a 'valet key') and the client uses it to interact directly with the storage system. Pros: dramatically less data through the application (memory, bandwidth, latency); no long-lived credentials at the client; no app-side credential to leak; the token can expire and be revoked. Cons: requires the storage side to validate tokens; the token's permissions and TTL must be carefully scoped — a leaked token still has its window. Every implementation has the same shape: sign the operation, the object key and the expiry with a key the storage side can check. Example 12 mints and verifies such a ticket in the service itself (HMAC-SHA256, an HS256 JWT in Go and C++), and most object stores, open-source ones included, accept signed URLs of the same shape. The code shows the pattern in the service's language.

## [078] SECURITY · VALET KEY · Valet key — scoped, time-bound, op-restricted (sldId 333)

[chip] java · Quarkus REST + javax.crypto (HmacSHA256)

```java
// ValetKeyService.java (excerpt), examples/12-security/quarkus: HMAC-SHA256 valet key
@ApplicationScoped
public class ValetKeyService {
    private static final int TTL_SECONDS = 300;                       // time-bound
    private final byte[] secret;          // VALET_SECRET, injected through @ConfigProperty
    public Map<String, Object> mint(String resource, String operation) {
        long expires = System.currentTimeMillis() / 1000 + TTL_SECONDS;
        String payload = resource + ":" + operation + ":" + expires;  // one object, one op
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("resource", resource);
        result.put("operation", operation);
        result.put("expires", expires);
        result.put("token", hmac(payload));               // HmacSHA256, hex-encoded
        return result;
    }
    public boolean verify(String resource, String operation, long expires, String token) {
        if (System.currentTimeMillis() / 1000 > expires) return false;   // expired
        String expected = hmac(resource + ":" + operation + ":" + expires);
        return MessageDigest.isEqual(token.getBytes(), expected.getBytes()); // constant time
    }
}
// OrderResource maps POST /valet-key to mint() and GET /verify-valet to verify()
```

p. 65

> The handler mints a ticket that authorises one operation (GET or PUT) on one resource for 300 seconds; after that it is worthless. In Example 12 the ticket is an HMAC-SHA256 signature over resource:operation:expires, keyed with VALET_SECRET (javax.crypto.Mac with HmacSHA256). POST /valet-key returns the resource, the operation, the expiry and the token.
>
> The verifier (GET /verify-valet in the example, the storage gateway in a real system) rejects an expired ticket first, recomputes the signature and compares the two with MessageDigest.isEqual, a constant-time comparison. A changed resource, operation or expiry gives a different signature, so any tampering is a 403.
>
> The application stays out of the data path: the client presents the ticket to the storage side directly. Most object stores, open-source ones included, accept signed URLs of the same shape: the method, the object key and the expiry signed into the URL. A user-scoped resource path also lets the store's policy restrict each user to their own prefix as defence in depth.

## [079] SECURITY · STRANGLER FIG · Strangler Fig for security modernisation (sldId 334)

- Use case: encapsulate legacy authentication (LDAP-only, HTTP Basic, hardcoded session cookies) behind a modern API gateway, then replace the legacy auth path one service at a time.
- Step 0: introduce the gateway in front of the monolith. Clients now hit the gateway, which forwards to the legacy auth. Day-zero behaviour unchanged.
- Step 1: the gateway terminates TLS, validates JWTs from a modern IdP (Keycloak, Dex), and translates to whatever the legacy expects; it speaks both languages.
- Step 2: per route, switch the gateway from 'forward legacy headers' to 'forward only the JWT claims to the new service'. Legacy auth is no longer in the path for that route.
- Step 3: when no routes still need legacy auth, remove it.
- Bounded blast radius: each route's auth migration is a config change in the gateway, reversible without a release.
  - See Appendix K for the general strangler-fig family (identify → move → redirect, with proxy, with shared database, with content-based routing). Same mechanics, applied to auth instead of business logic.

p. 66

> The strangler fig was covered as a general pattern in Appendix K — here it shows up specifically for security modernisation, which is a common need: most enterprises have legacy auth (LDAP-only, custom SSO, NTLM, hardcoded API keys) buried in critical systems, and a 'big bang' replacement is too risky. The gateway becomes the bilingual translator: it validates modern JWTs from your IdP at the edge and translates to whatever the legacy backend expects (X-Remote-User header, basic auth, NTLM, custom session cookie). Per route, you migrate when the new path is verified — if anything breaks, flip the gateway config back to forwarding legacy headers. The sub-bullet points to Appendix K for the full mechanics; this slide is the application of those mechanics to a specific security need.

## [080] SECURITY · ZERO-TRUST · Zero-trust / Identity-Aware Proxy (sldId 335)

Every request authenticated and authorised, on every hop. Perimeter trust is dead. SPIFFE inside, IAP at the edge.

p. 67

> The model: there is no trusted network. Every request, from any source, to any service, on every hop — authenticated and authorised. The old model (top of the diagram) was 'get inside the VPN, everything inside is trusted': once an attacker is in, they move laterally with little resistance. The new model (bottom): the user authenticates to an IAP (Identity-Aware Proxy) which evaluates identity, device posture, location, MFA. The IAP then forwards to a policy engine (OPA, Cedar) which returns an allow/deny per-request. The downstream service still authenticates the caller (mTLS + SPIFFE ID) and re-authorises against policy. Inside the cluster: mTLS via SPIFFE identity (every workload has an X.509 cert identifying its service account), AuthorizationPolicy per workload restricting which other workloads can call which endpoints. A breach in one service gives you nothing because the next call still has to prove identity and pass policy.

## [081] SECURITY · ZERO-TRUST · Implementing zero-trust (sldId 336)

- Edge (IAP): Pomerium or OAuth2 Proxy in front of an OIDC provider such as Keycloak — they terminate TLS, validate identity (OAuth/OIDC against your IdP), apply the route's access policy, then issue a JWT the downstream service sees in X-Forwarded-* headers.
- Inside the cluster (mTLS): Istio + SPIFFE assigns every workload an X.509 cert identifying its service account (spiffe://cluster.local/ns/orders/sa/order-service). Every service-to-service call is mutually authenticated automatically.
- Authorization: Istio AuthorizationPolicy declares 'order-service can call payment-service /charge but nothing else, only when carrying a valid customer JWT.' Per-workload, fine-grained, declarative.
- Policy decisions: OPA / Cedar evaluate context (user, time, device, target, action) and return allow/deny. Out-of-process so policy can change without redeploying every service.
- App-side discipline: read the validated peer identity from X-Forwarded-Client-Cert; never accept calls that arrive without it; log every authorization decision.
  - License notes: Istio, SPIFFE/SPIRE, OPA, Cedar — all open source (Apache 2.0 or similar). Pomerium (Apache 2.0) and OAuth2 Proxy (MIT) are open source too.

p. 68

> Concrete implementations to ground the model. The edge IAP is what your users hit — they authenticate against your IdP (Keycloak, or Dex federating an existing directory), the IAP issues a session, every request from then on carries identity. Inside the cluster, SPIFFE is the service-identity mechanism that makes mTLS work without manual cert management — it's what gives every Pod a verifiable identity. Istio's AuthorizationPolicy is the declarative layer on top: 'who can call what.' OPA / Cedar is the more flexible policy engine when your decision logic is complex (per-tenant, per-time-of-day, per-data-classification). The bold line is the app-side discipline: don't make these external policies redundant by accepting unauthenticated calls in your code; use the peer identity from the headers as a required input.

## [082] SECURITY · POLICY-AS-CODE · Policy-as-Code — security gates in Git (sldId 337)

OPA Gatekeeper / Kyverno enforce declarative policies at admission. CI runs the same policies pre-merge.

p. 69

> Security policies as code: declarative, version-controlled, tested, applied automatically. The flow on the diagram: a developer commits manifests; CI runs conftest or Kyverno against the manifests pre-merge (catches violations before they reach the cluster); on `kubectl apply` (or ArgoCD / Flux), the Kubernetes API server calls the admission controller (OPA Gatekeeper / Kyverno) which evaluates the ConstraintTemplate / ClusterPolicy against the incoming object. Non-conformant resources are rejected — they never become running Pods. The policy file lives in Git, reviewed like code, applied by the cluster. No human runs a checklist; consistency is enforced uniformly. Example policies: images must come from approved registries, no privileged containers, no host network, no host path mounts, all containers have resource limits, all images are signed.

## [083] SECURITY · POLICY-AS-CODE · OPA Gatekeeper ConstraintTemplate (Rego) (sldId 338)

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

p. 70

> The two-piece pattern: ConstraintTemplate defines the logic (in Rego, OPA's policy language), Constraint is the instance that applies the logic to specific resources with specific parameters. The Rego in violation[{msg}] reads as 'for every container in the Pod, if its image doesn't start with any of the allowed registries, emit a violation with this message.' Gatekeeper translates that into an admission webhook that rejects non-conformant Pods before they're scheduled. The Constraint binds the template to the kinds (Pods) and namespaces (everything except system namespaces), with the allowedRegistries list as the parameter. Lives in Git, applied via `kubectl apply` (or ArgoCD), versioned and reviewed like code. An equivalent Kyverno expression is more YAML-native if your team prefers it; Rego is more expressive for complex logic.

## [084] SECURITY · BULKHEAD · Bulkhead — isolate resources, bound the blast radius (sldId 339)

Per-tenant / per-call / per-priority pools. One tenant's storm cannot starve others. One compromise cannot cascade.

p. 71

> Bulkhead: borrowed from naval architecture, where watertight compartments stop one breach from sinking the ship. In software, you isolate resources (connection pools, thread pools, async semaphores, queues) by tenant, by call type, or by priority. The left side of the diagram (red) shows the default: one shared pool means a single tenant's traffic storm starves everyone else's. The right side: separate pools, each with its own bounded size. A storm from tenant A consumes tenant A's pool and rejects further A requests — tenants B and background workloads keep running. Why this matters for security as well as resilience: a compromised tenant or a compromised endpoint can be used to mount a denial-of-service against the shared system; bulkheads cap that to its own pool. Implementations: Resilience4j Bulkhead (JVM), Polly (.NET), asyncio.Semaphore (Python), Istio per-destination connection pools at the mesh layer.

## [085] SECURITY · BULKHEAD · SmallRye Fault Tolerance bulkheads (sldId 340)

[chip] java · Quarkus + SmallRye Fault Tolerance (MicroProfile)

```java
// examples/12-security/quarkus/order-service (condensed excerpts)
// BulkheadService.java: one SmallRye guard per tenant: 5 concurrent, no queue
private static Pool newPool() {
    var inFlight = new AtomicInteger();
    var guard = Guard.create()
            .withBulkhead().limit(CAPACITY)
                .onAccepted(inFlight::incrementAndGet)   // feeds /bulkhead-state
                .onFinished(inFlight::decrementAndGet)
                .done()
            .build();
    return new Pool(guard, inFlight);
}
public <T> T run(String tenant, Supplier<T> work, Class<T> type) {
    return pools.computeIfAbsent(tenant, t -> newPool()).guard().get(work, type);
}
// OrderResource.java, POST /orders: A's storm can't drain B's capacity
try {
    return bulkhead.run(body.tenant(),
            () -> placeOrder(body, identity, subject), Response.class);
} catch (BulkheadException e) {
    return Response.status(429).entity(Map.of("detail", "tenant bulkhead full")).build();
}
```

p. 72

> Quarkus ships SmallRye Fault Tolerance, the MicroProfile implementation. Its @Bulkhead annotation caps one method, but example 12 needs one limit per tenant, so it uses the library's programmatic API: a Guard per tenant, created on first use, with a bulkhead of five concurrent calls and no queue.
>
> A tenant that fills its five slots gets BulkheadException and a 429 at once, while every other tenant keeps its own five. The guard's onAccepted and onFinished hooks keep the in-flight count that the bulkhead-state endpoint reports. At the platform layer, Istio's per-destination connection-pool limits complement these in-process limits.

## [086] SECURITY · CLAIM-CHECK · Claim-check — send a reference, not the payload (sldId 341)

Large or sensitive payload goes to a secure store; the message bus carries only an opaque token to fetch it.

p. 73

> The claim-check pattern: a producer puts the (large or sensitive) payload into a secure object store and publishes only a claim ticket (an opaque token plus a fetch URI) to the message bus. The consumer receives the ticket, fetches the payload from the store with the token. Two big security wins: PII never sits in Kafka's topic history (which is replicated, retained, and possibly visible to operators and other tools); and the token can expire and be revoked, while a Kafka message cannot. The pattern also has performance benefits (you don't push 50MB messages through the message bus), but this section frames it for security. Compare to the write-around caching pattern: same shape, different motivation. Where: any flow where sensitive payloads (health records, financial documents, customer PII) cross messaging infrastructure that shouldn't see them; any flow where payloads are large enough that the bus would be the bottleneck.

## [087] SECURITY · CLAIM-CHECK · Producer mints claim, consumer fetches payload (sldId 342)

[chip] java · Quarkus + SmallRye Reactive Messaging

```java
// claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key
@ApplicationScoped
public class ClaimPublisher {
    @Inject ObjectStore store;                                 // any encrypted object store
    @Inject ValetKeyService valet;                             // examples/12-security
    @Inject @Channel("documents-out") Emitter<JsonObject> claims;   // topic order.documents
    public void publish(String orderId, byte[] body) {
        String key = "payloads/" + orderId;
        store.put(key, body, true);                            // encrypted at rest, ACL'd
        JsonObject claim = new JsonObject(valet.mint(key, "GET"))
            .put("order_id", orderId)
            .put("uri", "https://objects.internal/" + key);
        claims.send(claim);                                    // only the claim on the topic
    }
}
@ApplicationScoped
public class ClaimConsumer {
    @Inject ObjectStore store;
    @Incoming("documents-in")                                  // topic order.documents
    public void onClaim(JsonObject claim) {
        byte[] body = store.get(claim.getString("uri"), claim.getString("token"));
        handle(body);                                          // PII never touched the topic
    }
}
```

p. 74

> Two halves. The producer writes the payload to an encrypted object store under payloads/<order id>, mints a GET-only ticket for that key with Example 12's ValetKeyService.mint (300 seconds), and publishes only a small claim (order id, URI and the ticket) to order.documents with a Reactive Messaging Emitter. The PII is never on Kafka's wire.
>
> The consumer decodes the claim, fetches the payload with the token, processes it, then commits the offset (at-least-once delivery, so the handler must be idempotent). The store verifies the ticket before it serves the object and logs every fetch with the principal, an audit trail plain Kafka does not give.
>
> Size the ticket's lifetime to the consumer's worst-case lag. No runnable example covers claim-check; store stands for any encrypted object store. Set a lifecycle rule that expires claims after the retention period, so a replayed message points at nothing.

## [088] SECURITY · Choosing the right pattern (sldId 343)

- Sidecar — when you want one security policy uniformly across every workload, regardless of language. Cost: an extra container per Pod (memory + startup time).
- Valet Key — when clients need direct access to a large or specific resource (file upload, image download). Cost: storage system must validate tokens (most do).
- Strangler Fig (auth) — when you have legacy authentication you can't change all at once. Cost: a gateway running translation logic during the transition.
- Zero-Trust / IAP — the default model for any system with users outside your immediate control. Cost: mTLS everywhere has real CPU and operational overhead.
- Policy-as-Code — always. Always. The cost of not having it (drift, inconsistency, forgotten review steps) is much higher than the cost of adopting OPA / Kyverno.
- Bulkhead — any multi-tenant system, any system with mixed-priority workloads. Cost: pools are extra moving parts to size and tune.
- Claim-Check — when payloads carry PII or are large enough to bloat the message bus. Cost: an extra fetch hop and the store-and-bus must agree on token semantics.
- Most production systems combine all of these, not as a checklist but as a decision per concern.

p. 75

> Close the section with the decision rules. The cost lines are there because every pattern is a trade. Sidecar costs a container per Pod (a few MB of memory, a couple hundred ms of startup); for most systems the security uniformity makes it worth that. Valet key requires storage-side validation: the store, or a small gateway in front of it, must check the signature, the operation and the expiry. Strangler fig (auth) is a deliberate transition strategy; the gateway running translation is the cost. Zero-trust / mTLS everywhere has real CPU overhead (TLS handshakes are not free) — mesh implementations like Istio amortise it well but it's not zero. Policy-as-code's cost is the upfront investment in writing policies; the ongoing cost is near zero. Bulkheads are extra moving parts to tune. Claim-check adds a hop. The bold line is the take-home: production systems combine all seven, chosen per concern, not applied as a one-size-fits-all checklist.

## [089] SECURITY · Take-aways and references (sldId 344)

- Defence in depth across the 4 C's: cloud, cluster, container, code. A control at the wrong layer is false confidence.
- Identity is the new perimeter. mTLS + SPIFFE inside; IAP / OIDC at the edge. Every request authenticated and authorised, on every hop.
- Policy in Git, enforced by the cluster. OPA Gatekeeper or Kyverno at admission; conftest in CI for early feedback.
- PII never crosses your message bus in cleartext. Claim-check or end-to-end encrypt.
- Isolate by tenant, by call, by priority. Bulkheads bound the blast radius of both incidents and outages.
  - References: NIST SP 800-204A (microservices security); CNCF Cloud Native Security Whitepaper; OWASP API Security Top 10; the OpenSSF SLSA framework; Istio AuthorizationPolicy docs; OPA Gatekeeper library; OWASP Microservices Security Cheat Sheet.
  - Open-source pillars: Istio (Apache 2.0), SPIFFE/SPIRE (Apache 2.0), OPA / Gatekeeper (Apache 2.0), Kyverno (Apache 2.0), Sigstore (Apache 2.0), Falco (Apache 2.0), Trivy (Apache 2.0).

p. 76

> Close with the take-aways the audience should remember. Defence in depth across the 4 C's is the philosophical anchor. Identity-as-perimeter is the operational anchor. Policy-in-Git is the automation anchor. The PII-never-in-cleartext and bulkhead lines are the specific applications. The reference list is what you'd recommend for further reading — NIST 800-204A is the canonical microservices security paper; CNCF's Cloud Native Security Whitepaper organises the same material; OWASP API Top 10 is the application-layer reference; SLSA covers supply-chain security (signing, provenance, build integrity). The open-source list emphasises that the entire security stack is buildable with Apache 2.0 components.

## [090] Anti-Patterns (sldId 345)

13

Most outages re-couple what you separated.

> The final main section, and the most memorable framing of the whole talk: nearly every cloud-native failure is coupling sneaking back in. You did the work to separate things; entropy and deadlines pull them back together. This section names the specific ways that happens and gives heuristics to catch it early.

## [091] ANTI-PATTERNS · How cloud-native API systems go wrong (sldId 346)

Each anti-pattern reintroduces the coupling the architecture worked to remove.

p. 77

> Walk the grid briefly — most of these are callbacks to earlier sections. Distributed monolith (services that must deploy together), shared database (two services on one table), chatty calls (deep synchronous chains), no contract/leaky internal models (DB rows as the public API), missing observability (debugging by guesswork), retry storms (no backoff). The unifying diagnosis is on screen: each one reintroduces the coupling the architecture worked to remove. If you only remember one slide for code review, it's this one. The anti-pattern heuristics turn these into positive rules.

## [092] ANTI-PATTERNS · The heuristics that keep you out of them (sldId 347)

- If two services must deploy together, they are one service — merge them or fix the contract.
- One writer per dataset; everyone else reads through the API or subscribes to its events.
- Push aggregation to a gateway/BFF; forbid service-to-service call chains deeper than one hop.
- No contract in the registry, no merge — and every retry has a timeout and a bound.
- If you can't trace it, you can't run it: observability is a launch requirement, not a follow-up.

p. 78

> These are the five tests to apply in design and code review. (1) If two services must deploy together, they are one service: merge them or fix the contract. (2) One writer per dataset; everyone else reads through the API or subscribes to events — no shared tables. (3) Push aggregation to a gateway or BFF and forbid synchronous call chains deeper than one hop. (4) No contract in the registry, no merge — and every retry has a timeout and a bound. (5) If you can't trace it, you can't run it — observability is a launch requirement, not a follow-up. Offer these as a checklist the team can literally paste into a PR template.

## [093] IN CLOSING · The whole talk, in five lines (sldId 348)

- Cloud-native is a set of properties; the platform exists to make them the default.
- Match each interaction to its style (REST, gRPC, GraphQL or async) and compose at the edge.
- Own your data; share it as contracts and facts, never as shared tables.
- Make the contract a governed artifact: registry to enforce it, metadata to find it, observability to run it.
- Every anti-pattern is coupling sneaking back in. Design to keep things apart.

p. 79

> The recap — read these five as the entire talk compressed. If the audience remembers nothing else: cloud-native is properties not tools; match the protocol to the interaction and compose at the edge; own your data and share it as contracts and facts; make the contract a governed artifact (registry, metadata, observability); and watch for coupling sneaking back in. Pause here before References and Q&A. If it's the long-form session, this is the natural point to say 'and now the appendices go deeper on four things people always ask about' and continue.

## [094] REFERENCES · The shoulders this stands on (sldId 349)

- Building Microservices, 2nd ed. — Sam Newman (O'Reilly)
- Designing Data-Intensive Applications, 2nd ed. — Martin Kleppmann & Chris Riccomini (O'Reilly)
- Building Event-Driven Microservices, 2nd ed. — Adam Bellemare (O'Reilly)
- Cloud Native Patterns — Cornelia Davis (Manning)
- Patterns of Distributed Systems — Unmesh Joshi (Addison-Wesley)
- Architecture Modernization — Nick Tune & Jean-Georges Perrin (Manning)
- Cloud Native Anti-Patterns — Gerald Bachlmayr et al. (Packt)
- Principles of Web API Design — James Higginbotham (Addison-Wesley)
- Patterns for API Design — Olaf Zimmermann et al. (Addison-Wesley)
- API Design Patterns — JJ Geewax (Manning)
- Learning Domain-Driven Design — Vlad Khononov (O'Reilly)
- Balancing Coupling in Software Design — Vlad Khononov (Addison-Wesley)
- Quarkus guides (quarkus.io/guides), Quarkus Flow & Debezium docs — for the runtime specifics
- The full list, with publisher links: patterncatalyst.github.io/cloud-native-design-patterns/bibliography/

p. 80

> The reading list this talk stands on. Call out a couple of pairings: Newman's Building Microservices for the boundaries and integration story; Kleppmann's Designing Data-Intensive Applications for the data and consistency foundations behind the outbox and saga; Bellemare for the event-driven backbone; and the API-design trio (Higginbotham, Zimmermann et al., Geewax) for contract and versioning depth. The architecture books are language-agnostic — they apply whether you build on Quarkus, Spring or anything else. The Quarkus guides plus the Quarkus Flow and Debezium docs are the practical references for the runtime specifics shown in the code. The slides and these references are enough to build the system, not only to discuss it. The full list, with a publisher link for every title, is on the site's Bibliography page (patterncatalyst.github.io/cloud-native-design-patterns/bibliography/).

## [095] Thank you (sldId 350)

Questions?

> End of the main talk. Thank the audience and open for questions. The appendices are deep-dive backup material: pull them up on demand during Q&A, or work through them if you're running the full-length session. They cover the questions that always come up: how the three protocols differ, how to version each one, how to run WebSockets on Kubernetes, and the hard parts of saga state and compensation.

## [096] REFERENCE · Glossary of acronyms (1 of 2) — protocols, data, events (sldId 351)

- Protocols & APIs — REST (Representational State Transfer); RPC (Remote Procedure Call); gRPC (Google's RPC framework, over HTTP/2 + Protobuf); HTTP (HyperText Transfer Protocol); TLS / mTLS (Transport Layer Security / mutual TLS, where both peers present certificates); SSE (Server-Sent Events); BFF (Backend-For-Frontend); SDK (Software Development Kit); API (Application Programming Interface).
- Messaging & integration — AMQP (Advanced Message Queuing Protocol); ESB (Enterprise Service Bus); DLQ (Dead-Letter Queue, where un-processable messages go); SerDe (Serializer / Deserializer); pub/sub (publish-subscribe).
- Data & persistence — CQRS (Command Query Responsibility Segregation); CDC (Change Data Capture); WAL (Write-Ahead Log: the DB's commit-ordered durable log); ACID (Atomicity, Consistency, Isolation, Durability); TTL (Time-To-Live: how long a cached key lives before expiring); LRU (Least Recently Used: a cache eviction policy); SETEX (the Redis "SET with EXpiry" command: sets a key and its TTL atomically); ORM (Object-Relational Mapping); JPA (Jakarta Persistence API); Panache (Quarkus's ORM-simplification layer over Hibernate, not an acronym).
- Domain modelling & flow — DDD (Domain-Driven Design); OHS (Open Host Service: a published, stable interface a context offers others); ACL (Anti-Corruption Layer in DDD, which translates between models; ACL also means Access Control List in security); Saga (not an acronym: a sequence of local transactions with compensating actions).

p. 81

> Glossary part 1, the protocol/data/event vocabulary. Call out the ones most likely to trip people up: gRPC is recursively 'gRPC Remote Procedure Call' but practically it's Google's high-performance RPC over HTTP/2 with Protocol Buffers. mTLS (mutual TLS) is the one people often gloss — ordinary TLS authenticates the server to the client; mutual TLS also authenticates the client to the server, which is the basis of zero-trust service identity. The data row has the SETEX and TTL the audience asked about explicitly: TTL is the expiry duration on a cached key; SETEX is the Redis command that sets a value and its TTL in one atomic operation (SETEX key seconds value). LRU is the eviction policy that drops the least-recently-touched key when the cache is full. CDC and WAL go together — CDC tails the WAL. Call out the ACL ambiguity: in the DDD/data sections ACL means Anti-Corruption Layer; in the security section it means Access Control List.

## [097] REFERENCE · Glossary of acronyms (2 of 2) — platform, security, telemetry (sldId 352)

- Kubernetes & cloud — K8s (Kubernetes); RBAC (Role-Based Access Control); HPA (Horizontal Pod Autoscaler); KEDA (Kubernetes Event-Driven Autoscaling); PSS (Pod Security Standards); CRD (Custom Resource Definition); IAM (Identity & Access Management); KMS (Key Management Service); VPC (Virtual Private Cloud); CNI (Container Network Interface).
- Identity & security — SPIFFE (Secure Production Identity Framework For Everyone); SPIRE (the SPIFFE Runtime Environment); OPA (Open Policy Agent); IAP (Identity-Aware Proxy); JWT (JSON Web Token); OIDC (OpenID Connect); OAuth (Open Authorization); MFA (Multi-Factor Authentication); PII (Personally Identifiable Information); SLSA (Supply-chain Levels for Software Artifacts); CVE (Common Vulnerabilities & Exposures); SBOM (Software Bill of Materials).
- Observability — OTel (OpenTelemetry); RED (Rate, Errors, Duration: the request-driven metrics method); USE (Utilisation, Saturation, Errors: the resource metrics method); MDC (Mapped Diagnostic Context, per-thread log context); LGTM (Loki, Grafana, Tempo, Mimir); SLO / SLI / SLA (Service-Level Objective / Indicator / Agreement); p99 (99th-percentile latency).
- Runtime & build — JVM (Java Virtual Machine); JIT (Just-In-Time compilation); AOT (Ahead-Of-Time compilation, as in a GraalVM or Mandrel native image); GC (Garbage Collection); CDI (Contexts & Dependency Injection); DI (Dependency Injection); DTO (Data Transfer Object); POJO (Plain Old Java Object).

p. 82

> Glossary part 2, the platform/security/observability vocabulary. The Kubernetes row: HPA scales on CPU/memory, KEDA scales on event sources (queue depth, Kafka lag, HTTP rate) — the distinction matters in the autoscaling discussion. PSS (Pod Security Standards) replaced the deprecated PodSecurityPolicy. The security row has the terms from section 12: SPIFFE/SPIRE give workloads cryptographic identities for mTLS; OPA is the policy engine behind policy-as-code; IAP is the zero-trust edge proxy; JWT/OIDC/OAuth are the token/identity standards; SLSA/CVE/SBOM are supply-chain security. The observability row has RED and USE, the two metrics methods worth memorising: RED (Rate, Errors, Duration) for services, USE (Utilisation, Saturation, Errors) for resources. p99 means the 99th-percentile latency — 99% of requests are faster than this; it's what you alert on, not the average. The runtime row is tailored to this deck's language.

## [098] Appendix A · Protocols in Depth (sldId 353)

A

REST, gRPC and GraphQL: how they differ.

> Appendix A. This is the deep dive behind the 'pick the protocol' slide from section 2. We compare the three on three axes: the mental model each imposes, how they handle fetching and round trips, and what travels on the wire. By the end the audience should be able to defend a protocol choice on technical grounds, not fashion.

## [099] APPENDIX A · PROTOCOLS · Three paradigms and their mental models (sldId 354)

REST models resources, gRPC models procedures, GraphQL models a typed graph — the same intent, three shapes.

p. 83

> Start with the mental model, because it drives everything else. REST is resource-oriented: nouns and HTTP verbs, you transfer representations of state. gRPC is procedure-oriented: you call typed methods, it's behaviour not state, and the .proto is the contract. GraphQL is graph-oriented: one typed schema the client traverses, picking exactly the fields it wants. The same place_order intent takes three different shapes. Most arguments about 'which is best' are arguments about which mental model fits the problem, and the answer often differs per interaction.

## [100] APPENDIX A · PROTOCOLS · Over-fetching, under-fetching and round trips (sldId 355)

REST trades round trips or bespoke endpoints for simplicity; GraphQL shapes one response; gRPC is a typed call.

p. 84

> This is the practical difference clients feel. With REST you often need several round trips (order, then its items, then stock, then shipping) or you build a bespoke aggregate endpoint — and you still get fixed payload shapes that over- or under-fetch. GraphQL collapses that into one tailored query where the client names the fields, so no over- or under-fetching and the client controls the cost. gRPC is a single typed, binary call with a fixed reply shape: no field selection, but the fastest of the three. The trade: GraphQL gives clients flexibility at the cost of gateway complexity; gRPC gives speed at the cost of rigidity; REST gives reach and simplicity at the cost of round trips.

## [101] APPENDIX A · PROTOCOLS · The wire: transport, encoding and streaming (sldId 356)

Reach and caching, or raw speed, or client-shaped responses — choose on the wire properties you need.

p. 85

> What travels on the wire, and why it constrains your choice. REST: HTTP/1.1 or /2, JSON text, request/response, cacheable via standard HTTP, browser-native — maximum reach. gRPC: HTTP/2 only, protobuf binary, full uni- and bidirectional streaming, no HTTP caching, and it needs grpc-web to work from a browser. GraphQL: HTTP POST to a single URL, JSON, request/response plus subscriptions, caching is application-level (not HTTP), browser-native. The decision rule: if you need broad reach and HTTP caching, REST; if you need raw speed and streaming between services you control, gRPC; if you need client-shaped responses over many sources, GraphQL.

## [102] APPENDIX A · PROTOCOLS · Choosing between them in practice (sldId 357)

- Public or partner-facing, browser or third-party clients, caching matters → REST.
- Internal service-to-service, low latency, high call volume, streaming → gRPC.
- Aggregating many back-ends for varied clients that each want different fields → GraphQL at the gateway.
- A fact that many consumers react to, decoupled in time → none of these; emit an event.
- Real systems use all four; standardizing on one wire for everything is itself an anti-pattern.

p. 86

> The decision guide. Public/partner/browser with caching → REST. Internal, hot, streaming → gRPC. Client-driven aggregation across back-ends → GraphQL at the gateway. A fact many consumers react to → don't make it a call at all, emit an event. The bold closing point ties back to the whole talk: forcing one protocol everywhere ('we're a gRPC shop', 'everything is GraphQL') is itself an anti-pattern, because you pay gRPC's browser tax or GraphQL's gateway complexity where a plain cacheable GET would have done.

## [103] APPENDIX A · PROTOCOLS · Common mistakes with each (sldId 358)

- REST: verbs in URLs (/createOrder), 200-for-everything, offset pagination, and ignoring cache headers.
- gRPC: exposing it directly to browsers without grpc-web; treating it as REST-with-protobuf and ignoring streaming.
- GraphQL: the N+1 resolver explosion; no query depth/complexity limits; using it for simple single-resource reads.
- All three: leaking internal database models straight onto the wire, so you can never evolve them.
- Async: using a queue when you needed a log (no replay), or a request when you needed a fact.

p. 87

> The failure modes, drawn from real review comments. REST: verbs in URLs, returning 200 with an error body, offset pagination that breaks under load, and throwing away free HTTP caching. gRPC: trying to call it straight from a browser without grpc-web, or using it as 'REST with protobuf' and never touching its streaming superpower. GraphQL: the classic N+1 resolver explosion (fix with DataLoader batching), no depth or complexity limits so a malicious query melts the gateway, and reaching for it when a plain GET would do. The universal one is the last bold-adjacent: leaking your database schema onto the wire kills your ability to evolve — the same leaky-internal-models anti-pattern from section 12.

## [104] Appendix B · Versioning & Evolution (sldId 359)

B

REST vs RESTful, proto breaking changes, GraphQL evolution.

> Appendix B answers the question every team fights about: how do we version this without breaking everyone? The answer differs sharply by protocol. REST has several strategies with real trade-offs; gRPC has precise wire-compatibility rules; GraphQL rejects versioning entirely in favour of evolution. We'll see each, with code.

## [105] APPENDIX B · VERSIONING · Four ways to version a REST API (sldId 360)

URI versioning is common and visible; media-type versioning keeps URLs stable — the more RESTful choice.

p. 88

> REST has four strategies, ordered from coarse to fine. URI path (/v2/orders): visible, trivial to route, but couples the version to the URL and breaks REST's idea that a URL identifies a resource, not a representation. Query param: simple to default but muddies caches. Custom header: keeps URLs clean but is invisible and often forgotten. Media-type versioning (Accept: application/vnd.acme.order.v2+json): content negotiation keeps the URL stable as the identifier of the resource, and the representation is what's versioned. This is the RESTful approach. In practice, URI versioning is the most common because it's pragmatic; media-type is the most correct. Know which you're choosing and why. The media-type versioning code shows how.

## [106] APPENDIX B · VERSIONING · Media-type versioning with Quarkus REST (sldId 361)

[chip] java · Quarkus REST

```java
@Path("/orders")
public class OrderResource {
    static final String V1 = "application/vnd.acme.order+json";      // legacy
    static final String V2 = "application/vnd.acme.order.v2+json";   // adds currency
    @GET @Path("/{id}") @Produces(V2)        // one stable URL — the resource
    public Uni<OrderV2> getV2(String id) {   // chosen by Accept: …v2+json
        return orders.get(id).map(OrderV2::from);
    }
    @GET @Path("/{id}") @Produces(V1)        // same path, different representation
    public Uni<OrderV1> getV1(String id) {   // default for old clients
        return orders.get(id).map(OrderV1::from);
    }
}
// JAX-RS content negotiation routes on Accept; the URL never changes.
```

The resource URL is stable; the representation is negotiated. New clients ask for v2; old clients keep getting v1.

p. 89

> This makes 'RESTful versioning' concrete in Quarkus. There's one URL for the order resource — it never changes. Two methods share the path but declare different @Produces media types; JAX-RS content negotiation picks the method matching the client's Accept header and sets the Content-Type. New clients ask for the v2 media type and get the currency field; old clients send the default and get v1, completely unaffected. Contrast with /v2/orders, where you've now got two URLs for the same underlying thing. The OrderV1/OrderV2 records are explicit representation DTOs — exactly the pattern that keeps your wire contract decoupled from your entity.

## [107] APPENDIX B · VERSIONING · gRPC / protobuf: what is a breaking change (sldId 362)

Field numbers are the contract — names and order are not. Never reuse or renumber a field.

p. 90

> gRPC's rules are precise because the wire format is positional. Safe, wire-compatible changes: add a field with a new number, add an rpc method, add an enum value, rename a field (the number is what matters, not the name), mark fields deprecated, and reserve removed tags. Breaking changes: change a field's number or type, reuse a removed number, remove a field without reserving its tag, rename or move a service or package, or change the request/response message type. The one people miss is on screen at the bottom: changing a method between unary and any streaming mode changes the HTTP/2 framing and is always breaking. The discipline: field numbers are forever; never reuse or renumber. Code shows safe evolution next.

## [108] APPENDIX B · VERSIONING · Evolving a .proto safely (sldId 363)

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

p. 91

> Walk the safe pattern. We removed an old 'notes' field, so we reserve both its tag number (4) and its name permanently: nobody can reuse them and silently corrupt old data on the wire. We add currency and state as brand-new fields with new tag numbers; old clients ignore unknown fields and new clients read them, which gives forward and backward compatibility without extra work. Note the enum must keep a zero value as its default. The comment at the bottom lists the things that would break the wire: widening qty's type, moving an existing field to a new tag, or reusing a reserved tag. Apicurio's compatibility check (section 9) enforces exactly these rules in CI.

## [109] APPENDIX B · VERSIONING · GraphQL versions by evolution, not by number (sldId 364)

There is no /v2 in GraphQL: add fields, mark old ones @deprecated, watch usage, then retire.

p. 92

> GraphQL takes a completely different stance: there are no versions. There's one schema that evolves continuously. The lifecycle on screen: add new fields and types (additive is always safe, because existing queries did not ask for the new field); mark superseded fields @deprecated with a reason and a pointer to the replacement, while still serving them; watch field-level usage metrics to see who still queries the old field and drive their migration; and retire, the single breaking step, only once usage hits zero. The insight: GraphQL pushes you toward data-driven deprecation instead of big-bang version cutovers. Code shows the @deprecated directive next.

## [110] APPENDIX B · VERSIONING · Deprecating a field in SmallRye GraphQL (sldId 365)

[chip] java · SmallRye GraphQL

```java
public record Order(
    String id,
    @Deprecated(since = "2026-05")                 // shows in the schema + UI
    @Description("Use totalMinor (integer cents) instead.")
    double total,                                  // still served
    int totalMinor                                 // replacement, added additively
) {}
// @Deprecated surfaces in introspection and GraphiQL with the reason.
// Field-level usage metrics tell you when 'total' has zero callers —
// only then do you remove it. No /v2 endpoint ever exists.
```

Additive change plus @Deprecated plus usage metrics replaces versioning entirely.

p. 93

> The mechanics in SmallRye GraphQL. We add totalMinor additively and mark the old total field with Java's @Deprecated plus a @Description carrying the reason; SmallRye maps these onto GraphQL's @deprecated schema directive. The field keeps working and nothing breaks, but the deprecation shows up in introspection and in GraphiQL, nudging client developers. The crucial operational piece is the comment: you instrument field-level usage, and you only remove total when its usage drops to zero. That's the whole GraphQL philosophy — evolution governed by data, with the breaking removal deferred until provably safe. Each protocol answers the same problem differently.

## [111] APPENDIX B · VERSIONING · Principles that cut across all three (sldId 366)

- Additive change is always safe; removal and mutation are where you break people.
- Make compatibility mechanical — the registry's BACKWARD/FORWARD/FULL rules, checked in CI, not by reviewers' memory.
- Never break silently: deprecate with a reason, a replacement and a sunset date; measure who's still on the old version.
- Run old and new in parallel and migrate consumers before retiring — retirement is the only step that can break.
- Version data the same way you version APIs: event schemas in the registry follow the identical rules.

p. 94

> Step back to the universal principles, because the protocol-specific rules all rhyme. Additive change is safe; removal and mutation break people — so design to add. Make compatibility mechanical: the registry's rules checked in CI, never a reviewer remembering. Never break silently: deprecate with a reason, a replacement, a sunset date, and measure who's still on the old thing. Run old and new in parallel and migrate before you retire, because retirement is the only inherently breaking move. And the bold line that connects this back to the event-driven section: your event schemas version by exactly the same rules — the registry treats an Avro schema and an OpenAPI spec identically. Versioning data and versioning APIs are the same discipline.

## [112] Appendix C · WebSockets at Scale (sldId 367)

C

WebSockets Next, pod pinning, the backplane, binary framing, reconnection.

> Appendix C covers the protocol left out of the main interaction-styles discussion, because it behaves so differently on Kubernetes. WebSockets are long-lived, stateful and pinned to a pod — the opposite of the stateless request model the platform assumes. We'll build one with Quarkus WebSockets Next, see why it fights scaling, fix it with a backplane, make it fast and versioned with protobuf, and make it survivable with reconnection.

## [113] APPENDIX C · WEBSOCKETS · A WebSocket endpoint with WebSockets Next (sldId 368)

[chip] java · Quarkus WebSockets Next

```java
@WebSocket(path = "/ws/{userId}")            // quarkus-websockets-next
public class OrderSocket {
    @Inject WebSocketConnection connection;  // this pod owns this connection
    @Inject OpenConnections connections;     // per-pod registry — not shared!
    @OnOpen
    public void onOpen(@PathParam String userId) {
        connection.userData().put(KEY_USER, userId);
    }
    @OnTextMessage                           // full-duplex, long-lived
    public Uni<Void> onMessage(ClientMsg msg) {
        return handle(msg);
    }
    // @OnClose cleanup is automatic; OpenConnections tracks live sockets
}
```

Declarative, but OpenConnections is per-pod. That single fact is the entire scaling problem.

p. 95

> WebSockets Next makes the endpoint declarative: @WebSocket with a path, @OnOpen, @OnTextMessage (with automatic JSON binding to a record), and automatic @OnClose cleanup — far cleaner than the old Jakarta WebSocket API. But point hard at OpenConnections — the registry of who's connected lives in this pod's memory. That one design fact drives everything in this appendix: the connection and the knowledge of who's connected live on exactly one pod. Everything stateless about HTTP (any replica can serve any request) is now false. The scaling problem follows from that.

## [114] APPENDIX C · WEBSOCKETS · Why WebSockets fight Kubernetes scaling (sldId 369)

A long-lived connection pins to one pod; new pods get no existing connections and scale-down drops them.

p. 96

> Here's the collision with Kubernetes. A WebSocket connection, once established through the load balancer, is pinned to one pod for its entire lifetime. Two problems follow. Scale-up: the HPA or KEDA adds ws-pod-3, but it gets zero existing connections, only new ones, so a hot pod stays hot and the new pod sits idle; scaling doesn't relieve the load you already have. Scale-down and rollouts: terminating a pod severs every connection it was holding, so a routine deploy disconnects thousands of users at once. Stateless HTTP shrugs both off; WebSockets don't. The fix is to stop making any single pod the home of a conversation, which is the backplane, rather than to avoid scaling.

## [115] APPENDIX C · WEBSOCKETS · The scaling problem, stated precisely (sldId 370)

- Pinning: a connection is bound to one pod; the LB can't move it without dropping it.
- Uneven load: new replicas only receive new connections, so existing hotspots persist.
- Rollouts hurt: every deploy or scale-down severs the connections on the affected pods.
- Cross-pod delivery: to push to user X you must reach whichever pod holds X — which you don't track.
- Connection limits & memory: each socket is held-open state; pods cap out on file descriptors, not CPU.

p. 97

> Name the five distinct problems so the audience can recognize them. Pinning: the LB can't migrate a live socket. Uneven load: scaling adds capacity for new connections but doesn't rebalance existing ones. Rollouts hurt: every deploy is a mass disconnect event — you need graceful drain and client reconnection. Cross-pod delivery: to push a message to user X you must route to the specific pod holding X's socket, and nothing tracks that by default. And the resource shape is different (the bold point): you scale on open-connection count, file descriptors and memory, not CPU, so your KEDA/HPA trigger has to change too. The pub/sub backplane solves or eases every one of these.

## [116] APPENDIX C · WEBSOCKETS · Scaling out: a pub/sub backplane (sldId 371)

Each pod owns only its own sockets; a Redis or Kafka backplane fans a message out to whichever pod holds the client.

p. 98

> The pattern that makes WebSockets horizontally scalable. Each pod still owns only its own sockets, which is fine, but every pod subscribes and publishes to a shared backplane: Redis pub/sub for low latency, or a Kafka topic if you want durability and replay. When a publisher wants to push order.updated to user X, it publishes to the backplane without knowing which pod holds X; the backplane fans the message to all pods, and the one pod that holds X's socket delivers it. Now scale-up and zero-downtime rollouts work again, because no pod is the single home of a conversation — connections can land anywhere and still receive everything. Redis is the common default; Kafka if you already run it and want the durability.

## [117] APPENDIX C · WEBSOCKETS · Binary framing with protobuf — fast and versioned (sldId 372)

[chip] protobuf + java

```protobuf+java
// envelope.proto — version the message, not the URL
message Envelope {
  uint32 version = 1;        // bump for incompatible payload changes
  string type    = 2;        // "order.updated", "ping", ...
  bytes  payload = 3;        // the protobuf-encoded body for `type`
  uint64 seq     = 4;        // monotonic per-connection — drives resume
}
// server: send compact binary frames instead of JSON text
@OnBinaryMessage                                  // Envelope bound by a BinaryMessageCodec
public Uni<Void> onFrame(Envelope env) { return dispatch(env); }
Envelope frame = Envelope.newBuilder().setVersion(2)
    .setType("order.updated").setSeq(n)
    .setPayload(order.toByteString()).build();
connection.sendBinaryAndAwait(Buffer.buffer(frame.toByteArray()));
// client checks env.version; unknown major version -> reconnect & renegotiate
```

Protobuf frames are smaller and faster than JSON; the versioned envelope and seq number enable evolution and resume.

p. 99

> Two wins in one slide. Performance: protobuf binary frames via @OnBinaryMessage and connection.sendBinary are markedly smaller and cheaper to parse than JSON text — meaningful when pushing high-frequency updates to many sockets. With a BinaryMessageCodec registered for Envelope, WebSockets Next binds the incoming bytes to the generated type. Versioning: because WebSocket messages have no URL to hang a version on, you version the envelope. A version field lets the client detect an incompatible payload format and renegotiate; the type field dispatches to the right protobuf message; and a monotonic seq number per connection is what makes reconnection and replay possible, the subject of the failure-handling slide. So the envelope solves both 'make it fast' and 'how do I version a socket message' at once.

## [118] APPENDIX C · WEBSOCKETS · Failure handling: resume, don't restart (sldId 373)

Heartbeats detect dead links; the client reconnects with backoff and resumes from the last acknowledged sequence.

p. 100

> The cloud-native posture: treat every connection as disposable and design for its loss. Heartbeats (ping/pong) detect a dead link quickly — TCP alone can hang for minutes. When the connection drops, the client reconnects with exponential backoff plus jitter (so ten thousand clients don't reconnect in lockstep and hammer your pods after a rollout). On reconnect, the client sends its last-seen sequence number (last_seq = 1042); the server replays only the events the client missed (1043 onward), and because each frame carries a seq, the client can dedupe — so the whole thing is at-least-once and idempotent. The principle on screen: resume, don't restart. A reconnect should be invisible to the user, not a full state reload.

## [119] APPENDIX C · WEBSOCKETS · A cloud-native WebSocket checklist (sldId 374)

- Externalize fan-out to a backplane (Redis or Kafka); never assume one pod holds the client.
- Scale and trigger on connection count and memory, not CPU; set realistic per-pod connection caps.
- Drain gracefully on shutdown: stop accepting, signal clients to reconnect, let backoff spread the herd.
- Heartbeat to detect dead links (WebSockets Next auto-ping-interval); reconnect with exponential backoff + jitter; resume via a per-connection seq.
- Use binary frames with a versioned envelope; authenticate on connect and re-check on resume.

p. 101

> The operational checklist to leave on screen. Externalize fan-out to a backplane so no pod is special. Scale and set your KEDA/HPA trigger on connection count and memory, not CPU, and cap connections per pod realistically. Drain gracefully on shutdown — stop accepting, tell clients to reconnect, and let backoff-with-jitter spread the reconnect storm across your rollout. Heartbeat to detect dead links fast; reconnect with backoff and jitter; resume from a per-connection sequence number so the user never notices. And the security note in bold that teams forget: authenticate on connect and re-authenticate on resume, because a resume is a new TCP connection that could come from anywhere. Do these and WebSockets are just another well-behaved cloud-native workload.

## [120] Appendix D · Saga State & Compensation (sldId 375)

D

Persisting state, compensating cleanly, and the step-B-needs-A's-data problem.

> Appendix D is the deep mechanics behind the saga slide in the Data section. Three hard parts that the happy-path picture glosses over: where the orchestrator keeps its state so it survives a crash, how compensation works when a step fails midway, and a specific gnarly case people hit: when step B needs data that only step A produced, and how to resume after a crash between them.

## [121] APPENDIX D · SAGAS · Where a Quarkus saga keeps its state (sldId 376)

Memory won't survive a pod restart — persist every step transition in a DB, an event log, or a workflow engine.

p. 102

> First problem: the orchestrator must survive a crash mid-flow, so in-memory state is a non-starter — a pod restart would strand every in-flight saga with no idea what to compensate. Three real options. A DB-backed state machine: one row per saga instance holding its status and a context blob; you own the transitions — simplest, and great for most cases. Event-sourced: append each step as an event and rebuild state by replay — full audit history, fits naturally with the Kafka log. A workflow engine like Temporal or Camunda: durable execution with retries and timers built in — most power, least code, but a new dependency to run. The cross-cutting rule on screen: the state transition and the outbound command must commit together (the outbox pattern again), or you get lost or duplicated steps.

## [122] APPENDIX D · SAGAS · A persisted saga state machine (Panache) (sldId 377)

[chip] java · Hibernate Panache

```java
// SagaService.java (excerpt), examples/17-sagas/quarkus: one transaction per step
// STEPS = charge_payment, reserve_stock, book_shipping; each SagaStep also names its inverse
private Outcome advanceOneStep(String sagaId) {      // QuarkusTransaction.requiringNew()
    SagaEntity saga = SagaEntity.findById(sagaId, LockModeType.PESSIMISTIC_WRITE);  // row lock
    if (saga.stepIndex >= STEPS.size()) { saga.status = "COMPLETED"; return Outcome.DONE; }
    SagaStep step = STEPS.get(saga.stepIndex);
    Map<String, Object> context = new HashMap<>(saga.context);
    try {
        var result = stepExecutor.execute(step.name(), context);    // call the owning service
        SagaLogEntity.of(sagaId, step.name(), "execute", result).persist();
        context.put(step.name(), result);              // accumulate output into the context
        saga.context = context;
        saga.stepIndex++;                              // one commit: state + log row
        return Outcome.CONTINUE;
    } catch (Exception e) {
        SagaLogEntity.of(sagaId, step.name(), "failed", Map.of("error", e.getMessage()))
            .persist();
        saga.status = "COMPENSATING";                  // hand off to the unwinder
        return Outcome.COMPENSATE;
    }
}
```

One locked row per saga, advanced one durable step at a time. A crash just means 'load the row and call advance again.'

p. 103

> This is the DB-backed option made concrete with Panache, and the default choice when the team wants to own the transitions. Key ideas: one saga row, loaded with a PESSIMISTIC_WRITE lock (findById with a LockModeType) so two workers cannot advance the same saga concurrently. advanceOneStep runs in its own transaction, one step per transaction: the new context, the new step index and the saga_log row commit together, so a crash leaves either the old state or the new one. The context is a JSON column (@JdbcTypeCode(SqlTypes.JSON)) that accumulates each step's result, which the data-dependency slide builds on. A failed step logs the failure, marks the saga COMPENSATING and returns, and the caller runs the unwinder.
>
> Recovery needs no special path: on startup the service loads the RUNNING sagas and calls advance() again, and the loop resumes from the stored step index. The managed alternative is Quarkus Flow, which provides this state machine, retries and timers out of the box; the data-dependency slide shows it.

## [123] APPENDIX D · SAGAS · Compensating transactions unwind a failed saga (sldId 378)

Each committed step has an inverse; on failure they run in reverse order — there is no cross-service rollback.

p. 104

> Compensation is how a saga 'rolls back' when there's no actual rollback available across services. Each forward step that committed (payment.charge, inventory.reserve) has a defined semantic inverse: payment.refund, inventory.release. When book_shipping fails, you don't undo a database transaction (the payment has already happened at the provider); you run the compensations for the already-committed steps, in reverse order, newest first. Two things that bite people, both on screen: compensations must themselves be idempotent and durable, because a crash mid-unwind has to resume cleanly; and a compensation can itself fail, so it needs its own retries. The saga ends in a persisted COMPENSATED state with a full audit trail of what was done and undone.

## [124] APPENDIX D · SAGAS · Running compensations in reverse (sldId 379)

[chip] java · Hibernate Panache

```java
// SagaService.java (excerpt), examples/17-sagas/quarkus: compensate in reverse
public void compensate(String sagaId) {
    Saga saga = getSaga(sagaId);                   // stepIndex = completed steps
    for (int i = saga.stepIndex() - 1; i >= 0; i--) {         // newest first
        SagaStep step = STEPS.get(i);
        try {
            var result = stepExecutor.execute(step.compensate(), saga.context());
            logStep(sagaId, step.compensate(), "compensate", result);   // own transaction
        } catch (Exception e) {
            logStep(sagaId, step.compensate(), "failed", Map.of("error", e.getMessage()));
        }
    }
    QuarkusTransaction.requiringNew().run(() -> {
        SagaEntity entity = SagaEntity.findById(sagaId);
        entity.status = "COMPENSATED";             // Hibernate flushes the change at commit
    });
}
```

Compensate only completed steps, in reverse, and log every attempt; make each compensation idempotent so a retry never double-refunds.

p. 105

> The compensation logic. Each forward step names its inverse (SagaStep holds both), and the saga's step index says how many steps completed. We walk those steps in reverse, newest first, and run each compensation through the same step executor. Every attempt is written to saga_log in its own transaction, as compensate or failed, so a compensation that fails is recorded rather than skipped, and the saga ends COMPENSATED.
>
> In production you would also make each compensating call idempotent on the receiving service, for example with a key built from the saga id and the step, so a retry can never double-refund a customer, and track per-step compensation status so a crash halfway resumes from the right place. This is why compensations are designed up front, as part of each step, not bolted on after. If you use Quarkus Flow instead, you model these as the workflow's try/catch compensation tasks and the engine drives the unwind.

## [125] APPENDIX D · SAGAS · When step B needs data only step A produced (sldId 380)

Don't make B call A. Persist A's output into the saga context and pass it forward; on resume, read it back.

p. 106

> This case is a common source of bad designs. The orchestrator calls service A, then service B — but B needs a value that only A produced (say A returns a reservation_id and a warehouse region that B requires to proceed). The tempting wrong answer is to have B call A directly — now you've created a hidden synchronous dependency between B and A, exactly the chatty coupling the whole architecture fights. The right answer is on screen: the orchestrator owns a saga context (a 'blackboard'), persists A's output into it after step A, and passes the needed values into B's call. B never knows A exists. And note this is already in our state-machine code — that 's.context.put(step, result)' line is exactly this, and Quarkus Flow does it for you via the workflow data document.

## [126] APPENDIX D · SAGAS · Carrying context forward with Quarkus Flow (sldId 381)

[chip] java · Quarkus Flow

```java
import io.quarkiverse.flow.Flow;
import static io.serverlessworkflow.fluent.func.dsl.FuncDSL.*;
@ApplicationScoped
public class FulfillmentFlow extends Flow {     // CNCF Serverless Workflow
  @Override public Workflow descriptor() {
    return FuncWorkflowBuilder.workflow("fulfillment")
      // each task's output becomes the next task's input (the data document)
      .tasks(
        callFn("reserveStock", inventory::reserve),  // A -> {reservationId, region}
        callFn("bookShipping", shipping::book))      // B reads A's output as input
      .build();
  }
}
// The engine persists the data document + position after every task, so a
// crash between A and B resumes at B with A's result intact — A is never re-run.
```

Flow's data document carries A's output into B; durable state means a crash resumes at B with A's data intact.

p. 107

> This closes the loop and answers your question directly, using Quarkus Flow (the managed option from the state-options slide). In the CNCF Serverless Workflow model that Flow implements, each task's output becomes the next task's input: the workflow data document is the saga context, carried forward automatically. So bookShipping (B) receives reserveStock's (A's) output as its input; B never calls A, avoiding the hidden synchronous coupling. Quarkus Flow persists the data document and the current position after every task, so the crash scenario you raised resolves cleanly: the engine reloads the workflow, sees A is done and its result is in the data document, and resumes at B — A is never re-invoked, nothing is lost. The fluent task API here is illustrative; the point is the data-flow-plus-durable-state semantics. If you hand-roll it instead, that's the Panache 's.context.put(step, result)' line in the persisted-state code — same idea, you just own the plumbing.

## [127] Appendix E · API Error Handling (sldId 382)

E

One discipline, four wire formats.

> Appendix E. Error handling is where cloud-native systems fall apart, more often than the happy path. The thesis: agree one error contract (a stable machine code, a safe human message, a correlation id, a retryable flag, field details) and then map that same model onto REST, gRPC, Kafka and GraphQL. We finish on the failure mode that turns a blip into an outage, the retry storm, and the handful of controls that prevent it.

## [128] APPENDIX E · ERRORS · One error model, four wire formats (sldId 383)

The same five facts in every error; only the encoding changes per protocol.

p. 108

> Start with what every error must carry, regardless of protocol: a stable machine-readable code clients can branch on (not a localized string), a human-readable message safe to show, a correlation/trace id that ties the error to the distributed trace from section 11, a retryable flag (with retry-after when known), and structured field-level details. The four protocols just encode those same five facts differently — REST as problem+json, gRPC as status+details, Kafka via headers and a DLQ record, GraphQL as an errors[] entry with extensions. Agree this once as a shared contract; never leak stack traces or internal type names to callers.

## [129] APPENDIX E · ERRORS · REST: status, then Problem Details (sldId 384)

The status code is the category; the problem+json body carries the machine code and specifics.

p. 109

> REST has two layers. First the HTTP status class, which is the category and drives client behaviour: 4xx means the client must fix the request and should not blindly retry; 429 and 503 mean 'busy' and must be paired with a Retry-After header so clients back off; 5xx means a server fault that idempotent calls may retry with backoff. Second, the body: RFC 9457 Problem Details (application/problem+json, which superseded RFC 7807) gives a standard envelope (type, title, status, detail, instance), and you extend it with your stable code and the traceId. Status for the category, body for the specifics.

## [130] APPENDIX E · ERRORS · REST errors with Quarkus REST (sldId 385)

[chip] java · Quarkus REST

```java
public record Problem(String type, String title, int status,
                      String detail, String code, String traceId) {}
@ServerExceptionMapper                       // one place: domain -> wire
public RestResponse<Problem> mapStock(StockException e) {
    var body = new Problem(
        "https://errors.acme.io/stock", "Insufficient stock", 409,
        e.getMessage(),
        "STOCK_UNAVAILABLE",                  // stable machine code
        Span.current().getSpanContext().getTraceId());  // correlate
    return RestResponse.ResponseBuilder
        .create(Response.Status.CONFLICT, body)
        .type("application/problem+json")     // RFC 9457
        .build();
}
```

Map every domain error to problem+json in one @ServerExceptionMapper — stable code, safe message, trace id; never a raw stack trace.

p. 110

> A single @ServerExceptionMapper is the Quarkus REST pattern: domain code throws a typed exception, and one method maps it to the wire format, so you never scatter ad-hoc error JSON across resources. Note the media type is application/problem+json (RFC 9457), the status matches the category (409 here — a conflict the client can act on), and the body carries the stable code and the OpenTelemetry traceId for correlation. What's absent: any stack trace, exception class name, or SQL; those leak internals and are an attack surface. Register one mapper per error family, or a base-class mapper that switches on a code.

## [131] APPENDIX E · ERRORS · gRPC: status codes + rich details (sldId 386)

A small fixed set of canonical codes, plus structured google.rpc.Status details in the trailers.

p. 111

> gRPC gives you a small, fixed set of canonical status codes, and the code you choose is part of the contract, because clients (and the Istio mesh) decide retry behaviour from it. INVALID_ARGUMENT and NOT_FOUND are client bugs: don't retry. FAILED_PRECONDITION and ALREADY_EXISTS are state issues: don't retry. UNAVAILABLE and ABORTED are transient: retry with backoff. RESOURCE_EXHAUSTED means you're being rate-limited — honour the RetryInfo delay. DEADLINE_EXCEEDED means tune the timeout. Beyond the code, attach a google.rpc.Status in the trailers with rich details, ErrorInfo (machine reason + domain) and RetryInfo (how long to wait), so the client gets the same five facts as everywhere else.

## [132] APPENDIX E · ERRORS · gRPC errors with rich status details (sldId 387)

[chip] java · Quarkus gRPC

```java
import io.grpc.protobuf.StatusProto;
import com.google.rpc.*;
public Uni<ReserveReply> reserveStock(ReserveRequest req) {
    if (inventoryDown) {
        var status = com.google.rpc.Status.newBuilder()
            .setCode(Code.UNAVAILABLE_VALUE)            // canonical code
            .setMessage("inventory temporarily down")
            .addDetails(Any.pack(ErrorInfo.newBuilder()
                .setReason("STOCK_DOWN").setDomain("inventory").build()))
            .addDetails(Any.pack(RetryInfo.newBuilder().setRetryDelay(
                Duration.newBuilder().setSeconds(2)).build()))  // back off 2s
            .build();
        return Uni.createFrom().failure(
            StatusProto.toStatusRuntimeException(status));
    }
    return stock.reserve(req).map(this::toReply);
}
```

Pick the canonical code (UNAVAILABLE = retryable) and attach ErrorInfo + RetryInfo so clients back off correctly.

p. 112

> This is grpc-java's rich-error model via StatusProto. The canonical code UNAVAILABLE tells the client and the mesh this is transient and retryable; the google.rpc.Status carries structured details — ErrorInfo with a machine reason and domain, and RetryInfo telling the client exactly how long to wait. StatusProto.toStatusRuntimeException packs it into the trailers, and we fail the Mutiny Uni with it. The key discipline: don't overload a generic INTERNAL code for everything — the code is how automated clients and Istio decide whether and when to retry, so getting it right is what prevents both lost work and retry storms.

## [133] APPENDIX E · ERRORS · Kafka: retry topics and a dead-letter queue (sldId 388)

Commit the offset, route the failed record aside, and keep consuming — a poison record never blocks the partition.

p. 113

> Kafka error handling has a failure mode unique to logs: a single poison record can block the whole partition forever if you keep retrying it in place, because the offset never advances — head-of-line blocking that stalls every record behind it. The fix is to move failures aside: try a bounded number of in-place retries, then route the record to a delayed-retry topic (reprocessed after a delay without blocking the live stream), and after N attempts send it to a dead-letter queue for humans or tooling. You commit the offset either way, so the main consumer keeps making progress. With SmallRye Reactive Messaging this is configuration, not hand-rolled plumbing.

## [134] APPENDIX E · ERRORS · Kafka retry + DLQ with SmallRye Messaging (sldId 389)

[chip] java · SmallRye Reactive Messaging

```java
# application.properties — SmallRye Reactive Messaging failure handling
mp.messaging.incoming.orders.failure-strategy=dead-letter-queue
mp.messaging.incoming.orders.dead-letter-queue.topic=orders.DLQ
# or retry with delay first, DLQ only after the retry topics are exhausted:
# ...orders.failure-strategy=delayed-retry-topic
# ...orders.delayed-retry-topic.topics=orders.retry.5s,orders.retry.30s
@Incoming("orders")
@Retry(maxRetries = 3, delay = 200, jitter = 100)   // in-place retries first
public Uni<Void> consume(Order order) {
    return handle(order);   // exhausted retries -> nack -> failure-strategy
}
// the offset is committed by the strategy, so head-of-line is never blocked
```

Bounded @Retry first, then a dead-letter-queue or delayed-retry-topic strategy — declaratively, so a poison record can't stall the partition.

p. 114

> Quarkus makes this declarative. @Retry from SmallRye Fault Tolerance gives bounded in-place retries with jitter; when those are exhausted the method nacks, and the connector's failure-strategy takes over. dead-letter-queue commits the offset and writes the record to orders.DLQ; delayed-retry-topic instead forwards it through a series of delay topics (5s, 30s) for later reprocessing without blocking the live stream, DLQ-ing only after those are exhausted. Either way the offset advances, so one poison record never causes head-of-line blocking. Make handle() idempotent — at-least-once delivery means retried records may have partially applied. This is the framework version of the manual retry/DLQ loop.

## [135] APPENDIX E · ERRORS · GraphQL: partial success with errors[] (sldId 390)

One HTTP 200; the failed field is null and explained in errors[] with a machine code in extensions.

p. 115

> GraphQL breaks the one-request-one-status assumption: a single query can touch many resolvers, so the response is almost always HTTP 200 and carries both a data object and an errors array. When one field fails (say stock can't reach inventory), that field is set to null, an entry is added to errors[] with a message and the path to the failed field, and the machine code goes in extensions.code along with retryable and traceId. The rest of the data still returns. The anti-pattern to call out: blanket-failing the whole query (or returning a 500) when only one field broke — that throws away useful data the client already asked for. Partial success is a feature; let the client decide whether to retry just the failed field.

## [136] APPENDIX E · ERRORS · GraphQL field errors with SmallRye GraphQL (sldId 391)

[chip] java · SmallRye GraphQL

```java
import io.smallrye.graphql.api.ErrorCode;
@ErrorCode("UNAVAILABLE")                    // -> errors[].extensions.code
public class InventoryUnavailable extends RuntimeException {
    public InventoryUnavailable(String m) { super(m); }
}
@GraphQLApi
public class OrderApi {
    public Integer stock(@Source Order order) {     // one field's resolver
        try { return inventory.remaining(order.sku()); }
        catch (Unavailable e) {
            throw new InventoryUnavailable("inventory unavailable"); // nulls field
        }
    }
}
# config: surface the code (and more) in errors[].extensions
quarkus.smallrye-graphql.error-extension-fields=code,retryable,traceId
```

Throw from the field resolver: SmallRye nulls just that field and adds it to errors[] with @ErrorCode in extensions — the rest of data still returns.

p. 116

> Throwing from a single field's resolver is exactly right: SmallRye GraphQL catches it, sets that field to null, and appends an entry to errors[] with the message and path — while every other field resolves and returns normally. The @ErrorCode annotation on the exception maps straight to extensions.code, and quarkus.smallrye-graphql.error-extension-fields controls which fields (code, retryable, traceId) appear in the extensions object. Resist letting the exception bubble to the top and fail the whole operation — that's the blanket-failure anti-pattern. The client sees the order and total, sees stock is null, reads extensions.code, and decides whether to retry just stock.

## [137] APPENDIX E · ERRORS · How a retry storm forms — and how to stop it (sldId 392)

Naive retries multiply load on a struggling service; bounded, spaced, circuit-broken retries break the feedback loop.

p. 117

> This is the failure mode that turns a brief blip into a full outage. The loop: a service slows, calls start timing out, clients retry (often 3x), which triples the load on the already-struggling service, causing more timeouts, causing more retries. It's a positive feedback loop, and naive retry logic is the amplifier. The controls that break it, bottom of the slide: bound every call with a timeout; cap retries to a small number and only for idempotent calls; space them with exponential backoff plus jitter (so clients don't retry in lockstep); add a circuit breaker to fail fast while the dependency is down; enforce a retry budget (cap retries as a percentage of traffic); and shed load early with 429/UNAVAILABLE rather than queueing work you can't do. In Quarkus, SmallRye Fault Tolerance (@Timeout, @Retry with jitter, @CircuitBreaker, @Bulkhead) plus the Istio config from section 2 give you these at both the code and mesh layers.

## [138] APPENDIX E · ERRORS · Error-handling heuristics across all four (sldId 393)

- One contract, four encodings: a stable code, a safe message, a trace id, a retryable flag, field details — everywhere.
- The category lives in the protocol: HTTP status, gRPC code, GraphQL errors[] entry, Kafka DLQ vs retry topic.
- Make retryability explicit and honour it: Retry-After, RetryInfo, extensions.retryable — don't make clients guess.
- Never leak internals: no stack traces, SQL, or class names on the wire; map them to a code and log the detail server-side.
- Bound every retry (@Timeout, @Retry + jitter, @CircuitBreaker, retry budget) and make handlers idempotent.

p. 118

> The cross-cutting checklist to leave on screen. One contract expressed four ways — the same five facts whether it's problem+json, google.rpc.Status, a GraphQL extensions object, or a Kafka DLQ header. Let each protocol carry the category natively rather than inventing your own. Make retryability explicit and machine-readable so clients and the mesh back off correctly instead of guessing. Never leak internals — that's both a security issue and a coupling issue. And the bold line is the one that prevents outages: every retry is bounded and spaced (SmallRye Fault Tolerance gives you @Timeout, @Retry with jitter and @CircuitBreaker declaratively), protected by a retry budget, and every handler idempotent so a redelivered or retried request is safe. Get these right and your failure paths become as boring as your happy paths.

## [139] Appendix F · DDD & Hexagonal Architecture (sldId 394)

F

Where the boundaries and the contracts come from.

> Appendix F. The whole talk assumes you've drawn good service boundaries and know what each API should say — this is where those come from. Domain-Driven Design gives you the strategic tools to place boundaries (subdomains, bounded contexts) and the tactical tools to model what's inside (aggregates, domain events); hexagonal architecture keeps the four protocols we've discussed as mere adapters around a clean domain core. Together they answer: where does an API boundary go, what should its contract say, and how do I keep REST/gRPC/GraphQL/Kafka out of my business logic. The reference is Vlad Khononov's Learning Domain-Driven Design.

## [140] APPENDIX F · DDD · Why DDD belongs in an API talk (sldId 395)

- An API is a contract between two bounded contexts — so “where's the boundary?” and “what does the contract say?” are DDD questions before they're API questions.
- Strategic DDD places the boundaries: subdomains (core, supporting, generic) and bounded contexts, each with its own model and ubiquitous language.
- Tactical DDD models what's inside: aggregates (consistency boundaries), entities, value objects and domain events — which become your resources and your Kafka events.
- Hexagonal architecture keeps it clean: the domain core is isolated, and REST, gRPC, GraphQL and Kafka are just adapters plugged into ports.
- Get the boundaries right and the APIs almost design themselves; get them wrong and no amount of REST polish will save you.

p. 119

> Set up why a DDD appendix belongs in an API talk. The throughline: an API is the contract between two bounded contexts, so the hardest API questions (where to split, what the contract should contain, what stays private) are boundary questions, and DDD is the discipline for boundaries. Distinguish strategic DDD (where the lines go) from tactical DDD (how you model inside a line), and preview that hexagonal architecture is what stops the four protocols from contaminating the domain. The closing line is the one to land: boundaries dominate outcomes far more than protocol polish.

## [141] APPENDIX F · DDD · Strategic DDD: subdomains & bounded contexts (sldId 396)

Place boundaries by business value and rate of change; each context owns one model and exposes it through an API.

p. 120

> Strategic DDD first. Classify the business into subdomains by value and volatility: core subdomains are your competitive edge, complex and fast-changing, where your best people belong; supporting subdomains are necessary but not differentiating, so build them cheaply; generic subdomains are solved problems you buy or adopt (auth, notifications). Each subdomain becomes one or more bounded contexts — a boundary inside which one model and one ubiquitous language are consistent. The punchline here is the bottom box: that boundary is exactly where the API sits, and the contract translates between two contexts' models rather than sharing internals. Map it to our system: order and pricing are core, inventory and shipping supporting, auth and notification generic.

## [142] APPENDIX F · DDD · A bounded context is a service-and-API boundary (sldId 397)

- A bounded context is the scope within which one model and one ubiquitous language stay consistent — the natural unit for a service and its API.
- The same word means different things across contexts: an “order” in fulfillment is not an “order” in billing. Don't force one shared model across the system.
- The context's published API is its only public surface; the schema, storage and internal types stay private — this is the “no leaky internal models” rule from anti-patterns, restated.
- Put boundaries where the business naturally splits and where a team can own them end-to-end (Conway's law) — that's where the integration cost is worth paying.

p. 121

> Make the bounded context concrete as the service/API boundary. The vivid example is the word 'order' meaning different things in fulfillment and in billing: that is why a single shared canonical model across the whole company fails, and why each context exposes its own model through an API instead. Tie back explicitly to the anti-patterns section: 'no leaky internal models' is just 'keep the bounded context's internals private.' And invoke Conway's law: boundaries that don't match team ownership generate constant cross-team coordination.

## [143] APPENDIX F · DDD · Context mapping: how contexts integrate (sldId 398)

The relationship patterns between contexts, and which ones your API implements.

p. 122

> Context mapping catalogues the ways two contexts relate. Walk the starred ones because they're what APIs implement: an Open-Host Service is a context that, because many others integrate with it, publishes a stable public API; the Published Language is the shared, versioned schema that API speaks; and an Anticorruption Layer is the translation you build when consuming someone else's context so their model doesn't leak into yours. The others are trade-offs: Conformist means you just accept the upstream model; Shared Kernel means you share a model and therefore change in lockstep — high coupling, use sparingly; Partnership means two contexts co-evolve; Separate Ways means don't integrate. The starred three are the ones to design explicitly.

## [144] APPENDIX F · DDD · Open-Host Service & Published Language (sldId 399)

- Open-Host Service: a context integrated by many publishes a stable, documented API as its public protocol — that's your REST / gRPC / GraphQL surface.
- Published Language: the shared, versioned schema that API speaks (OpenAPI, .proto, Avro), which is exactly what lives in the Apicurio registry.
- Anticorruption Layer: when you consume another context, translate their model into yours at the edge so their concepts never leak into your domain.
- Conformist is the cheap opposite — accept their model wholesale and inherit their changes; choose an ACL instead when the upstream model is messy or volatile.
- So the registry-backed contract from section 9 is a Published Language, and edge/gateway translation is an Anticorruption Layer.

p. 123

> This slide does the real work of connecting DDD vocabulary to the platform we built. Open-Host Service = the public API; Published Language = the schema in the registry; Anticorruption Layer = the translation at your edge. The bold line is the payoff: the audience has already built these things in sections 9 and 8 without the names; now they have the names and the theory. Emphasize the ACL-vs-Conformist choice as a real decision: conform when the upstream is clean and stable, build an ACL when it's messy or changes a lot, because the ACL localizes the blast radius of their changes to one translation layer.

## [145] APPENDIX F · HEXAGONAL · Hexagonal architecture: ports & adapters (sldId 400)

The domain core is isolated; REST, gRPC, GraphQL and Kafka are just adapters that plug into ports.

p. 124

> This is the architectural payoff of the whole protocols discussion. The domain core in the middle holds entities, aggregates and domain logic and depends on nothing — no framework, no I/O. It declares ports: inbound ports (what it can be asked to do) and outbound ports (what it needs from the world). Driving adapters on the left (REST, gRPC, GraphQL) translate an incoming protocol into a call on an inbound port. Driven adapters on the right (a Postgres repository, a Kafka publisher) implement the outbound ports. The arrows all point inward: adapters depend on the domain, never the reverse. The consequence we care about: the four protocols we spent the talk on are interchangeable adapters; you can add gRPC alongside REST, or a Kafka consumer, without touching a line of domain logic.

## [146] APPENDIX F · HEXAGONAL · Ports & adapters in code (sldId 401)

[chip] java · ports & adapters

```java
// domain: ports and the use case, no framework (examples/19-ddd-hexagonal/quarkus)
public interface OrderRepository { void save(Order o); Optional<Order> findById(String id); }
public interface EventPublisher  { void publish(OrderPlaced event); }
public class PlaceOrderUseCase {                // plain Java: no jakarta.* import
    private final OrderRepository repo;  private final EventPublisher events;
    public Order execute(PlaceOrderCmd cmd) {
        Order order = Order.create(cmd);        // aggregate enforces invariants
        repo.save(order);
        events.publish(new OrderPlaced(order.id(), order.sku(), order.quantity()));
        return order;
    }
}
// wiring: the one place CDI meets the use case
@Produces @ApplicationScoped
PlaceOrderUseCase useCase(OrderRepository repo, EventPublisher events) {
    return new PlaceOrderUseCase(repo, events);
}
// driven adapter: Panache behind the port; the REST resource and a CLI call the same use case
@ApplicationScoped @Transactional
public class PostgresOrderRepository implements OrderRepository {
    public void save(Order order) { OrderEntity.from(order).persist(); }
}
```

The domain depends only on ports it declares; CDI injects the adapters (Panache repo, log publisher). Swap or add one without touching the domain.

p. 125

> Walk the blocks. Ports: the domain declares plain Java interfaces, a repository and an event publisher, and depends on nothing else. The use case, PlaceOrderUseCase, is a plain class with no jakarta or Quarkus import: it creates the aggregate, saves it through the port and publishes a domain event through the port. One CDI producer method is the only place the framework meets it. The outbound ports are implemented by adapters: a Panache-backed repository over an OrderEntity (the domain Order stays free of JPA) and a publisher that logs the event.
>
> The driving adapters are thin. The REST resource turns the HTTP body into a command and calls the use case. The command-line adapter is a QuarkusApplication started under a profile that turns the HTTP server off, and it calls the same use case and the same repository. That's dependency inversion serving the boundary: protocols are replaceable, the domain stays stable.

## [147] APPENDIX F · DDD · Aggregates and domain events (sldId 402)

- An aggregate is a cluster of objects treated as one consistency unit — the boundary inside which invariants hold and a single transaction commits. It's usually what sits behind one API resource.
- That makes the aggregate the natural transaction boundary, and therefore the outbox boundary: the state change and the domain event commit together (section 4).
- Domain events (“OrderPlaced”) are first-class in DDD; they become the Kafka events other contexts react to (section 5) — choreography between bounded contexts.
- Keep aggregates small: one aggregate per transaction, reference others by id, and let events connect them — which is exactly the saga story in Appendix D.

p. 126

> Tactical DDD, and it ties three earlier sections together. The aggregate is the consistency boundary: invariants hold within it and one transaction commits it, and it typically maps to a single API resource. Because it's the transaction boundary, it's also the outbox boundary from section 4: state plus event commit atomically. Domain events are the DDD concept that becomes your Kafka topic payloads, enabling choreography across contexts (section 5). And the small-aggregate rule (one per transaction, reference others by id, connect via events) is precisely why cross-aggregate consistency needs a saga (Appendix D). This slide is where DDD stops being abstract and visibly underpins the data, event and saga designs.

## [148] APPENDIX F · DDD · How DDD maps to our API stack (sldId 403)

- Bounded context → a service and its API boundary.
- Open-Host Service / Published Language → the REST/gRPC/GraphQL contract + the Apicurio registry.
- Anticorruption Layer → model translation at the gateway / consumer edge.
- Aggregate → an API resource and the transaction/outbox boundary behind it.
- Domain event → a Kafka event other contexts consume.
  - Reference: Vlad Khononov — Learning Domain-Driven Design (O'Reilly, 2021).

p. 127

> The summary map — leave it up while you recap. Every DDD concept on the left has shown up concretely on the right somewhere in the talk: contexts are services, the OHS/Published Language is the registry-backed contract, the ACL is edge translation, aggregates are resources and outbox boundaries, domain events are Kafka events. The message: DDD is the naming and reasoning behind the boundaries the whole architecture already relies on, not a separate methodology bolted on. Point people to Khononov's Learning Domain-Driven Design for the full treatment.

## [149] Appendix G · Balancing Coupling (sldId 404)

G

Coupling isn't the enemy — imbalance is.

> Appendix G. We've thrown around “coupled” and “decoupled” throughout as if loose is always better. This sharpens it, using Vlad Khononov's Balancing Coupling model. The reframe: coupling is necessary, since a system with zero coupling does nothing, so the goal is to balance it, not eliminate it. Coupling has three dimensions (integration strength, distance and volatility), and a coupling only hurts when all three are high together. This gives precise language for why a shared database is bad but a registry-backed API contract is fine, and it ties every anti-pattern from section 12 back to one model.

## [150] APPENDIX G · COUPLING · Coupling is necessary — balance it, don't eliminate it (sldId 405)

- Components must share some knowledge to collaborate; a system with zero coupling also has zero behaviour. “Loosely coupled” is too blunt a goal.
- Khononov's model evaluates the connection between two components, not the components themselves, along three dimensions: integration strength, distance and volatility.
- The headline: a coupling is only painful when strength, distance and volatility are all high at once — reduce any one and the pain drops.
- This is why “just split it into microservices” can backfire: spreading strong, volatile coupling across a network maximises all three dimensions — a distributed monolith.

p. 128

> Frame the appendix. The central, slightly contrarian idea: coupling is not a defect to be driven to zero — it's necessary, and the real skill is balancing it. Credit Khononov's Balancing Coupling model and stress that it measures the connection between components, not the components, along three dimensions. The headline sentence is the whole model in one line — pain needs all three of strength, distance and volatility to be high. The bold line is the cautionary tale that resonates with anyone burned by microservices: splitting strongly- and volatile-coupled code across a network doesn't remove the coupling, it just adds distance to it — the distributed monolith.

## [151] APPENDIX G · COUPLING · Coupling has three dimensions (sldId 406)

Integration strength × distance × volatility — a coupling only hurts when all three are high.

p. 129

> The model in one picture. Integration strength is how much knowledge two parts share — the more they share, the more likely a change in one forces a change in the other. Distance is how far apart they sit (same method, class, module, service, or system), and it sets the cost of a change that has to cross the boundary. Volatility is how often the coupled thing changes. The cost box at the bottom is the key relationship: strong plus distant is global complexity (the distributed monolith), but it only bites when the code is volatile. A strong, distant coupling on something that never changes costs you nothing. That's why all three dimensions have to be considered together rather than chasing “lose coupling” in the abstract.

## [152] APPENDIX G · COUPLING · The three dimensions, in practice (sldId 407)

- Integration strength: how much knowledge two parts share — from intrusive (private internals) down to contract (an explicit interface). Less shared knowledge = looser coupling.
- Distance: how far apart they sit — method, class, module, service, system. Greater distance raises the cost of any change that crosses the boundary.
- Volatility: how often the coupled thing changes. Khononov derives it from DDD subdomain type — core is volatile, generic is stable.
- Modularity = strength XOR distance: keep strong coupling local, and make anything distant a weak (contract) coupling. Being both strong and distant is the trap.

p. 130

> Unpack each dimension with a concrete handle. Strength is a ladder (intrusive to contract). Distance is intuitive — the further apart, the more it costs to change across the seam. Volatility is the clever part of the model: you can't know the future, but you can predict change-rate from DDD subdomain type (core changes a lot, generic barely changes), which connects this appendix straight back to Appendix F. The bold line is Khononov's modularity rule rendered as a slogan, strength XOR distance: you want exactly one of them, not both; strong-and-local (a cohesive module) is fine, weak-and-distant (microservices via contracts) is fine, strong-and-distant is the distributed monolith.

## [153] APPENDIX G · COUPLING · Integration strength: a ladder, worst to best (sldId 408)

From intrusive (shared internals) to contract (a versioned schema) — across distance, aim for the bottom rung.

p. 131

> Integration strength has four levels, worst to best. Intrusive coupling: one component reaches into another's private internals — the classic case is two services on one database, where either can break the other invisibly. Functional coupling: they share business logic or rules and must change together for functional reasons. Model coupling: they share a data model or DTOs — a shared library of types. Contract coupling: they integrate only through an explicit, stable, versioned contract — and that's our REST, gRPC, GraphQL and Kafka schemas in the registry. Lower on the ladder means less shared knowledge and looser coupling. The rule that matters: the greater the distance between two components, the further down this ladder you need to be.

## [154] APPENDIX G · COUPLING · Strength in our system (sldId 409)

- Intrusive (worst): two services sharing one database, or reaching into another's internals — any change can break the other invisibly. This is the shared-database anti-pattern.
- Functional / Model: sharing business logic or a model — e.g. a shared library of types. Fine within a context; risky across teams because it forces lockstep change.
- Contract (best across distance): integrate only through an explicit, versioned schema — our REST/gRPC/GraphQL APIs and Kafka event schemas, governed by the registry.
- The rule: the greater the distance, the weaker the coupling must be. Across services that means contract coupling — never shared state.

p. 132

> Map the ladder onto decisions in our system. The shared database is intrusive coupling and it's the worst precisely because the integration strength is maximal and invisible — neither side knows what the other depends on. Shared libraries are model/functional coupling: perfectly fine inside one bounded context or team, dangerous when they force two independently-deployed teams to release together. Contract coupling (APIs and event schemas in the registry) is the only strength level appropriate across service distance. The bold rule is the actionable takeaway and it's exactly why every cross-service integration in the talk went through a registered contract rather than a shared table.

## [155] APPENDIX G · COUPLING · Balancing coupling: strength vs. distance (sldId 410)

Strong or distant, rarely both — and put any unavoidable strong-and-distant coupling where volatility is low.

p. 133

> This brings strength and distance together into the design rule. Read the quadrants: high strength and close together is a cohesive module — perfectly healthy, keep it local. Low strength and distant is healthy microservices — services integrating through contracts. Low strength and close is needless indirection — you've split things that could just be merged. And the danger quadrant, top-right, is high strength at high distance: the distributed monolith, global complexity, where one change ripples across services and teams. The right-hand panel adds the third dimension: even a top-right coupling is tolerable if it never changes, but on volatile core-domain code it's where slow delivery and outages come from. So the formula: balance equals strength-XOR-distance, OR low volatility.

## [156] APPENDIX G · COUPLING · Distance and volatility (sldId 411)

- Distance is the cost multiplier: a change contained in one module is cheap; the same change spanning two services and two teams is slow and expensive.
- Volatility is the trigger: a strong, distant coupling on code that never changes is harmless; on volatile core-domain code it's where outages and slow delivery originate.
- Predict volatility from the domain: core subdomains change often — keep their couplings weak and local; generic subdomains are stable, so you can afford more coupling.
- Balance = (strength XOR distance) OR low volatility — put any unavoidable strong-and-distant coupling where the code rarely changes.

p. 134

> Deepen distance and volatility. Distance is why the same logical change can be a one-line edit or a multi-team, multi-deploy project — it multiplies cost. Volatility decides whether a less-than-ideal coupling matters: a textbook-ugly coupling on frozen code is a non-problem; a textbook-fine coupling on hot, ever-changing core code can still hurt. The DDD connection (from Appendix F) is the practical tool: subdomain type predicts volatility, so you route your strongest couplings away from core and toward stable, generic areas. The bold formula is Khononov's balance condition — worth writing on a whiteboard in a design review.

## [157] APPENDIX G · COUPLING · Coupling and our APIs (sldId 412)

- Every protocol choice we've made is a coupling choice: REST, gRPC, GraphQL and events are all contract coupling — the loosest kind that still lets services collaborate.
- The registry is what keeps that contract coupling stable: compatibility rules stop a producer from silently raising the integration strength on its consumers.
- Connascence (Page-Jones) is a finer lens on the same idea — API versioning is managing connascence of name and position in your schemas (why protobuf field numbers matter).
- Every anti-pattern from section 12 is an imbalance: shared DB = intrusive at distance; chatty sync chains = strong + distant + volatile; leaky models = model coupling across a boundary.

p. 135

> Bring it home to the talk's content. The reframe to offer: every protocol decision was secretly a coupling decision, and we kept choosing contract coupling because it's the loosest that still works across distance. The registry's compatibility gate is, in this language, a guard against a producer silently increasing integration strength on consumers — that's what a breaking change is. Mention connascence as the finer-grained classical model (Page-Jones) that versioning manages — protobuf field numbers are connascence of position made explicit and stable. The bold line re-diagnoses the anti-patterns section through the coupling model, which is a satisfying way to show these aren't separate lists of rules but one underlying principle.

## [158] APPENDIX G · COUPLING · Heuristics for balanced coupling (sldId 413)

- Don't chase zero coupling — chase balance. Strong coupling is fine when it's local and stable.
- As distance grows, drive strength down: across services, integrate only through versioned contracts, never shared state.
- Keep strong, volatile couplings inside a single bounded context or aggregate, where distance is small.
- Use DDD subdomain types to predict volatility, and put your weakest couplings around the parts that change most.
  - References: Vlad Khononov — Learning Domain-Driven Design (O'Reilly) and Balancing Coupling in Software Design (Addison-Wesley).

p. 136

> The closing heuristics — the slide to leave up. Don't eliminate coupling, balance it; lower strength as distance rises; keep strong-and-volatile couplings local (inside an aggregate or context); and use subdomain types to predict volatility so your loosest seams are around your most-changing code. These five lines are a usable design-review checklist. Close by pointing to both Khononov books, Learning Domain-Driven Design for the boundary tools in Appendix F and Balancing Coupling in Software Design for this model, as the two references that underpin both of these appendices.

## [159] Appendix H · Graceful Shutdown (sldId 414)

H

Disposability, kept as a promise.

> Appendix H. This is the operational flip side of factor 9 (disposability) and the cloud-native pillars: pods are killed and replaced constantly, so a service has to be able to go away cleanly. Ungraceful exits are the source of the 5xx blips users see during otherwise-healthy rolling deploys. The thesis: graceful shutdown isn't one setting, it's a short protocol between your app and Kubernetes — stop new traffic, finish in-flight work, drain consumers and sockets, then exit before the grace period runs out.

## [160] APPENDIX H · SHUTDOWN · Disposability is a promise you have to keep (sldId 415)

- Pods are cattle: every deploy, scale-down, autoscale event or reschedule kills and replaces them — often many times a day.
- An ungraceful exit drops in-flight requests, abandons unacked messages and leaves work half-done: the 5xx blips users notice during a rollout.
- Graceful shutdown is the flip side of factor 9, disposability: stop taking new work, finish what you accepted, release resources, then exit.
- It's a protocol between your app and the platform, not a single setting, and the platform gives you a fixed budget to do it in.

p. 137

> Set up the appendix by connecting it to two earlier ideas: factor 9 (disposability) from the twelve-factor arc, and the resilience pillar. The motivating story is the one every team has lived: a rolling deploy that looks healthy in tests but throws a scatter of 5xx errors in production because pods were torn down mid-request. Stress that this is not about a magic flag — it's a sequence the app and Kubernetes perform together, on a clock. This appendix walks that sequence, then shows the code on both sides of it.

## [161] APPENDIX H · SHUTDOWN · What happens when Kubernetes stops a pod (sldId 416)

SIGTERM starts a race; readiness-down plus a short preStop keep new traffic off until you've drained.

p. 138

> Walk the two lanes. Top, Kubernetes: it sends SIGTERM to PID 1, starts the terminationGracePeriodSeconds clock, and will SIGKILL you if you overrun. The catch is the red box — removing the pod from the Service endpoints is asynchronous (kube-proxy, kubelet, the mesh all have to catch up), so for a moment after SIGTERM traffic can still arrive. Bottom, your pod: the response is to flip readiness DOWN immediately (which starts the deregistration) and run a short preStop sleep to cover the lag, then stop accepting, drain in-flight work, stop consumers and close resources, and exit — ideally well before the grace period ends. The red arrows are the whole point: readiness + preStop are what keep new traffic off your dying pod during the race.

## [162] APPENDIX H · SHUTDOWN · The contract with Kubernetes (sldId 417)

- SIGTERM is the signal: Kubernetes sends it to PID 1, then waits terminationGracePeriodSeconds (default 30s) before SIGKILL.
- Readiness DOWN is how you stop new traffic — the pod leaves the Service endpoints but keeps running to finish in-flight work.
- There's a race: endpoint removal is asynchronous, so traffic can still arrive briefly after SIGTERM — a short preStop sleep covers the lag.
- Liveness must stay UP during the drain, or the kubelet restarts a pod that is already winding down.
- Set the grace period larger than your longest acceptable in-flight operation — too short cuts work off, too long stalls deploys.

p. 139

> These five points are the rules of the protocol. The distinction that trips people up is readiness vs liveness during shutdown: readiness should fail (it stops new traffic), but liveness must not fail (the kubelet would restart a pod that is draining). The asynchronous-deregistration race is the subtle one — it's why a preStop sleep exists at all; it's not about doing work, it's about waiting for the rest of the cluster to stop routing to you. And the sizing rule on the grace period is the practical lever: it must exceed your real worst-case in-flight operation, with headroom, or you'll be SIGKILLed mid-request.

## [163] APPENDIX H · SHUTDOWN · Graceful means something different per workload (sldId 418)

Only HTTP drains automatically; Kafka consumers, WebSockets and jobs each need their own drain.

p. 140

> The trap is assuming 'graceful shutdown' is one thing. Only HTTP request draining tends to be automatic (the server stops accepting and finishes in-flight). Everything else you wire up yourself in your shutdown hook. Kafka consumers: stop polling, finish the records already in hand, commit offsets, and leave the group so the rebalance is clean. WebSockets (from Appendix C): you can't finish a long-lived connection, so send a close/go-away and rely on client reconnection plus the per-connection seq and backplane. Jobs and schedulers: stop starting new work and either let running jobs finish or checkpoint so they resume after restart. The green footer is the safety net under all of it — because a hard SIGKILL is always possible, idempotent handlers make a redelivered request or message harmless.

## [164] APPENDIX H · SHUTDOWN · Graceful shutdown in Quarkus (sldId 419)

[chip] java · Quarkus

```java
// ShutdownState + DrainReadinessCheck (excerpt), examples/21-graceful-shutdown/quarkus
// application.properties: quarkus.shutdown.delay-enabled=true, delay=5S, timeout=20s
@ApplicationScoped
public class ShutdownState {          // one SIGTERM starts the delay, then HTTP stops, drains
    void onDelayInitiated(@Observes ShutdownDelayInitiatedEvent event) {   // SIGTERM received
        shuttingDown.set(true);            // readiness reports DOWN; the pod keeps serving
        Log.info("SIGTERM received — readiness flipped to 503, draining...");
    }
    void onShutdown(@Observes ShutdownEvent event) {      // delay over: HTTP stops, drains
        Log.infof("shutting down HTTP server (in_flight=%d)", inFlight.get());
    }
}
@Readiness @ApplicationScoped              // /readyz = this check + the datasource check
public class DrainReadinessCheck implements HealthCheck {
    @Inject ShutdownState shutdownState;
    public HealthCheckResponse call() {
        var builder = HealthCheckResponse.named("drain");
        return shutdownState.isShuttingDown()
            ? builder.down().withData("reason", "shutting down").build()
            : builder.up().build();
    }
}
```

One SIGTERM flips readiness; after quarkus.shutdown.delay (5 s) Quarkus stops HTTP and drains in-flight requests within quarkus.shutdown.timeout (20 s).

p. 141

> Example 21 lets Quarkus run the drain. With quarkus.shutdown.delay-enabled=true, one SIGTERM, the only signal Kubernetes sends before SIGKILL, makes Quarkus fire ShutdownDelayInitiatedEvent and keep serving for quarkus.shutdown.delay (DRAIN_DELAY_SECONDS, 5 s; it plays the part of a preStop sleep) while the endpoint removal propagates. The ShutdownState bean observes the event and flips its flag, so the DrainReadinessCheck, a SmallRye Health @Readiness check, reports DOWN and /readyz answers 503 beside the datasource check, while /healthz keeps answering 200.
>
> When the delay ends Quarkus stops accepting connections, fires ShutdownEvent, waits for in-flight requests up to quarkus.shutdown.timeout (20 s), closes the datasource and exits, inside the 30-second grace period. A ShutdownEvent observer is also the hook for what Quarkus leaves to you: Kafka consumers, the scheduler, WebSockets. Pair it with the Kubernetes side: probes, preStop and the grace period.

## [165] APPENDIX H · SHUTDOWN · The Kubernetes side: probes, preStop, grace period (sldId 420)

[chip] yaml · Kubernetes

```yaml
# deployment.yaml — give the pod time to deregister and drain
spec:
  terminationGracePeriodSeconds: 30        # >= preStop + drain + buffer
  containers:
    - name: order-service
      readinessProbe:                      # flips the pod out of the Service
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

p. 142

> The platform half of the contract, the same in every language. terminationGracePeriodSeconds is the total budget: it must exceed the preStop sleep plus the worst-case drain plus a buffer. The readiness probe's periodSeconds times failureThreshold sets how fast Kubernetes stops routing after the service reports not ready, about ten seconds here, which the preStop sleep should cover.
>
> Readiness points at /readyz, which returns 503 from the moment SIGTERM arrives. Liveness points at /healthz, which keeps answering during the drain, so the kubelet does not restart a pod that is shutting down cleanly. The examples expose both endpoints in all six languages.
>
> The preStop sleep looks crude, but it is the practical fix for the asynchronous-deregistration race: align it with the probe timing rather than picking an arbitrary number.

## [166] APPENDIX H · SHUTDOWN · Beyond HTTP: messages, sockets, jobs (sldId 421)

- Only HTTP drains without extra code; everything else needs explicit drain code in your shutdown hook.
- Kafka consumers: stop polling, finish the records in hand, commit offsets, and leave the group so the rebalance is clean (ties to Event-Driven).
- WebSockets: send a close / go-away, let clients reconnect to another pod, and lean on the per-connection seq + backplane from Appendix C.
- Jobs and schedulers: don't start new work; let running jobs finish or checkpoint so they resume after restart.
- A hard SIGKILL is always possible — idempotent handlers make a redelivered request or message safe, which is your real safety net.

p. 143

> Reinforce the per-workload point from the diagram with the concrete drain steps. The Kafka sequence is the one to emphasize because it connects to the at-least-once delivery discussion from the Event-Driven section: committing offsets on the way out minimizes redelivery, and leaving the group makes the rebalance fast. WebSockets can't be 'finished,' so graceful there means handing the client off, which is exactly what the Appendix C reconnection design enables. The closing bold point anchors the whole appendix: you cannot guarantee a graceful exit, because the kubelet will sometimes SIGKILL you, so idempotency is what makes the system safe, and graceful shutdown makes the unsafe window rare.

## [167] APPENDIX H · SHUTDOWN · Graceful shutdown checklist (sldId 422)

- Handle SIGTERM; flip readiness DOWN first so the Service stops routing before you stop accepting.
- Add a short preStop sleep to cover asynchronous endpoint removal; keep liveness UP throughout the drain.
- Drain in-flight HTTP, commit consumer offsets, close sockets and pools — all bounded by terminationGracePeriodSeconds.
- Make the work idempotent so the inevitable occasional SIGKILL is survivable.
- Test it under a real SIGTERM during a rolling deploy — not just a happy-path integration test.
  - References: Quarkus lifecycle guide & M. Eisele, “Quarkus Graceful Shutdown” (2026); uvicorn — --timeout-graceful-shutdown.

p. 144

> The leave-up summary. Read it as an ordered runbook: readiness first, preStop to cover the race, then the actual drains, all inside the grace budget. The fourth point turns shutdown from fragile to safe: with idempotency, the occasional hard kill is a non-event. And the bold final point is the one teams skip: graceful shutdown that's never tested under a real SIGTERM during a rollout is just hopeful configuration. Encourage a small script (or a chaos test) that kills a pod mid-request and asserts the client still got an answer — exactly how the referenced Quarkus write-up proves its recipe.

## [168] Appendix I · L7 Routing & Traffic Management (sldId 423)

I

Software-defined, north/south and east/west.

> Appendix I. This one is large enough to be its own talk — the user explicitly suggested it could be cut later for that. The thesis: L7 routing isn't one box in a rack any more; it's a four-layer stack of software (edge, gateway, mesh, in-app) that makes decisions on every HTTP and gRPC envelope crossing the network, north/south and east/west. We'll walk what each layer can see and decide, show real config in HAProxy/Nginx/Istio, cover sticky sessions, traffic steering, payload modifications and latency, then go inside the app for rule-based routing with Quarkus + Apache Camel + Drools, then circle back to east/west, where most routing decisions happen.

## [169] APPENDIX I · L7 ROUTING · L7 routing: software, not silicon (sldId 424)

- The hardware load balancer used to be where routing decisions lived. In a cloud-native system that work has moved into software — programmable, observable, and runnable anywhere.
- L7 means application layer: the router sees the HTTP or gRPC envelope (host, path, method, headers, cookies, gRPC service.method) and can route on any of it.
- It lives in four layers — edge / ingress, API gateway, service mesh, and (sometimes) inside the app itself. Each makes a different type of L7 decision.
- It runs both directions: north/south (clients into your system) and east/west (service to service). Most L7 decisions happen on internal traffic.
- The non-hardware stack is open source and composable: HAProxy, Nginx, Envoy, Istio, Linkerd, Kong, Traefik, Apache Camel, Kogito DMN, Drools — plus a YAML or two.

p. 145

> Open the appendix by reframing what L7 routing is in 2026: not an appliance, but layered software that runs inside Kubernetes alongside everything else. The four-layer mental model (edge, gateway, mesh, in-app) is the backbone of the whole appendix — we'll touch each layer in turn. Stress north/south plus east/west early; people default to thinking about ingress, but inside a microservices system the volume of east/west calls dwarfs north/south, and that's where mTLS, retries and locality routing earn their keep. Name the open-source pieces explicitly so the audience knows the talk is about real, free, runnable software.

## [170] APPENDIX I · L7 ROUTING · L4 vs L7: what each layer can decide on (sldId 425)

L4 sees connections; L7 sees the conversation — paths, headers, methods, cookies, gRPC service.method.

p. 146

> Anchor the discussion in the OSI model just enough to be useful. L4 is the layer of IPs, ports and TCP — a classic load balancer can pick a backend by 5-tuple and hash-balance traffic, but it cannot read URLs, headers, cookies, methods or gRPC metadata. L7 sees the full HTTP/gRPC envelope: host, path, headers, cookies, JWT claims, query parameters, methods, and the gRPC service.method pair. That's the entire menu of inputs the routing patterns in this appendix use to make routing decisions. The TLS SNI line in both columns matters: L4 LBs can route by SNI without terminating TLS (cheap, opaque), while L7 LBs typically terminate TLS so they can see everything else (richer, slightly slower).

## [171] APPENDIX I · L7 ROUTING · The L7 capability menu (sldId 426)

- Routing rules: path / host / header / method / cookie / gRPC method → backend.
- TLS termination: decrypt at the edge, re-encrypt (or use mTLS) inward.
- Traffic management: canary, blue/green, A/B, header-based, geo, shadow.
- Payload modification: inject / strip headers, rewrite URLs, transform bodies.
- Resilience: timeouts, retries with backoff + jitter, circuit breakers, outlier ejection — the same toolkit from Appendix E, applied at the network.
- Cross-cutting: authn/authz, rate limiting, WAF, request mirroring, full traces and metrics on every hop.

p. 147

> Read this as the menu of L7 features you can mix and match across layers. The bold last point is the operational payoff: every L7 router emits traces and metrics, which is how you see what is happening across the four layers, and it ties back to the observability section. Most of these features used to be hardware appliances; now they're an annotation or a YAML block away. The resilience capabilities (timeouts, retries, circuit breakers) overlap with what Appendix E said about avoiding retry storms: the mesh implements many of them by default, but you still need bounded retries and budgets to prevent amplification.

## [172] APPENDIX I · L7 ROUTING · Where L7 lives: the layered stack (sldId 427)

Four layers, north/south at the top, east/west at the bottom, each making a different type of L7 decision.

p. 148

> This is the backbone diagram for the whole appendix. North/south traffic (clients into the system) enters through the edge/ingress layer (HAProxy, Nginx, Envoy, Traefik), where TLS terminates and coarse host/path routing happens, then through the API gateway (Kong, Istio gateway, Spring Cloud Gateway), which handles product-level concerns like auth, rate limiting and transformation. Once inside the cluster, east/west traffic is governed by the service mesh (Istio + Envoy sidecars, or Linkerd) — every internal call gets mTLS, retries, outlier detection and locality-aware load balancing. Finally, when L7 decisions need to consider business rules the platform doesn't know about, you push routing into the app itself (Quarkus + Apache Camel + Drools + Kogito DMN). Each layer is the right place for a different type of decision; every topic in this appendix maps to one of them.

## [173] APPENDIX I · L7 ROUTING · A request's L7 path (sldId 428)

One HTTP request is a chain of L7 decisions made by four independent components.

p. 149

> Walk a single request left to right. It starts at the client — say a browser or another service. The edge load balancer terminates TLS, does host/path routing and maybe WAF; the API gateway authenticates the caller, applies rate limits and may transform; the mesh sidecar adds mTLS for the cluster's internal hop, applies retries and locality routing; and finally the service can do its own in-app routing if the business rules demand it. Each box can refuse, transform or branch the request, and each emits a trace span, so the full path is observable end to end. This is the request lifecycle from section 11, viewed through the L7 lens.

## [174] APPENDIX I · L7 ROUTING · Open-source L7 building blocks (sldId 429)

- HAProxy: fast, battle-tested L7 LB; ACL-driven config; classic ingress.
- Nginx: ubiquitous web server / LB; location-block routing; widely used as ingress controller.
- Envoy: the modern L7 proxy; HTTP/2, gRPC, dynamic config; the sidecar of choice.
- Istio: a control plane built on Envoy; CRDs for routing, security, observability across the mesh.
- Kong, Traefik, Spring Cloud Gateway: opinionated API gateways with plugin ecosystems.
- Apache Camel + Drools / Kogito DMN: when the routing logic is a business rule, push it into the app — EIP DSL + a rule engine.

p. 150

> Differentiate the pieces so the audience knows when to reach for which. HAProxy and Nginx are the workhorses of the edge — mature, fast, predictable. Envoy is the modern choice for sidecars because it speaks HTTP/2 and gRPC natively and supports dynamic configuration via xDS. Istio (and Linkerd) wrap Envoy in a control plane and give you the mesh CRDs (VirtualService, DestinationRule). Kong, Traefik and Spring Cloud Gateway are API gateways with plugin ecosystems and a more product-aware feature set. The bold last point introduces the rule-based routing material: when the decision is 'route based on a business rule a non-developer needs to change weekly,' the right place is a rule engine inside the app, not a YAML file in the cluster.

## [175] APPENDIX I · L7 ROUTING · Content-based routing with HAProxy (sldId 430)

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

p. 151

> HAProxy is the lingua franca of L7 LBs. The pattern is always the same: declare ACLs that read parts of the L7 envelope (path_beg for URL prefixes, hdr/req.hdr for headers, content-type for the body type), then use_backend dispatches based on those ACLs in order. This single frontend shows four different content-based routing decisions — by content-type (gRPC traffic goes to a gRPC pool), by cookie (canary users), by header (internal users), by path. Notice TLS terminates at this frontend; everything inside is plaintext within the cluster (or re-encrypted via mTLS at the mesh layer). HAProxy's reload semantics are graceful by default — it can drain old workers while new ones take traffic, which matters for Appendix H's shutdown discipline.

## [176] APPENDIX I · L7 ROUTING · Content-based routing with Nginx (sldId 431)

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

p. 152

> Nginx's content-based routing is built around location blocks and the map directive. The map is the elegant bit: it converts a header value into a variable, which then drives proxy_pass — you express the routing table declaratively, then point a single location at the variable. Location blocks split HTTP from gRPC (grpc_pass) so you can run both protocols through one server. The X-Request-Id injection is a tiny example of payload modification — the L7 router can inject correlation headers so downstream traces can be stitched together. Nginx as an ingress controller in Kubernetes (the ingress-nginx project) is one of the most-deployed L7 routers in the world.

## [177] APPENDIX I · L7 ROUTING · Content-based routing in the mesh: Istio VirtualService (sldId 432)

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

p. 153

> The same content-based routing primitives, but expressed as Kubernetes CRDs that the mesh control plane (Istio) compiles down to Envoy sidecar configuration. Three match rules, each sending to a different DestinationRule subset: by URI prefix (which is how you route on gRPC service.method, since gRPC paths look like /package.Service/Method), by header, and by cookie. The default route at the bottom is critical; without it, unmatched requests have nowhere to go. The CRD lives in Git, gets reviewed like any other change, and Istio reconfigures every sidecar in the cluster within seconds. This is the modern face of L7 routing — declarative, GitOps-managed, distributed across thousands of pods.

## [178] APPENDIX I · L7 ROUTING · SSL / TLS termination at L7 (sldId 433)

- Edge terminates TLS so the L7 router can read and route on the request — you cannot inspect headers or paths through an encrypted connection.
- Re-encrypt or mTLS inward: terminate at the edge, then either plaintext within the cluster (rare today) or mTLS via the mesh (the modern default).
- Certificate management: cert-manager + Let's Encrypt for public certs; SPIFFE / SDS for service identity inside the mesh; Istio rotates pod certs automatically.
- TLS passthrough (no termination) when you need end-to-end encryption (gRPC client mTLS, regulated payloads); route by SNI only.
- Cost: TLS handshakes are real CPU. Modern stacks use session resumption, TLS 1.3 and HTTP/2 to amortise the cost across many requests.

p. 154

> Cover the three modes of TLS at the edge: terminate-and-decrypt (the common case, lets you do L7 things), terminate-and-re-encrypt (most secure default in a mesh, since mTLS inside is automatic), and passthrough (when you must not see the payload, e.g. client mTLS for regulated traffic — route by SNI only). cert-manager is the standard cluster-side answer for public certificates; SPIFFE-style identity and Envoy's SDS handle service-to-service certs automatically inside the mesh. Mention the CPU cost briefly so the L7 latency budget makes sense — a TLS handshake is milliseconds, and you want to amortise it via session resumption, TLS 1.3 and HTTP/2 multiplexing.

## [179] APPENDIX I · L7 ROUTING · Sticky sessions: cookie vs IP-hash vs none (sldId 434)

Convenient for legacy state, hostile to elastic scaling — prefer stateless behind a JWT.

p. 155

> Three modes worth knowing about. No affinity is the default and what you want — any pod gets any request, load is even, and client state lives somewhere else (Redis, the JWT, the database). Cookie-based stickiness is what you fall back to when something stateful (a shopping cart in memory, a legacy session) has to stay with one pod; the LB sets a cookie on the first response and uses it to route subsequent requests to the same pod. It works behind any L7 LB but ties the user's session to one pod's lifetime — restart that pod, lose the session. IP-hash hashes the source IP to a pod; it needs no cookies but is fragile to NAT and mobile networks where many users share an IP, leading to skewed load. The red footer is the real cost: stickiness fights elastic scaling, hurts pod restarts and breaks scale-to-zero. Use it only for a known constraint, never as a default.

## [180] APPENDIX I · L7 ROUTING · Sticky sessions in practice (sldId 435)

- When you need them: legacy session state, a stateful WebSocket that hasn't been moved off-process yet, certain rate-limit windows tied to a token bucket per pod.
- Cookie-based is almost always the right choice over IP-hash: it survives NAT and lets clients explicitly drop the cookie.
- What stickiness breaks: even load balancing, fast pod restarts, scale-to-zero, blue/green flips, and a clean Appendix H graceful shutdown for any stateful pod.
- The right fix is usually upstream: move session state to Redis or the JWT, use a backplane for WebSocket fan-out (see Appendix C), and treat every pod as disposable.

p. 156

> Make stickiness a last resort, not a first reach. Cookie-based affinity is the safer of the two stickiness options because clients can drop the cookie and NAT doesn't break it. The list of things stickiness breaks is the real argument against it: it actively fights the entire cloud-native delivery model — elastic scaling, fast restarts, graceful shutdown. The bold final point is the architectural fix: externalise the state. Redis for session data, JWT claims for user identity, the WebSocket backplane from Appendix C for fan-out. With that done, your LB is back to no-affinity and the platform works the way it wants to.

## [181] APPENDIX I · L7 ROUTING · Intelligent traffic steering (sldId 436)

Six familiar shapes — each is a header or weight rule away.

p. 157

> Six patterns that all share the same L7 primitives. Canary: 90/10 weighted routing to a new version, watching metrics and ramping. Blue/green: two identical environments, traffic flipped atomically (and rolled back atomically). A/B test: a stable cohort maps to a variant via a user identifier so the same user always sees the same variant — critical for valid measurement. Header-based: dark launches and internal-only previews by routing on x-internal or similar. Geo / latency: send EU users to EU pods for RTT and data residency. Shadow / mirror: copy a percentage of real traffic to a new version, observe its behaviour, but don't return its responses to the client; this tests the new version under realistic load. The point is they're not different things mechanically; they're the same routing rule expressed with different inputs and weights. The difficult part is the deploy discipline around them: alerts that trigger an automatic rollback, gradual ramps, and the metrics that tell you the canary is bad before users do.

## [182] APPENDIX I · L7 ROUTING · Canary release: weighted Istio routing (sldId 437)

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

p. 158

> The canonical Istio canary. Two CRDs working together: DestinationRule defines subsets by pod label (version=v1 and version=v2), and VirtualService routes by weight to those subsets. Changing the weights in Git and reconciling the cluster ramps the canary — typically through 10%, 25%, 50%, 100% over hours or days, with metric gates between each step. If error rate or latency on v2 crosses a threshold, an automated controller (Flagger, Argo Rollouts) flips the weights back to 100/0 in seconds. The same weighted-routing primitive does shadow traffic, geo balance, and blue/green flips — the only thing that changes is which subsets you target and what the weights are.

## [183] APPENDIX I · L7 ROUTING · Header-based steering: dark launches (sldId 438)

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

p. 159

> Header-based steering is how you do dark launches and betas safely. An upstream identity proxy sets an x-acme-beta header for opted-in users, and the VirtualService routes those users to v2 — in real production traffic, on real data, but with zero exposure to anyone outside the beta. First match wins, so order the rules from most-specific to least, ending with the catch-all default. This is also how you do internal-only previews (route by an internal user-agent string) and per-tenant feature gates (route by an x-tenant-id). Combined with weighted routing, you can do 'roll the canary forward only for the beta cohort,' which is the most surgical release pattern in the toolbox.

## [184] APPENDIX I · L7 ROUTING · Payload modifications (sldId 439)

- Header injection: X-Request-Id, traceparent, X-Forwarded-For, identity claims — propagate context downstream so the trace stitches together.
- Header stripping: drop Authorization or PII headers before forwarding to a less-trusted backend; strip Server / X-Powered-By outbound.
- URL rewrites: /api/v1/orders → /orders internally; clean public URLs over messy service paths.
- Body transformation: rare but possible — protocol translation, redaction, format conversion (Envoy filters, Camel transforms).
- Cost: body inspection means reading the full request into memory — the slowest L7 thing you can do. Use it sparingly, never on every request.

p. 160

> Distinguish the cheap modifications from the expensive ones. Header inject/strip and URL rewrites cost almost nothing: the router is already parsing the HTTP line and headers. Body transformation is the expensive one because it forces the router to buffer the full payload, which kills streaming, blows memory on large requests and can become a bottleneck under load. Two examples: trace context propagation (the W3C traceparent header is how the spans from earlier in the request path stitch together with the spans downstream, which is why the request-id injection in the Nginx example mattered), and identity propagation (the auth proxy validates a JWT once at the edge and injects validated claims as headers so downstream services don't each re-validate). The bold point is the practical advice: if you can do it in the headers, do it in the headers.

## [185] APPENDIX I · L7 ROUTING · Header injection and URL rewrites (sldId 440)

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

p. 161

> Payload modification as configuration, not code. The URL rewrite cleans up the path before forwarding: public /api/v1/orders becomes internal /orders.
>
> The request header set adds the caller's address and the identity from the client's mTLS certificate (its URI SAN, which is the SPIFFE ID inside the mesh), so identity arrives at the network layer. Envoy creates an x-request-id itself when a request has none.
>
> The request header remove strips Authorization and Cookie before the request reaches the backend, after the gateway has validated the token and turned it into trusted claims. The response header remove drops Server and X-Powered-By so responses do not reveal the stack. All of it is declarative and reconciled from Git; no service code is involved.

## [186] APPENDIX I · L7 ROUTING · Beyond the edge: routing inside the app (sldId 441)

- Sometimes the routing decision is a business rule the platform doesn't know about: route 'high-value-customer claims' here, 'European HL7 messages of type A03' there.
- Pushing those rules into HAProxy ACLs or VirtualService matches does not scale: domain experts own them, they change often, and they depend on the payload, not just the envelope.
- The pattern: an in-app router (Apache Camel, Spring Integration, a custom dispatcher) calls a rule engine (Drools, Kogito DMN) and routes on the result.
- It runs inside one service, behind the mesh — not on the network. The mesh still does mTLS, retries and locality; the rule engine just decides where to send the message next.

p. 162

> Pivot from network-layer routing to in-app routing. The threshold is roughly: if the decision can be expressed in a few YAML lines and depends only on the envelope, do it at the mesh. If it depends on the payload, requires a decision table that domain experts edit, or involves complex conditions, push it into the app. The classic example (and the one the code models) is HL7 healthcare messages: route by patient class, encounter type, message subtype — dozens of intersecting conditions a non-developer needs to maintain. That belongs in a rule engine, not a VirtualService. Stress that this isn't an alternative to the mesh; it sits behind the mesh, complementing it.

## [187] APPENDIX I · L7 ROUTING · Quarkus + Camel + Drools: rule-based routing (sldId 442)

Camel is the EIP DSL; Drools is the decision engine; Quarkus glues them together.

p. 163

> This is the canonical Java pattern (verified from the Apache Camel and KIE community examples). Inputs arrive over REST, gRPC or Kafka. They land in an Apache Camel route, which is a fluent DSL for Enterprise Integration Patterns: from(...) declares the source, .enrich() gathers any context needed for the decision, .process(rulesEvaluator) calls into Drools (rules) or Kogito DMN (decision tables), which sets a 'whereTo' header on the message. Then .routingSlip(header("whereTo")) dynamically dispatches to one or more destinations based on that header. The Drools rule unit is a separate, version-controlled artefact — .drl rules or DMN decision tables that domain experts can edit independently of the Camel route. The result: the routing logic is data, not code; reroutes don't need redeploys; and the heavy network plumbing stays in the mesh.

## [188] APPENDIX I · L7 ROUTING · A Camel route in Quarkus, calling Drools (sldId 443)

[chip] java · Quarkus + Camel

```java
// pom.xml: camel-quarkus-platform-http, camel-quarkus-kafka, drools-quarkus
@ApplicationScoped
public class OrderRoutes extends RouteBuilder {
    @Inject RulesEvaluator rules;                    // wraps a Drools KieSession
    @Override public void configure() {
        from("kafka:orders.inbound")
            .enrich("direct:lookupCustomer", aggregateStrategy)  // context
            .process(rules::evaluate)                // sets "whereTo" header
            .log("routing ${header.whereTo}")
            .routingSlip(header("whereTo"))          // dynamic dispatch
            .end();
        from("direct:lookupCustomer")
            .to("http:customer-svc/lookup")          // enrich w/ HTTP call
            .unmarshal().json();
    }
}
```

from → enrich → rules.evaluate → routingSlip — the canonical content-based-router EIP, with the decision externalised to Drools.

p. 164

> This is the structure used in the official Camel + Quarkus + Drools content-based-routing example (from Red Hat's iDaaS-style use case). from() picks up Kafka messages. enrich() makes an HTTP call to a customer service to gather additional context and aggregates it onto the exchange. process(rules::evaluate) hands the enriched message to the rule engine, which fires .drl rules against the facts and sets a 'whereTo' header listing one or more destination URIs. routingSlip then dispatches the message to each of those destinations in sequence. The whole pattern is 15 lines of fluent Java; the routing logic lives in the .drl rules, owned by domain experts and editable without a Quarkus rebuild.

## [189] APPENDIX I · L7 ROUTING · A Drools rule: the decision, externalised (sldId 444)

[chip] drl · Drools rules

```drl
// orders.drl  —  edited by domain experts, not developers
package com.acme.orders;
import com.acme.orders.OrderFact;
rule "High-value VIP orders go to the priority queue"
    when
        $o : OrderFact( amountCents > 50_000, customer.tier == "VIP" )
    then
        $o.setWhereTo("kafka:orders.priority,http:notify-vip");
end
rule "European orders go to the EU region"
    when
        $o : OrderFact( customer.region == "EU" )
    then
        $o.setWhereTo("kafka:orders.eu");
end
rule "Default route"
    salience -100                                  // last resort
    when   $o : OrderFact( whereTo == null )
    then   $o.setWhereTo("kafka:orders.default");
end
```

Each rule is a small business statement: when X is true, then route to Y. Edited and reviewed by domain experts.

p. 165

> Drools rules are 'when ... then ...' statements. The 'when' is a pattern match against facts in the working memory (here, OrderFact). The 'then' is the action — in our case, setting the whereTo header that the Camel routingSlip will consume. Two real rules and a default with low salience (so it fires last if nothing else matched). This file is owned by domain experts, the people who decide what 'VIP' or 'high-value' mean, and can be redeployed without a developer touching Camel or Quarkus code. When the rules get complex, Drools/Kogito has a DMN (Decision Model and Notation) flavour with decision tables in a spreadsheet form that non-developers find easier still.

## [190] APPENDIX I · L7 ROUTING · Every L7 hop costs time (sldId 445)

Typical p50/p99 added per stage — the budget you spend before your service even runs.

p. 166

> Set expectations with the numbers. Each L7 capability has a typical cost: TLS termination is sub-2ms, path/header routing is sub-1ms, auth/JWT validation is a few ms, WAF a few more, mesh sidecar another millisecond per hop, rate-limit Redis lookup is a couple of ms. Body inspection is the outlier — it can be 5 to 50 ms depending on size, which is why we say to use it sparingly. The numbers are typical, not authoritative; profile your own stack. The right-side card has the working heuristic: stay under ~10ms total L7 on hot paths. With four layers (edge, gateway, mesh sidecar in, mesh sidecar out), every layer must be lean and justify its latency. The retry-storm discipline from Appendix E applies here too — timeouts must account for the total L7 budget plus the service's own work, or retries will pile up.

## [191] APPENDIX I · L7 ROUTING · L7 pitfalls and how to avoid them (sldId 446)

- Too many hops: edge → gateway → ingress → mesh sidecar in → mesh sidecar out adds up fast. Collapse layers that aren't earning their place.
- Regex-heavy ACLs / matches: each regex evaluation is real CPU. Prefer exact / prefix matches; use regex only when needed.
- Sticky sessions break elasticity without any error: the auto-scaler can't rebalance, restarts are painful, scale-to-zero is gone.
- Body inspection on every request: blows memory, kills streaming. If you must transform bodies, do it on a small percentage or just at the edge.
- Sync auth lookups on the hot path: cache validated tokens, validate JWT signatures locally, never do a per-request DB lookup for identity.
- Misaligned timeouts and retries between layers — a 30s gateway timeout + 3 mesh retries with 10s each = a retry storm at the bottom (see Appendix E).

p. 167

> Run quickly through the failure modes. The hop-count one is the most common: every layer feels free until you measure p99 — then you realise the request crossed seven proxies. The regex point is a perf footgun many people miss. The sticky-session one ties back to the sticky-sessions comparison. Body inspection is the latency-budget killer. The auth-lookup one is the most common cause of cascading slowdowns under load. And the timeout-misalignment is the gateway-to-mesh-to-service version of the retry storm we covered in Appendix E — the lesson is identical: bound retries, align timeouts top-down, give the deepest layer the strictest budget.

## [192] APPENDIX I · L7 ROUTING · East / West: L7 between services, inside the mesh (sldId 447)

Every service-to-service call is L7-routable through the sidecars.

p. 168

> Most L7 decisions in a microservices system don't happen at the edge — they happen east/west, between services, every time service A calls service B. The mesh's sidecar pair handles that traffic: mTLS between services (encryption and identity), HTTP/2 multiplexing, native gRPC support, retries with backoff and jitter, outlier detection (eject misbehaving pods automatically), locality-aware load balancing (prefer same-zone pods to keep RTT low), header-based routing and canary weights for east/west versions, plus rich per-call traces and metrics. The headline is the second box: all of that, per call, with no app code. Application services keep talking plain HTTP or gRPC; the sidecars make it secure, reliable and observable in flight. This is the modern answer to 'how do you build a microservices system that works in production.'

## [193] APPENDIX I · L7 ROUTING · Why east/west L7 matters (sldId 448)

- Internal traffic dominates: in a microservices system the volume of east/west calls dwarfs north/south by 10x or more.
- Security: mTLS everywhere by default — every internal call has an identity, encryption and an audit trail without per-service code.
- Resilience: timeouts, retries, circuit breakers and outlier ejection live in the sidecar, applied uniformly to every internal hop.
- Observability: every internal call gets a span, latency histogram and per-route success rate — the request lifecycle from section 11, populated automatically.
- Locality: prefer same-zone or same-region pods so internal RTT stays in single-digit milliseconds, and graceful failover when a zone goes.
- Routing decisions: header-based canaries and weighted releases work east/west too — you can canary a backend service that has no external traffic at all.

p. 169

> Hammer the volume point first: most production L7 routing happens between services, not at the edge. The security argument is the one that justifies the mesh on its own — mTLS everywhere is otherwise hard to retrofit. The resilience and observability arguments are the operational ones; you stop writing the same boilerplate in every service. Locality is the perf argument: with the right Istio config, two pods in the same zone talk over a few milliseconds; cross-region traffic gets degraded gracefully. And the last point is non-obvious but important: canary releases of a deeply internal service (say, a payments calculation engine that no client touches directly) are possible because the mesh can split east/west traffic by weight — you cannot canary internal services through an edge LB.

## [194] APPENDIX I · L7 ROUTING · Istio for east/west: DestinationRule + VirtualService (sldId 449)

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

p. 170

> Same Istio primitives as the weighted canary, but applied to an internal service (note the cluster.local host). DestinationRule sets up the connection pool (HTTP/2 multiplexing for gRPC), enables outlier detection (5 consecutive 5xxs in 30s ejects the pod), enables locality-aware load balancing (same-zone preferred), and defines version subsets. VirtualService weights east/west traffic 95/5 between v1 and v2 — a canary release of a backend service that no external client knows exists. This is what the 'mesh' is: the same routing CRDs the edge uses, applied everywhere, between every pair of services, configured centrally and enforced by the sidecars.

## [195] APPENDIX I · L7 ROUTING · gRPC east/west specifics (sldId 450)

- gRPC is HTTP/2 under the hood, so it works natively in any L7 router that speaks HTTP/2 (Envoy, Istio, modern HAProxy/Nginx).
- Route by gRPC service.method: the URI path is /package.Service/Method — use a uri prefix match in Istio, grpc_pass in Nginx, or path_beg in HAProxy.
- Header-based balancing matters more for gRPC: connections are long-lived and multiplexed, so least-request or per-request load balancing beats round-robin.
- Streaming RPCs (server-streaming, client-streaming, bidi): retries are dangerous if the stream is non-idempotent — cap retries to UNARY calls in the mesh policy.
- Trailers carry status: a 200 + a non-OK trailer is the gRPC equivalent of a 5xx — outlier detection has to be configured to read trailers, not just the status line.

p. 171

> gRPC has a few sharp edges of its own. Route on the gRPC URI prefix to do per-method canaries. Use least-request (or random-3-choices) load balancing instead of round-robin because gRPC connections are long-lived — a few long-running streams can starve other backends if you round-robin connections instead of requests. Be careful with retries on streaming RPCs: the mesh can retry a UNARY call safely if it's idempotent, but retrying a half-completed streaming RPC will replay half the work — Istio lets you scope retries to specific gRPC status codes and request kinds. And the trailer point is subtle: gRPC returns its real status in HTTP trailers (a 200 with a non-OK gRPC status is a failure), so outlier detection has to know to read those, or it will think a failing service is healthy.

## [196] APPENDIX I · L7 ROUTING · When to use which L7 layer (sldId 451)

- Edge / ingress: TLS termination, host/path routing, WAF, public-facing rate limits. Anything north/south that affects all clients.
- API gateway: cross-cutting product policy — auth, per-consumer rate limits, request transformation, monetisation, key management.
- Service mesh: east/west routing, mTLS, retries, outlier detection, canaries between internal services. The default home for service-to-service L7.
- In-app router (Apache Camel + Drools): when routing depends on business rules, payload content, or decisions that domain experts must own.
- Rule of thumb: prefer the lowest layer that can fully express the decision, and never push business rules into mesh CRDs.

p. 172

> This is the decision guide to leave on screen for a beat. The mental model: each layer has a job it's good at, and pushing work to the wrong layer is where complexity comes from. Edge/ingress for the things every client crosses. API gateway for product-shaped policy. Mesh for east/west and everything internal. In-app for business rules. The bold rule of thumb prevents the common antipattern of growing increasingly baroque Istio VirtualService configs to encode rules that domain experts need to maintain — if it's a business rule, it belongs in a rule engine inside a service, not in a network CRD.

## [197] APPENDIX I · L7 ROUTING · L7 routing checklist (sldId 452)

- Pick one ingress, one gateway, one mesh — don't run three competing L7 layers because each team had a favourite.
- TLS terminates at the edge; mTLS between services in the mesh; cert rotation is automatic (cert-manager + SDS), not a quarterly outage.
- Routing rules live in Git, reviewed like code; GitOps reconciles them; rollback is a git revert.
- Every L7 layer emits traces and metrics — sample the spans, alert on per-route SLOs, watch for retry budget exhaustion.
- Stickiness is an exception, not a default; business rules belong in a rule engine inside a service, not in network YAML.
- Test under load and under failure: bring a pod down, eject a zone, ramp a canary, verify the mesh does what the YAML says.
  - References: HAProxy / Nginx / Envoy docs; Istio traffic management guide; Apache Camel EIP guide; Drools / Kogito DMN docs; the tarilabs/quarkus-content-based-routing example.

p. 173

> Leave the checklist up at the end. The first point is the most common organisational failure — a cluster ends up running three ingress controllers because three teams each picked one. Pick one and standardise. The cert-rotation point is the one teams underestimate — expired certs are still a top-3 outage cause in many shops. GitOps for routing is the operational discipline that makes the whole thing reviewable. Observability and the load/failure-test point are non-negotiable. The references sub-bullet is the reading list: official docs for each piece and the Camel/KIE content-based routing example (the canonical demo for the Quarkus + Apache Camel + Drools pattern shown).

## [198] Appendix K · Monolith to Microservices (sldId 453)

K

Patterns that survive the migration with the system still running.

> Appendix K covers the migration patterns. The thesis: you don't decompose a monolith by stopping it and rewriting; you decompose it incrementally, one bounded asset at a time, with the system serving users the whole way through. We'll walk through the monolith as the starting point, modular monoliths as a frequently-correct destination, the strangler-fig family of patterns for progressive extraction, content-based routing for fine-grained cutover, and the decorating collaborator pattern for wrapping legacy code you can't touch. Code in this appendix uses Quarkus REST + REST Client Reactive + Mutiny, but the patterns are language-neutral.

## [199] APPENDIX K · MONOLITH · A monolith is a unit of deployment (sldId 454)

One process, one binary, one heartbeat. All modules live or die together. Often the right starting point — don't be ashamed of it.

p. 174

> Define the term before fixing it. A monolith is not a code-organisation problem — it's a deployment-organisation property. Even a well-organised codebase with clear modules, layers, and tests is a monolith if it ships as one binary on one heartbeat. The defining property is on the slide: change anywhere, redeploy everything; bug in Reporting can take down Payments; one scaling unit for workloads that scale differently. But the second italic line is what to leave audience with: monoliths are not always wrong. For new products, small teams, or anything that fits in one team's head, they're often the simplest and fastest path to value. Premature decomposition is its own anti-pattern. The conversation is: when does this monolith start hurting more than it helps? — and that's when these patterns earn their keep.

## [200] APPENDIX K · MODULAR MONOLITH · The modular monolith — often the right destination (sldId 455)

Still one deployable, but with strict in-process module boundaries enforced by build tooling — not by gentlemen's agreement.

p. 175

> The intermediate pattern that's often the right destination, not a stepping stone. Modules within one process have clear public APIs (PlaceOrder, ReserveStock, ChargeCard) and private internals that other modules cannot reach. Enforcement is the key bit: in Quarkus you can split the codebase into multi-module Maven/Gradle builds with explicit dependency declarations — ArchUnit or jdeps in CI fails the build if Orders.internals is imported outside the orders module. Modules can share a database, but each owns a schema and no cross-schema joins are allowed. Why this is often the destination: you get most of the benefits of microservices (clear boundaries, replaceable modules, independent reasoning) at a fraction of the operational cost — one Pod, one deployment, one log stream, one debugger session. If you do need to split later, you have a small refactor, not a rewrite. The cost of being wrong about boundaries is also lower.

## [201] APPENDIX K · DECOMPOSED DBS · Modular monolith with decomposed databases (sldId 456)

Data ownership becomes per-module — the hardest part of the split, done while still one process. The next step is mechanical.

p. 176

> Splitting the database is the hard part of decomposition. The insight of this pattern: do that work while you're still one process. Each module gets its own Postgres / Mongo / whatever, its own connection pool, its own Liquibase or Flyway migration history. Quarkus makes this natural — multiple datasources are first-class via 'quarkus.datasource.<named>.*' configuration, and each Panache repository binds to its named datasource. Cross-module data is now async or event-driven — you replace a JOIN with a service call or an event subscription (typically via SmallRye Reactive Messaging). Same discipline microservices require, but with one operational target instead of N. Once this is done, promoting a module to a separate service is a refactor of the deployment topology, not a data-migration project.

## [202] APPENDIX K · STRANGLER FIG · Identify → move → redirect (sldId 457)

Named after the strangler fig vine: grow the new system around the old until the old can be removed.

p. 177

> The Martin Fowler strangler-fig pattern, named for the vine that grows around its host tree until the host is gone. The three steps are the unit of work you repeat. Identify: pick a bounded asset — 'order creation' or 'order status query' specifically. The smaller and more bounded, the safer the move. Move: build the new Quarkus service alongside the monolith, replicate the behaviour, test it in parallel without production traffic. REDIRECT: switch callers to the new service. Each cycle is independently reversible. There are three ways to do the redirect: via a proxy, via a proxy plus partial routing, or via a shared database. The proxy is the foundation for everything else.

## [203] APPENDIX K · STRANGLER FIG · With a proxy — step zero of every migration (sldId 458)

Introduce the routing layer first, before extracting anything. Then redirection becomes a config change, not a release.

p. 178

> The pre-condition for incremental migration: clients hit the proxy, the proxy forwards to the monolith. Day zero, behaviour is unchanged. But you now have the lever — the proxy is where you'll later route 1% of /orders/* traffic to the extracted Quarkus service, then 5%, then 100%. Without this step, every cutover requires coordinated client releases. With it, every cutover is a proxy config change. For Quarkus deployments this is typically nginx, Envoy, or Istio gateway as a Kubernetes Service ahead of your application Pods. The proxy is also the right place for TLS termination, auth, rate-limiting, and observability — the strangler-fig literature calls this 'event interception.'

## [204] APPENDIX K · STRANGLER FIG · With proxy + redirection (sldId 459)

The proxy splits traffic between the new service and the shrinking monolith. Roll forward by widening the route; roll back by narrowing.

p. 179

> Now the proxy routes: by path (/orders/* → new Quarkus service), by header (X-Tenant: acme → new service), by percentage (1% → new), or by feature flag (beta users → new). The new service handles its slice; the monolith handles everything else. Clients still see one URL. Roll forward by widening the new-service route in proxy config; roll back by narrowing. The new service can fail completely and the monolith picks up — the bounded blast radius is the entire point. Instrument both paths so you can verify the new service produces the same outcomes as the monolith before widening. For Quarkus, this typically lives in Istio VirtualService rules or nginx server blocks — same patterns from Appendix I, used for migration instead of canary release.

## [205] APPENDIX K · STRANGLER FIG · With a shared database — a deliberate intermediate state (sldId 460)

Process boundary first, data boundary later. Useful intermediate state, not a destination. Schema coupling will bite eventually.

p. 180

> Sometimes the data split is too risky to do at the same time as the process split. In that case the new Quarkus service and the monolith share a database for a while. Both apps read and write the same tables; the new service owns the API but not the data. Useful for extracting reads first (the new service is a read API over the shared store), or as a stepping stone when the data migration is a separate project. A stage, not a destination: every schema change now needs both apps to agree, and the coordination tax grows. The next step is to give the new service its own store: CDC out of the monolith's DB into the new service's via Debezium, or dual-writing during a brief sync window, or event-sourcing the data into the new service. Plan that step before starting the shared-DB phase.

## [206] APPENDIX K · ROUTING · Content-based routing during migration (sldId 461)

[chip] java · Quarkus REST + REST Client

```java
// RouterResource.java (excerpt), examples/24-monolith-to-microservices/quarkus/router
@Path("/")
public class RouterResource {
    @RestClient MonolithClient monolith;           // quarkus.rest-client.monolith.url
    @RestClient NewServiceClient newService;       // quarkus.rest-client.new-service.url
    ConcurrentHashMap<String, String> tenantRoutes = new ConcurrentHashMap<>();  // acme -> new
    volatile String defaultRoute = "monolith";
    @POST @Path("orders")
    public Response createOrder(Map<String, Object> body) {
        String tenant = (String) body.get("tenant");            // decide by content, not URL
        String upstreamBody = routesToNewService(tenant == null ? "" : tenant)
                ? newService.createOrder(body)                   // cut the tenant over
                : monolith.createOrder(body);                    // default: legacy
        return Response.status(201).entity(upstreamBody).build();
    }
    private boolean routesToNewService(String tenant) {
        return "new-service".equals(tenantRoutes.getOrDefault(tenant, defaultRoute));
    }
}
@RegisterRestClient(configKey = "monolith") @Path("/orders")     // one client per upstream
public interface MonolithClient { @POST String createOrder(Map<String, Object> body); }
```

Read the body, decide by content (tenant / region / feature flag), forward through a typed REST Client.

p. 181

> The Quarkus shape. The proxy is a Quarkus REST resource that reads the body and decides which downstream to call. The MicroProfile REST Client (@RegisterRestClient) gives typed outbound calls; declare Uni<T> on the client interface when the proxy should not block a worker thread.
>
> The decision is by payload content (tenant, region, feature flag), not by URL pattern. That makes the pattern more flexible than path-based proxying: you can roll the new service out to one tenant at a time, watch it under production traffic, then widen. Behind a proxy (nginx, Envoy, Istio) the same logic becomes a Lua or WASM filter or an EnvoyFilter at the mesh layer; the resource version shows the shape.
>
> Parsing the body costs CPU. Over a migration of months that cost adds up; over a migration of days it is small next to the risk control it buys.

## [207] APPENDIX K · DECORATOR · The decorating collaborator (sldId 462)

The new service wraps the legacy one, adds capability, then becomes the API. Useful when you can't modify the legacy code.

p. 182

> Different shape from the proxy patterns: the decorator owns behaviour, not just routing. The new Quarkus service sits in front of the legacy API and adds cross-cutting capability: caching, audit, validation, enrichment, fan-out to Kafka, rate-limiting, metrics. The legacy service is unaware. Clients now talk to the decorator's API, which delegates for the underlying work but contributes everything else. Over time, the decorator can take ownership of more behaviour. Particularly useful when the legacy system is a 3rd-party product, a vendor system, or a piece of code so fragile that touching it is forbidden. The decorator is a real Quarkus microservice (its own deploy, its own scaling, its own data) — not just a router. Common implementation: Quarkus + REST Client Reactive + Redis client + Reactive Messaging emitter.

## [208] APPENDIX K · DECORATOR · A decorating collaborator in Quarkus (sldId 463)

```
java · Quarkus REST + REST Client + Redis + Reactive Messaging
```

```
// DecoratorResource.java (excerpt), examples/24-monolith-to-microservices/quarkus/decorator
@RestClient LegacyClient legacy;                   // quarkus.rest-client.legacy.url
@Channel("order-events-out") Emitter<Map<String, Object>> kafkaEmitter;   // Jackson serializer
@POST @Path("orders")
public Response createOrder(Map<String, Object> body) {
    Map<String, Object> legacyResponse = legacy.createOrder(body);     // 1. legacy first
    Map<String, Object> event = new LinkedHashMap<>();
    event.put("event", "order.placed");
    event.put("order_id", legacyResponse.get("id"));
    event.putAll(body);
    kafkaEmitter.send(event);                                          // 2. emit the event
    return Response.status(201).entity(legacyResponse).build();
}
@GET @Path("orders/{orderId}")
public Response getOrder(@RestPath String orderId) {
    String cacheKey = "order:" + orderId;
    String cached = commands.get(cacheKey);                            // 1. Redis lookup
    if (cached != null) return Response.ok(cached).build();            //    CACHE_HIT
    String body = legacy.getOrder(orderId);                            // 2. legacy on a miss
    commands.setex(cacheKey, 60, body);                                // 3. populate, 60 s TTL
    return Response.ok(body).build();
}
```

The decorator adds caching, event emission — capabilities the legacy service can't add on its own.

p. 183

> The Quarkus decorator. LegacyClient is a typed MicroProfile REST Client (quarkus.rest-client.legacy.url), so the call to the legacy service is a method call. The POST path delegates the write to the legacy service, which stays the source of truth, reads the new order id from its answer and emits an order.placed event through a Reactive Messaging Emitter on the order-events-out channel. The event is a map written by the Jackson serializer, so the field order stays event, order_id, then the request fields. The GET path looks in Redis through the Quarkus Redis client (RedisDataSource, quarkus-redis-client), falls back to the legacy service on a miss and populates the cache with a 60-second TTL; the log lines CACHE_HIT and CACHE_MISS show which way it went.
>
> The legacy service does not know it is wrapped, and clients do not know they talk to a decorator.
>
> Over time more behaviour moves into the decorator: validation rules, idempotency keys, deduplication, multi-source reads. To retire the legacy service, implement the order storage inside the decorator (or in a new service it calls) and stop forwarding; the API stays the same for clients.

## [209] APPENDIX K · DECISIONS · Choosing the right migration pattern (sldId 464)

- Modular monolith first, microservices later — the cheapest decomposition is often inside one Quarkus process. Many systems never need to leave this state.
- Decompose the database before decomposing the deployment. The data split is the hard part; doing it with multiple Quarkus datasources is much cheaper than coordinating across services.
- Always introduce the proxy first — the routing layer is what makes incremental cutover possible. No proxy = no incremental migration.
- Strangler with shared database is a transition state. Plan its end before you start it. Schema coupling is debt that accrues.
- Content-based routing when you need to cut over by tenant / region / segment instead of by URL. Costs CPU at the proxy; buys precise risk control.
- Decorating collaborator when you need to add behaviour to a system you can't modify. Most useful for vendor / 3rd-party / legacy-mainframe wrappers.
- Reversibility is the design property to optimise for. Every migration step should be undo-able by a config change, not a release.

p. 184

> Close the appendix with the decision rules. The first point is the most important and most often skipped: a modular monolith is frequently a fine destination. Microservices have real operational cost, and not every system warrants paying it. The second point is the most underrated: the database split is where projects get stuck for years — do it early, while still one Quarkus process, when it's cheaper to redo. The third point is the platform discipline: no proxy, no incremental migration. The fourth point is the schedule discipline: shared-database strangler is OK as a means but never as an end. The fifth and sixth are about choosing the right pattern. The bold final line is the architectural take-home: design for reversibility, so every step is a config change you can undo without coordinating a release. Migrations fail when they reach an irreversible step too early.

## [210] Appendix L · Caching patterns (sldId 465)

L

Six patterns for keeping a cache useful and your data correct.

> Appendix L is the caching reference. Five reasons to cache and six patterns to do it well. The patterns differ in who reads/writes the cache, when, and who owns the consistency story. We use Redis as the canonical cache because it's the default open-source choice on Kubernetes; same patterns apply to in-memory caches or any KV store. CDN and HTTP-layer caching is mentioned in passing but isn't this appendix's focus. Code uses quarkus-redis-client (Mutiny reactive API) throughout.

## [211] APPENDIX L · WHY CACHE · Five things a cache earns you (sldId 466)

- Application performance — a cache hit is microseconds; a database round trip is milliseconds. The hot path becomes ~100x faster on hits.
- Backend load — caching shields the database from repeated reads of unchanged data. Read-heavy workloads can offload 80-95% of queries with a sensible TTL.
- Throughput — the same Pod fleet serves dramatically more requests because it spends less time waiting on the DB. Vertical scaling without buying anything.
- Predictable performance — p99 latency stops being a function of DB load. Tail latencies flatten because the hot path doesn't contend on the same lock-bound resource as everyone else.
- Database cost — fewer queries means smaller (or fewer) DB instances, smaller IOPS budgets, less replication bandwidth. Cache is almost always cheaper than the DB tier it offloads.
  - Trade-off: every cache adds a consistency story, an invalidation story, and a failure-mode story. Pick the pattern that matches the consistency you need from the six patterns in this appendix.

p. 185

> Five concrete reasons that justify the caching investment. Start with application performance — the user-facing speedup is the visible win. Backend load matters more in steady state: shielding the database is what lets your DB tier stay smaller and cheaper than your app tier. Throughput follows from both. Predictable performance is the operational win that is hard to measure: a cache layer flattens p99. Database cost is the financial win that often pays for the entire caching infrastructure. The sub-bullet at the end is what trips teams up: every cache adds complexity; pick the pattern that matches the consistency you need.

## [212] APPENDIX L · CACHE-ASIDE · Cache-aside (look-aside) — the default (sldId 467)

The application reads cache, falls back to DB, populates cache. Explicit and simple; the most common pattern.

p. 186

> The pattern everyone starts with. The Quarkus application is in charge: try the cache first, on a miss query Postgres via Panache, populate the cache on the way back, return. Every other pattern in this appendix differs from this one in who does the work — cache-aside is the baseline. Pros: explicit, debuggable, no magic. Cons: every read has the if/else; cache miss costs two round trips; cache logic is repeated across services if you don't extract it. The TTL is the consistency knob — longer = fewer DB hits, more stale-read risk. Use this when you want explicit control and reads dominate writes.

## [213] APPENDIX L · CACHE-ASIDE · Cache-aside in Quarkus with Redis (sldId 468)

[chip] java · Quarkus REST + Panache + Redis

```java
// CacheResource.java (excerpt), examples/25-caching/quarkus: cache-aside
@GET @Path("cache-aside/products/{pid}")
public ProductView cacheAsideGet(@RestPath String pid) {
    return cachedProduct("ca:product:" + pid, pid);
}
private ProductView cachedProduct(String key, String pid) {
    String cached = cache.get(key);                       // 1. Redis lookup (best effort)
    if (cached != null) {
        return ProductView.of(fromJson(cached, Product.class), "cache");   //    hit
    }
    Product row = store.findProduct(pid);                 // 2. database on a miss (Panache)
    if (row == null) throw new NotFoundException();
    cache.setex(key, toJson(row), ttl);                   // 3. populate
    return ProductView.of(row, "db");
}
@PUT @Path("cache-aside/products/{pid}")
public Response cacheAsideUpdate(@RestPath String pid, ProductUpdate body) {
    store.updateProduct(pid, body.name(), body.priceCents());     // write the database
    cache.delete("ca:product:" + pid);                    // 4. invalidate on write
    return Response.ok(Map.of("ok", true, "action", "invalidated")).build();
}
```

Try cache; on miss, Panache query and populate. Invalidate on write. Three operations; the rest is naming conventions and TTL choices.

p. 187

> Quarkus cache-aside, as Example 25 runs it. SafeRedis wraps the Quarkus Redis client so every call is best effort: a Redis failure is logged and the read falls through to the database. The GET path looks in Redis for ca:product:<id>, falls back to Store.findProduct, a Panache lookup in its own transaction, on a miss and populates the cache with a 60-second TTL; the response says whether the value came from the cache or the db. The PUT path updates the row in a transaction and then deletes the cache key; setting the new value instead is write-through.
>
> For high-cardinality keys, set a maxmemory-policy on Redis (allkeys-lru is typical) so the cache cannot grow without bound.

## [214] APPENDIX L · READ-THROUGH · Read-through — the cache fetches on miss (sldId 469)

Application sees one interface; the cache library handles DB fallback transparently.

p. 188

> The variation where the cache layer, not the application, calls the database on a miss. The app calls cache.get() and gets the value back — doesn't know or care whether the cache had it or had to fetch. For Quarkus, the cleanest expression is via Quarkus Cache annotations (@CacheResult / @CacheInvalidate from quarkus-cache, which can be backed by Caffeine or Redis). The cache library handles miss-time loading; you write the loader as a normal method, annotated. Pros: cleaner application code, single read interface. Cons: less control over what triggers a DB hit. Use when read paths are repetitive across the codebase and you want to eliminate the if/else from every caller.

## [215] APPENDIX L · READ-THROUGH · Read-through in Quarkus with Cache.get (sldId 470)

[chip] java · Quarkus Cache + quarkus-redis-cache

```java
// CacheResource.java (excerpt), examples/25-caching/quarkus: read-through
// application.properties: quarkus.cache.redis.read-through.value-type=com.cndp.cache.Product
//                         quarkus.cache.redis.read-through.expire-after-write=60s
@CacheName("read-through") Cache readThroughCache;       // quarkus-redis-cache
@GET @Path("read-through/products/{pid}")
public ProductView readThroughGet(@RestPath String pid) {
    var loaded = new AtomicBoolean(false);               // did the loader run?
    Product product = readThroughCache.<String, Product>get(pid, key -> {
        loaded.set(true);                                // miss: the cache calls the loader
        Product row = store.findProduct(key);
        if (row == null) throw new NotFoundException();  // nothing is cached for a missing id
        return row;
    }).await().indefinitely();
    return ProductView.of(product, loaded.get() ? "db" : "cache");
}
// Cache.get stores the loader's result under rt:product:<id> with the TTL, and falls back
// to the loader when Redis is unreachable.
```

Cache.get turns the lookup into a loader call: the cache owns the miss path, and a flag in the loader reports where the value came from.

p. 189

> Read-through in Quarkus uses the Cache API from quarkus-cache with quarkus-redis-cache behind it. Cache.get(key, loader) looks in Redis first and runs the loader only on a miss, then stores the result for the TTL (quarkus.cache.redis.read-through.expire-after-write) under the configured prefix, so the application holds no if/else around the cache. The cache needs the value type (quarkus.cache.redis.read-through.value-type) to read entries back. A flag set inside the loader tells the response whether the value came from the cache or the database.
>
> A loader that throws, for a missing product, caches nothing, and when Redis is unreachable Cache.get runs the loader and returns its value, so a Redis outage costs hits, not availability. The annotation form, @CacheResult on a service method, expresses the same pattern declaratively; the explicit call is used here because the response reports the source of the value.

## [216] APPENDIX L · WRITE-THROUGH · Write-through — cache and DB written synchronously (sldId 471)

Every write hits both the cache and the DB. Cache is never stale; writes pay both latencies.

p. 190

> When stale reads are not acceptable, write-through forces every write to update both stores. The Quarkus app calls cache.set(...) and Panache update(...) and both must succeed before the response returns. Pros: a read immediately after a write sees the new value; the cache is never stale for the writer's view. Cons: write latency is the sum of both stores; you have to handle the case where the cache write succeeds but the DB write fails (or vice versa). The usual discipline: write the DB first inside a @Transactional boundary, then write the cache. Accept that a failure between them means the cache may briefly hold a stale value. Pair with a short TTL so any inconsistency self-heals.

## [217] APPENDIX L · WRITE-THROUGH · Write-through in Quarkus (sldId 472)

[chip] java · Quarkus REST + Panache + Redis

```java
// CacheResource.java (excerpt), examples/25-caching/quarkus: write-through
@PUT @Path("write-through/products/{pid}")
public Response writeThroughUpdate(@RestPath String pid, ProductUpdate body) {
    store.updateProduct(pid, body.name(), body.priceCents());  // 1. DB first (source of truth)
    Product row = store.findProduct(pid);                      //    read back the stored row
    if (row != null) {
        cache.setex("wt:product:" + pid, toJson(row), ttl);    // 2. cache second: SET
    }
    return Response.ok(Map.of("ok", true, "action", "set")).build();
}
```

DB first (source of truth), cache second: the managed entity is what gets cached.

p. 191

> Write-through in Quarkus. The update writes the row first, then reads it back through Store.findProduct and caches that value: the canonical row, including server-side defaults. The DB write comes first because the DB is the source of truth; if the cache write fails, you lose cache freshness, not data.
>
> Writing the request body straight to the cache would save a read but can diverge from the row when the database applies defaults, triggers or computed columns. The TTL is the safety net: if cache and DB drift briefly, they converge when the entry expires and the next read repopulates it.

## [218] APPENDIX L · WRITE-AROUND · Write-around — writes skip the cache (sldId 473)

Writes go to the DB only. The next read populates the cache lazily. Good for write-heavy, low-re-read workloads.

p. 192

> When data is written far more often than it's read (audit logs, event records, telemetry), caching every write is wasteful: most cached entries expire before being read again. Write-around solves this: write the DB, leave the cache alone. The next reader pays the cache-miss cost and populates the cache. Pros: no cache pollution by write-only data. Cons: the first read after every write is slow (cache miss); reads of recently-written data are slower than under cache-aside. Pair with cache-aside or read-through on the read side. Common use: any 'append-only' or 'mostly-written' workload — events, log lines, audit entries, IoT telemetry where you read summaries, not individual entries.

## [219] APPENDIX L · WRITE-AROUND · Write-around in Quarkus (sldId 474)

[chip] java · Quarkus REST + Panache + Redis

```java
// CacheResource.java (excerpt), examples/25-caching/quarkus: write-around
@POST @Path("write-around/events")
public Response writeAroundCreate(EventRequest body) {
    store.insertEvent(body.id(), body.type(), body.payload());    // DB only: cache untouched
    return Response.ok(Map.of("ok", true, "action", "db-only")).build();
}
@GET @Path("write-around/events/{eid}")
public Response writeAroundGet(@RestPath String eid) {
    String key = "wa:event:" + eid;
    String cached = cache.get(key);                               // standard cache-aside read
    if (cached != null) { /* ... parse the JSON, add "source": "cache" */ }
    EventEntity event = store.findEvent(eid);
    if (event == null) return Response.status(404).build();
    Map<String, Object> data = new LinkedHashMap<>();             // id, type, payload
    cache.setex(key, toJson(data), ttl);                          // the first read populates
    data.put("source", "db");
    return Response.ok(data).build();
}
```

Writes skip the cache; first read populates. Avoids cache thrash from one-time writes.

p. 193

> Write-around: the write goes to the database through Panache and the cache is not touched; the read side is plain cache-aside, so the first read populates the entry. If a concurrent reader may have cached a stale sibling entry, delete that key after the insert; it is cheap insurance on high-contention paths.
>
> The pattern fits workloads where most writes are never read back. A security event log might take 10,000 writes a minute and 100 reads a day for active alerts; caching every write would churn entries. A product catalog is the opposite: every read is a probable hit, so write-through makes the writer's update visible to the next reader.

## [220] APPENDIX L · WRITE-BACK · Write-back (write-behind) — fast writes, eventual durability (sldId 475)

Writes return immediately after touching the cache; a background flusher persists to the DB asynchronously.

p. 194

> The fastest-write pattern, with the most caveats. The Quarkus app writes to the cache and returns an immediate ack — the cache is the source of truth for that window. A background @Scheduled drains the cache to the DB, batching writes for efficiency. Pros: write latency equals cache latency — microseconds, not milliseconds; massive throughput. Cons: a cache crash before the flusher catches up loses unflushed writes; the cache must be configured for persistence (Redis AOF or RDB), and even then you might lose seconds of data. Use this pattern only when (a) write throughput is the constraint, (b) eventual durability is acceptable, and (c) you've worked out what 'lost the last 5 seconds of writes' means for your business.

## [221] APPENDIX L · WRITE-BACK · Write-back with @Scheduled in Quarkus (sldId 476)

[chip] java · Quarkus + @Scheduled + Redis + Panache

```java
// CacheResource + BackgroundTasks + Store (excerpt), examples/25-caching/quarkus: write-back
// CacheResource: PUT write-back/metrics/{mid} does HSET metric:<mid> {value, tags} and SADD
// metric:dirty <mid>, then answers 202 (queued, not yet durable); 503 when Redis is down
@Scheduled(every = "${cache-service.flush-period:1s}")  // concurrent runs are skipped
void flusher() {                                       // BackgroundTasks
    if (System.currentTimeMillis() < nextFlushAt) return;   // backing off after a failure
    Set<String> ids = cache.spop("metric:dirty", FLUSH_BATCH);    // atomic: no id twice
    if (ids == null || ids.isEmpty()) return;
    List<String> failed = new ArrayList<>();
    for (String mid : ids) {
        try {
            Map<String, String> data = cache.hgetall("metric:" + mid);
            if (!data.isEmpty()) store.upsertMetric(mid, data);   // one upsert per id
            cache.hdel("metric:attempts", mid);
        } catch (Exception e) { failed.add(mid); }       // Log.errorf: flush failed for <mid>
    }
    if (failed.isEmpty()) { failures = 0; return; }
    nextFlushAt = System.currentTimeMillis() + Math.min(FLUSH_PERIOD_MS << ++failures, 8000);
    requeue(failed);   // HINCRBY metric:attempts; SADD metric:dirty, or metric:failed at 5
}
// Store.upsertMetric: statelessSession.upsert(metric), an INSERT ... ON CONFLICT DO UPDATE
```

A write answers 202 Accepted. A failed flush re-queues its ids with backoff; after five attempts an id is parked on metric:failed.

p. 195

> Quarkus write-back, as Example 25 runs it. (1) PUT /write-back/metrics/{mid} writes the metric to a Redis hash, adds the id to a dirty set, which tells the flusher what still has to reach the database, and answers 202 Accepted: the value is queued, not yet durable. (2) A @Scheduled method runs every second (a run is skipped while one is in flight), pops up to FLUSH_BATCH dirty ids with SPOP (atomic, so two flusher instances get distinct subsets and the flusher scales out) and upserts each one through Hibernate's StatelessSession.upsert, which issues INSERT ... ON CONFLICT (id) DO UPDATE, so an id flushed twice stays one row. (3) An id whose upsert fails is re-queued: its count in the metric:attempts hash goes up and it goes back on the dirty set, or, after five attempts, onto metric:failed with its value still in the cache and the failure in the log. After a failed run the flusher waits two seconds, then four, then eight before it tries again.
>
> This is only safe with Redis persistence (AOF, appendonly yes); without it a Redis crash loses unflushed writes. For data that must not be lost, use write-through. For high-throughput telemetry where losing the last second is acceptable, write-back is what lets the service scale.

## [222] APPENDIX L · REFRESH-AHEAD · Refresh-ahead — keep hot keys warm (sldId 477)

A background task refreshes hot keys before their TTL expires. Users never see a cold miss on popular items.

p. 196

> The pattern for eliminating the 'cache miss latency cliff' on popular keys. Plain cache-aside has a sharp behaviour: while a key is cached, reads are fast; the moment its TTL expires, the next reader pays the slow DB-fetch path. For homepage data, top-products, frequently-queried entities, that latency spike is user-visible. Refresh-ahead pre-empts this: a background task watches the cache (or maintains a set of 'hot' keys) and refreshes their values from the DB before the TTL fires. Users always read warm cache. Pros: no user-visible misses on the keys you mark as hot. Cons: extra DB load for keys that may not be requested again; you need a way to identify which keys are hot.

## [223] APPENDIX L · REFRESH-AHEAD · Refresh-ahead in Quarkus (sldId 478)

[chip] java · Quarkus + @Scheduled + Redis sorted set

```java
// BackgroundTasks.java (excerpt), examples/25-caching/quarkus: refresh-ahead
// CacheResource.refreshAheadGet: zadd("product:hot", now, pid), then the cache-aside read
@Scheduled(every = "${cache-service.refresh-period:5s}")
void refresher() {
    double cutoff = (System.currentTimeMillis() / 1000.0) - 300;      // 5-minute hot window
    cache.zremrangebyscore("product:hot", 0, cutoff);
    for (String pid : cache.zrange("product:hot", 0, -1)) {
        long ttlVal = cache.ttl("ra:product:" + pid);
        if (ttlVal > 0 && ttlVal < refreshBefore) {                   // danger zone
            Product row = findProduct(pid);                           // store.findProduct
            if (row != null) {
                cache.setex("ra:product:" + pid, toJson(row), ttl);   // refresh
                Log.infof("refresher: pre-warmed %s", pid);
            }
        }
    }
}
```

Hot keys live in a Redis sorted set scored by last-access time. Refresh those with low TTL.

p. 197

> Refresh-ahead in Quarkus. A Redis sorted set tracks which keys are hot, scored by the last access time; every read touches it. A @Scheduled task runs every 5 seconds: it drops keys not read in the last 5 minutes (ZREMRANGEBYSCORE), then for each remaining key checks the TTL and, when it is under refresh-before-seconds (10 by default), re-reads the row and resets the entry.
>
> A variant subscribes to Redis keyspace notifications for expiry events and refreshes on the event; it is cleaner but needs more setup. The pattern fits read-heavy workloads where a small set of keys serves most traffic and miss latency is visible to users.

## [224] APPENDIX L · ANTI-PATTERNS · When not to cache, and what to watch for (sldId 479)

- Don't cache by default. Caching adds a consistency story, an invalidation story, and a failure-mode story. If reads are already fast, just don't add a cache — the cheapest cache is no cache.
- Don't cache rarely-read data. Caching write-once-read-never data thrashes your cache and gains nothing. Profile your read patterns first.
- Don't cache without a TTL. Unbounded caches grow until they evict at random, which gives you the worst type of failure: unpredictable. Always set explicit expire-after-write or maxmemory-policy on Redis (allkeys-lru typical).
- Avoid cache stampedes (thundering herd): when a hot key expires and many concurrent Quarkus Pods all miss at once, they all hit the DB. Mitigate with a Redis lock per key (only one fetches, rest wait), or refresh-ahead, or jittered TTLs.
- Watch for cache aside + write-around without invalidation — the write goes to the DB but a stale cached value persists for the full TTL. Invalidate on every write, or use a short TTL.
- Treat the cache as a performance optimisation, never as the source of truth. A Redis outage must mean slower reads, not data loss — always have a DB fallback path. Test this by stopping Redis in staging.

p. 198

> The six things that go wrong with caching. The first point is the most important and most often missed: caching is a complexity tax, only worth paying when reads hurt. The second is the write-around lesson: profile first. The third is operational — an unbounded Redis with no eviction policy will OOM-kill itself. The fourth is the cache stampede problem: hot key expires → 100 concurrent Quarkus Pods all miss → 100 simultaneous DB reads → DB tips over. Mitigations: distributed lock per key (only one fetches, the rest wait); refresh-ahead; TTL jitter (add random ms to TTL so similar keys don't expire together). The fifth is the most common stale-data bug. The bold final line is the architecturally important one: the cache is never the source of truth. If Redis dies, you must serve slower reads, not return errors. Build the DB fallback path; test it by killing Redis in staging.

## [225] APPENDIX L · DECISIONS · Choosing the right caching pattern (sldId 480)

- Cache-aside — the default. Use when you want explicit control and reads dominate writes. The pattern everyone should know first.
- Read-through (Quarkus Cache annotations) — use when the read path is repetitive across the codebase and you want declarative caching. Same semantics as cache-aside; cleaner code.
- Write-through — use when zero stale-read risk after a write matters more than write latency. Read-heavy with infrequent writes is the sweet spot.
- Write-around — use when writes far outnumber re-reads. Avoids cache pollution by write-once data.
- Write-back — use only when extreme write throughput is the constraint, eventual durability is acceptable and your Redis is configured for persistence.
- Refresh-ahead — use when a small set of hot keys serves most traffic and miss latency is unacceptable. Adds DB load for the hot set; eliminates user-visible misses.
- Most production Quarkus systems use cache-aside (or @CacheResult) for 95% of cases, with refresh-ahead on a small set of identified hot keys and write-through where stale-read is forbidden. Mix patterns; don't pick one as the rule.

p. 199

> The decision rules to leave audience with. Cache-aside (or Quarkus @CacheResult read-through) is the default and the right pattern for most reads. Write-through trades write latency for read consistency, which pays off when stale reads after writes are harmful (financial, healthcare, regulatory). Write-around is the right pattern for telemetry / events / logs / any append-heavy workload. Write-back is the niche extreme-throughput pattern, with serious caveats. Refresh-ahead is the hot-key pattern. The bold final line is the take-home: don't pick one pattern as 'the' cache strategy. Use cache-aside as the default, layer refresh-ahead on the hot keys you identify, use write-through where consistency demands it, write-around for telemetry. Different read/write profiles want different patterns; matching them is the engineering work.

## [226] Appendix M · Failure modes (sldId 481)

M

Where it all breaks — and the patterns that hold.

> Appendix M is the synthesis appendix — it brings together error handling, graceful shutdown, observability and the resilience patterns from across the deck, and points them at the specific ways distributed systems fail. If you can only take one slide from this appendix, take the matrix at the end: it maps each failure mode to the patterns that address it. This appendix references section 11 (Observability), section 12 (Security — bulkheads), and Appendix H (Graceful shutdown); it is the place where those threads are tied together. If this runs long in your session, it stands alone and can be presented on its own.

## [227] APPENDIX M · Distributed systems fail differently (sldId 482)

- In a single process, an operation succeeds or it throws. Across a network, a call can succeed, fail, hang forever, succeed-but-the-response-is-lost, or succeed-slowly — and you often cannot tell which.
- Partial failure is the defining trait: some dependencies are up, some down, some degraded, all at the same time. There is no global 'the system is up'.
- Failures are not independent: one slow component can exhaust a caller's resources and take down healthy services around it. Failure spreads.
- Some failures lie: a node passes its own health check while failing real traffic (gray failure). What the system believes about itself and what users experience diverge.
- The goal is not zero failures; that is impossible. The goal is to bound the blast radius and recover automatically. All management is risk management.
  - This appendix: six failure modes, the defensive patterns that address them (with code), Istio's mesh-level role, graceful shutdown, how to observe failures, and a mapping matrix.

p. 200

> Set the frame. The single most important conceptual shift for developers moving from monoliths is partial failure: in a monolith a function call either returns or throws, synchronously, in-process. Across a network there is a whole spectrum of failure, including the worst kind — the call that hangs, or the one that succeeded on the server but whose response was lost, leaving the client unsure whether to retry. Emphasise that failures are correlated (one failure causes others) and that some failures are actively deceptive (gray failures). Land the bold point hard: we are not trying to prevent failure, we are trying to bound it and recover. This reframes everything that follows from 'how do we stop failures' to 'how do we contain and survive them.'

## [228] APPENDIX M · A taxonomy of failure modes (sldId 483)

Network failures, component failures, load failures — and the defensive toolkit that addresses them.

p. 201

> The map for the appendix. Three families. NETWORK failures: partition (nodes alive but unreachable) and split-brain (both sides act as leader). COMPONENT failures: partial (some deps fail) and gray (some degrade and are perceived differently by different observers). LOAD failures: amplification (a failure feeds on itself) and cascading (failure spreads to neighbours). Underneath sits the defensive toolkit — timeouts and deadlines, retry with backoff and jitter, circuit breakers, bulkheads (section 12), load shedding, fallback/degradation, quorum/consensus, Istio mesh policies, graceful shutdown (Appendix H), and observability (section 11). Every pattern addresses specific failure modes; the closing matrix maps which to which. Reconnect to the section-1 maxim: all management is risk management — you manage the distribution of failures, not their existence.

## [229] APPENDIX M · NETWORK · Network partition (sldId 484)

Nodes are alive and healthy; they cannot reach each other. CAP forces a choice: consistency or availability.

p. 202

> See the diagram notes. The key teaching point: a partition is not a crash. Every node is healthy and running; the network between them is the thing that failed. This is what makes partitions so confusing to debug — every individual component looks fine. CAP theorem becomes concrete here: while partitioned, you choose to stay consistent (the minority side refuses writes, sacrificing availability) or available (both sides accept writes, sacrificing consistency, reconciling later). Most data systems let you tune this. Kubernetes itself uses etcd, which chooses consistency (the minority side of a control-plane partition stops accepting writes). Address with quorum/consensus, idempotent writes (so a retried write after heal is safe), and partition-tolerant design.

## [230] APPENDIX M · NETWORK · Split-brain (sldId 485)

A partition where both sides think they are the leader and both accept writes. State diverges; the worst partition outcome.

p. 203

> See the diagram notes. Split-brain is the specific catastrophic outcome of a partition in a system that elects a leader or primary. Both sides lose contact, each assumes the other died, each promotes itself, and now you have two primaries accepting conflicting writes. On heal you have divergent state and no clean way to merge. The prevention is quorum: an action requires a majority (N/2 + 1) of nodes to agree, so a minority partition mathematically cannot act — it knows it is the minority and steps down. This is why cluster sizes are odd (3, 5, 7): to always have a clear majority. Fencing tokens (monotonically increasing IDs that let resources reject a stale leader's writes) and leases are complementary. etcd/Raft give the Kubernetes control plane this property out of the box.

## [231] APPENDIX M · COMPONENT · Partial failure (sldId 486)

The defining trait of distributed systems: some dependencies fail while others keep working. Handle each leg.

p. 204

> See the diagram notes. This is the slide for developers moving from monoliths. In a monolith, the order service and the inventory service are function calls in the same process — if one is 'down' the whole process is down. Distributed, the order service calls inventory (healthy), payment (down), and shipping (slow) and must make a per-dependency decision for each: use the healthy result, fall back or fail for the down one, time out and fall back for the slow one. The mistake that causes most production incidents is treating a remote call like a local one, with no timeout, no fallback and no circuit breaker, so a single down dependency hangs the caller. Address with per-call timeouts, per-dependency circuit breakers, fallbacks, and bulkheads. The next several slides are exactly these patterns, with code.

## [232] APPENDIX M · COMPONENT · Gray failure (sldId 487)

The insidious one: a component is degraded and is perceived differently by different observers. Liveness is green; users suffer.

p. 205

> See the diagram notes. Gray failure is the failure mode that defeats naive health checking. The classic shape: a node is slow or dropping a fraction of requests, but its liveness probe (GET /healthz returning 200 from a trivial handler) still passes, so Kubernetes keeps it in rotation and the load balancer keeps sending it traffic. The system believes it is healthy; users experience errors and latency. This is 'differential observability' — the observer that matters (the client) sees something different from the observer that decides (the probe). The fixes are all about observing from the right vantage point: deep health checks that exercise real dependencies, RED metrics measured on live traffic, SLO burn-rate alerts, and, most important, Istio outlier detection, which ejects a host from the pool when it returns consecutive errors, regardless of what its health check claims. This ties directly to section 11.

## [233] APPENDIX M · LOAD · Amplification loops & retry storms (sldId 488)

A failure triggers retries, which add load, which cause more failures. Backoff, jitter and retry budgets break the loop.

p. 206

> See the diagram notes. Amplification is a positive feedback loop: the system's own defensive behaviour (retrying) becomes the attack. Two compounding effects. First, retry multiplication across layers: if the gateway retries 3x, and it calls a service that retries 3x, which calls a service that retries 3x, one user request becomes 27 requests to the bottom of the stack. Second, synchronisation: every client that failed at the same moment retries at the same moment, creating a thundering herd. The result can be metastable — the system stays collapsed even after the original trigger is gone, because the retry load alone sustains the failure. Breaking it: exponential backoff with jitter (de-synchronise), retry budgets (cap retries to a small percentage of live traffic so they can never multiply unboundedly), retry at exactly one layer, and circuit breakers to stop the doomed calls entirely. This is the failure mode most often caused by well-intentioned resilience code.

## [234] APPENDIX M · LOAD · Cascading failure (sldId 489)

One component's failure overloads its neighbours, which fail in turn — the domino effect up the call graph.

p. 207

> See the diagram notes. Cascading failure is how a single slow dependency takes down an entire system. The mechanism: a slow database causes the calling service's request threads (or async tasks, or connection pool) to fill up waiting; with its resources exhausted, that service now fails or slows for all callers, not just the ones touching the database; its callers' resources then fill up waiting on it; and so on up the graph until the user-facing edge is down. The amplifiers are synchronous call chains and unbounded resources (unbounded queues, unbounded thread pools, no timeouts). Each defensive pattern breaks one link: timeouts stop threads blocking forever; bulkheads isolate the pool so the database calls can't consume all of it; circuit breakers stop calling the slow dependency entirely; load shedding rejects excess work at the edge before it propagates. This is the failure mode bulkheads (section 12) were invented for.

## [235] APPENDIX M · The defensive toolkit — patterns and what they buy (sldId 490)

- Timeout + deadline propagation — never wait forever; pass the remaining budget downstream so nobody does doomed work. Defends: partial, cascading.
- Retry with backoff + jitter — ride out transient failures without building a storm; only for idempotent calls; use a retry budget. Defends: partial, amplification (if done right).
- Circuit breaker — stop calling a failing dependency; fail fast; test for recovery. Defends: cascading, amplification, gray.
- Bulkhead (§12) — isolate resources by tenant/call/priority so one failure can't starve the rest. Defends: partial, cascading.
- Load shedding — when overloaded, reject excess early (503) rather than collapsing. Defends: amplification, cascading.
- Quorum / consensus — majority-required action; the only real answer to split-brain. Defends: partition, split-brain.
- Fallback / graceful degradation — return a useful degraded response (cache, default, queue-for-later) instead of an error. Defends: partial, gray.
- Istio mesh policies + graceful shutdown + observability: the platform layer underneath all of these patterns. Each one gets code, and a matrix maps patterns to modes.

p. 208

> The toolkit overview before the deep dives. Each line names a pattern and the failure modes it defends against — this is the verbal version of the closing matrix. The thing to stress: no pattern is sufficient alone, and several patterns interact (retry without a circuit breaker amplifies; a circuit breaker without a fallback just fails faster; bulkheads without timeouts still let threads block within a pool). Production resilience is the composition of several of these, tuned together. Each gets its own diagram and per-language code so developers can implement them; the bold line flags that the platform-level pieces (Istio, shutdown, observability) sit underneath the application-level patterns.

## [236] APPENDIX M · TIMEOUTS · Timeouts + deadline propagation (sldId 491)

Every remote call needs a timeout; the remaining budget should travel downstream so nobody does doomed work.

p. 209

> See the diagram notes. Two ideas. First, every remote call must have a timeout — the default in many HTTP clients is infinite, which is how a single slow dependency hangs a whole service. Second, deadline propagation: the original deadline (say 1000ms) travels with the request, and each hop subtracts the time it has used and passes the remainder downstream. When the remaining budget is too small to plausibly finish, the downstream fails immediately rather than starting work that will be thrown away. gRPC does this natively with deadlines; for HTTP you pass a deadline header and honour it. The waste this prevents is real: without it, your database spends 500ms on a query for a request the user abandoned 450ms ago, and that wasted work is exactly what tips an overloaded system over. The code example shows the language-specific mechanics.

## [237] APPENDIX M · TIMEOUTS · Timeouts + deadlines (sldId 492)

[chip] java · Quarkus + REST Client

```java
// examples/26-failure-modes/quarkus/edge-service (condensed excerpts)
// application.properties: every call through the REST client gives up after 2 s
//   quarkus.rest-client.backend.read-timeout=2000
@GET
@Path("with-deadline")
public Map<String, Object> withDeadline(
        @RestQuery("budget_ms") @DefaultValue("1000") int budgetMs) {
    int remaining = budgetMs - 50;                         // edge overhead
    if (remaining < 50) {                                  // too little to finish
        return Map.of("error", "deadline_exceeded", "reason", "insufficient budget at edge");
    }
    // The budget is per request, so this client gets its own read timeout.
    BackendClient budgeted = QuarkusRestClientBuilder.newBuilder()
            .baseUri(URI.create(backendUrl))
            .readTimeout(remaining, TimeUnit.MILLISECONDS)
            .build(BackendClient.class);
    var response = budgeted.process(String.valueOf(remaining));   // sent as X-Deadline-Ms
    return Map.of("status", response.getStatus(), "body", response.readEntity(Map.class));
}
```

p. 210

> Two layers, from examples/26. The REST client's read timeout in application.properties bounds every call to the backend at 2 seconds. The deadline endpoint subtracts the edge's overhead from the caller's budget, refuses at once when too little remains, and otherwise builds a client whose read timeout is the remaining budget and sends that number in the X-Deadline-Ms header, so the backend can refuse work it cannot finish.

## [238] APPENDIX M · RETRY · Retry with exponential backoff + jitter (sldId 493)

Retry transient failures — but spread retries with exponential backoff + jitter, cap them, and only for idempotent calls.

p. 211

> See the diagram notes. Retry is the most abused resilience pattern because the naive version (retry immediately, a fixed number of times, at every layer) is precisely how you build the amplification storm from the amplification-loop discussion. The correct version has four properties: exponential backoff (each retry waits longer: 100ms, 200ms, 400ms), jitter (add randomness so clients don't synchronise), a cap on both attempts and total time, and a retry budget (retries may never exceed, say, 10% of live traffic). And it only applies to idempotent operations — retrying a non-idempotent POST without an idempotency key can double-charge a customer. Always pair retry with a circuit breaker so that once a dependency is clearly down, you stop retrying entirely. The code example shows the idiomatic library for each language.

## [239] APPENDIX M · RETRY · Retry with backoff + jitter (sldId 494)

[chip] java · Quarkus + SmallRye Fault Tolerance

```java
// examples/26-failure-modes/quarkus/edge-service: Backend.java (excerpt)
// The annotations are CDI interceptors: the resource calls through this bean.
@ApplicationScoped
public class Backend {
    /** Retried on a 5xx or a timeout: 3 attempts, 100 ms doubling to 2 s, 50 ms jitter. */
    @Retry(maxRetries = 2, delay = 100, jitter = 50,
            retryOn = {WebApplicationException.class, ProcessingException.class})
    @ExponentialBackoff(factor = 2, maxDelay = 2000)
    public Response processWithRetry(AtomicInteger attempts) {
        attempts.incrementAndGet();          // reported by /with-retry
        return client.process();             // a 4xx or 5xx throws WebApplicationException
    }
}
```

p. 212

> SmallRye Fault Tolerance, the MicroProfile implementation in Quarkus. @Retry sets two retries after the first attempt, a 100 ms delay with up to 50 ms of jitter, and the exceptions that count; @ExponentialBackoff doubles the delay up to 2 seconds. The annotations are CDI interceptors, so they only apply when another bean calls the method, which is why the example keeps them on a Backend bean that the REST resource calls. Retry only idempotent calls, and pair the retry with a circuit breaker.

## [240] APPENDIX M · CIRCUIT BREAKER · Circuit breaker — the state machine (sldId 495)

Closed → Open (fail fast) → Half-Open (test) → Closed. Stops doomed calls; gives the dependency room to recover.

p. 213

> See the diagram notes. The circuit breaker is the pattern that most directly stops cascading and amplification. Three states. CLOSED: calls pass through, failures are counted over a rolling window. When the failure ratio crosses the threshold, the breaker trips to OPEN: calls fail immediately without even attempting the downstream, which both gives a fast answer to the caller and gives the struggling dependency room to recover instead of being hammered. After a reset timeout the breaker goes HALF-OPEN: it allows a few trial calls; if they succeed it closes (recovered), if they fail it re-opens. Crucial details: one breaker per dependency (never a single global breaker), and pair it with a fallback so that an open breaker degrades gracefully rather than just erroring faster. Libraries differ per language; the code example shows each.

## [241] APPENDIX M · CIRCUIT BREAKER · Circuit breaker + fallback (sldId 496)

[chip] java · Quarkus + SmallRye Fault Tolerance

```java
// examples/26-failure-modes/quarkus/edge-service: Backend.java (condensed excerpt)
/** 5 failed calls open the breaker for 10 s; 2 successful trial calls close it. */
@CircuitBreaker(requestVolumeThreshold = 5, failureRatio = 1.0,
        delay = 10, delayUnit = ChronoUnit.SECONDS, successThreshold = 2)
@CircuitBreakerName("backend")              // /breaker-state reads CircuitBreakerMaintenance
@Fallback(fallbackMethod = "fallback")
public Map<String, Object> processWithBreaker() {
    return Map.of("source", "live", "body", client.process().readEntity(Map.class),
            "breaker", breakerState());
}
Map<String, Object> fallback(Throwable cause) {   // SmallRye passes the cause
    String reason = switch (cause) {
        case CircuitBreakerOpenException ignored -> "circuit_open";
        case WebApplicationException e -> "upstream_" + e.getResponse().getStatus();
        default -> "upstream_unreachable";
    };
    return Map.of("source", "fallback", "reason", reason, "breaker", breakerState());
}
```

p. 214

> SmallRye Fault Tolerance's @CircuitBreaker: five calls in the rolling window, all failed, open it for ten seconds, and two successful trial calls close it again. @CircuitBreakerName gives it the name that CircuitBreakerMaintenance reads for the breaker-state endpoint. @Fallback names a method that receives the cause, so the response says why it fell back: circuit_open when the breaker refused the call, upstream_<status> or upstream_unreachable when the call failed. One breaker per dependency.

## [242] APPENDIX M · BULKHEAD · Bulkhead — isolate so one failure can't sink the rest (sldId 497)

- Covered in depth in section 12 (Security) as a blast-radius pattern; it is equally a resilience pattern, so it appears here in the failure-mode context.
- Isolate resources (connection pools, thread pools, async semaphores, queues) by tenant, by call type, or by priority. A storm in one pool exhausts only that pool.
- Against cascading failure: if database calls have their own bounded pool, a slow database exhausts that pool and returns errors for DB-backed calls — but the service's other endpoints keep serving from their own pools.
- Against partial failure: a single misbehaving tenant or dependency is contained to its own compartment instead of consuming the shared resource.
- Implementation (from §12): SmallRye Fault Tolerance @Bulkhead — declarative concurrency + waitingTaskQueue caps, paired with @Timeout. At the mesh: Istio DestinationRule connectionPool gives the same isolation at the network layer.
  - Pair with timeouts: a bulkhead bounds how many calls run concurrently, but without a timeout those calls can still block forever and keep the bulkhead full. The two patterns need each other.

p. 215

> Bulkhead got full treatment in section 12, so here we just re-frame it in the failure-mode context and cross-reference. The key insight to land: a bulkhead bounds concurrency, but concurrency-bounding alone doesn't help if the bounded calls block forever — you must combine bulkhead (limit how many) with timeout (limit how long). Point back to section 12 for the per-language code (we don't repeat it here to save slides), and forward to the Istio slide for mesh-level bulkheading via connectionPool limits.

## [243] APPENDIX M · SHEDDING & FALLBACK · Load shedding and graceful degradation (sldId 498)

- Load shedding — when you are over capacity, reject excess work immediately (HTTP 503 + Retry-After) at the edge, before it consumes resources. A system that sheds 20% of load stays up for the other 80%; a system that accepts everything collapses for 100%.
- Shed by priority: drop health-check-style or low-value traffic first, protect revenue-critical paths. Adaptive concurrency limits (e.g. Netflix's, or Envoy's) shed automatically based on observed latency.
- Graceful degradation — when a dependency is unavailable, return a useful reduced response instead of an error: serve stale cache, omit the personalised section, queue the write for later, show a default recommendation.
- Degradation turns a hard failure into a soft one the user may barely notice. A product page that can't reach the reviews service should still show the product — just without reviews.
- Both are the application-level complement to the circuit breaker: the breaker decides to stop calling; the fallback decides what to return instead; load shedding decides what not to accept in the first place.
  - Reference §11: you cannot shed or degrade intelligently without observability — you shed based on measured saturation, and you alert when degradation rates climb.

p. 216

> Two related patterns that often get skipped. Load shedding is counter-intuitive to engineers, because rejecting requests feels like giving up, but it is the difference between a system that degrades and one that collapses. The maths is simple: if you are at 120% of capacity and accept everything, everything is slow and timing out (0% goodput); if you shed the excess 20%, the 80% you accept is served well. Adaptive limiters do this automatically based on latency. Graceful degradation is the product-level decision about what to return when you can't return everything — it requires the product/design team's input on what's essential vs nice-to-have. The bold line ties shedding, breakers and fallback together as a system: stop accepting (shed), stop calling (break), return something useful (fall back).

## [244] APPENDIX M · ISTIO · Istio — resilience at the mesh layer (sldId 499)

Timeouts, retries, outlier detection (gray-failure ejection) and circuit breaking — uniform, config-driven, no app code.

p. 217

> See the diagram notes. The service mesh gives you a large slice of the resilience toolkit without writing code in every service, in every language. VirtualService configures per-route timeouts and retries (with Envoy adding backoff and jitter automatically, and retryOn conditions controlling which failures are retried). DestinationRule configures connectionPool limits (mesh-level bulkheading) and outlierDetection — which is the mesh's answer to gray failure: it watches each host, and when one returns consecutive errors it ejects that host from the load-balancing pool for a cooldown period, regardless of what the host's own health check claims. That is exactly the gray-failure defence the health-check can't provide. The important discipline: don't double up. If Istio is retrying, don't also retry in the app (that's amplification). Decide where each concern lives — typically: timeouts and outlier detection at the mesh, business-aware retries and fallbacks in the app.

## [245] APPENDIX M · SHUTDOWN · Graceful shutdown (see App. H) (sldId 500)

[chip] java · Quarkus + SmallRye Health

```java
// application.properties + ShutdownState + DrainReadinessCheck, examples/21-graceful-shutdown
// quarkus.shutdown.delay-enabled=true, quarkus.shutdown.delay=5S, quarkus.shutdown.timeout=20s
// 1. SIGTERM: Quarkus fires ShutdownDelayInitiatedEvent and keeps serving for the delay
void onDelayInitiated(@Observes ShutdownDelayInitiatedEvent event) {     // ShutdownState
    shuttingDown.set(true);       // readiness flips: /readyz answers 503, /healthz stays 200
}
// 2. the delay keeps serving while the load balancer stops routing
// 3. delay over: HTTP stops, in-flight requests drain, ShutdownEvent fires
void onShutdown(@Observes ShutdownEvent event) {
    Log.infof("shutting down HTTP server (in_flight=%d)", inFlight.get());
}
// 4. Quarkus closes the pools and the process exits
@Readiness @ApplicationScoped              // DrainReadinessCheck: /readyz = this + datasource
public class DrainReadinessCheck implements HealthCheck {
    public HealthCheckResponse call() {
        var builder = HealthCheckResponse.named("drain");
        return shutdownState.isShuttingDown()
            ? builder.down().withData("reason", "shutting down").build()
            : builder.up().build();
    }
}
```

p. 218

> Example 21 lets Quarkus run the drain: quarkus.shutdown.delay-enabled, quarkus.shutdown.delay and quarkus.shutdown.timeout. On the single SIGTERM: (1) Quarkus fires ShutdownDelayInitiatedEvent and an observer flips the ShutdownState flag, so the SmallRye Health readiness check reports DOWN, /readyz answers 503 and Kubernetes stops routing new traffic, while /healthz stays 200; (2) the delay keeps the service serving, so the load balancer's removal propagates; (3) when it ends, Quarkus stops HTTP and drains in-flight requests within quarkus.shutdown.timeout (20 s); (4) Quarkus closes the datasource and the process exits. Appendix H covers the Kubernetes-side preStop and terminationGracePeriodSeconds.

## [246] APPENDIX M · OBSERVE · Observing failure modes (see §11) (sldId 501)

- Network partition — watch peer-connectivity and cross-zone error metrics; alert on quorum-loss events from etcd / your datastore.
- Split-brain — alert on more-than-one-leader conditions, divergent-replica metrics, and fencing-token rejections in logs.
- Partial failure — RED metrics per dependency (rate, errors, duration), not just per service. A spike in errors to one downstream is the early signal.
- Gray failure — the hard one: compare health-check status against real-traffic SLOs. Latency percentiles (p99) diverging from the average, and Istio outlier-ejection counts, are your tells.
- Amplification — watch request-rate against user-action-rate (if requests >> actions, retries are multiplying), retry-count metrics, and goodput falling while load rises.
- Cascading — a distributed trace shows the error spreading service-to-service; saturation metrics (thread pools, queue depth, connection pools) climb together across services.
  - The unifying tool is the trace_id from §11: when an alert fires, pivot from the metric to an exemplar trace to its logs to find which leg failed first and how it spread.

p. 219

> Tie the appendix back to section 11. Each failure mode has characteristic signals, and you must instrument for them explicitly: a default dashboard of CPU and memory will not show you a gray failure or an amplification loop. The most important specific guidance: measure RED per dependency (so partial failures are visible), compare health-check status to real-traffic SLOs (so gray failures are visible), and watch request-rate vs user-action-rate (so amplification is visible). The sub-bullet is the workflow: the trace_id is what lets you pivot from 'something is wrong' (a metric) to 'here is the request that shows it' (a trace) to 'here is what failed' (the logs on that trace), the correlation story from section 11 applied to incident response.

## [247] APPENDIX M · Which pattern addresses which failure mode (sldId 502)

Read a row to defend a failure mode; read a column to see what a pattern buys you. Production layers several.

p. 220

> The synthesis slide — if the audience keeps one thing, keep this. Reading across a row tells you the portfolio of patterns that defend a given failure mode (e.g. cascading failure is addressed by timeouts, circuit breakers, bulkheads, load shedding, and graceful shutdown together). Reading down a column tells you what a given pattern buys you across failure modes. Two observations: first, quorum/consensus is the only real answer to split-brain; no amount of retrying or circuit-breaking helps when the problem is two leaders, so you need a majority rule. Second, almost every other cell is about assembling a portfolio — there is no single pattern that handles partial, gray, amplification and cascading failures; you layer timeouts, retries-with-budget, breakers, bulkheads, shedding and fallbacks, and you observe the result. Defence in depth, exactly as in the security section, applied to reliability.

## [248] APPENDIX M · Take-aways and references (sldId 503)

- Design for partial failure from the start: every remote call can succeed, fail, hang, or lie. Timeout everything; the default is often infinite.
- Retry only idempotent calls, with backoff + jitter + a budget, at one layer, always paired with a circuit breaker. Naive retries cause the outages they were meant to prevent.
- Bound the blast radius: bulkheads isolate, circuit breakers stop the bleeding, load shedding protects capacity, fallbacks keep the user served.
- Quorum is the only cure for split-brain. Let etcd / Raft / your datastore handle consensus; don't invent your own.
- Push uniform concerns (timeouts, outlier detection, mesh bulkheads) to Istio; keep business-aware concerns (fallbacks, idempotency) in the app. Don't double-retry.
- Observe from the client's vantage point (RED per dependency, SLOs, outlier ejections) — gray failures are invisible to naive health checks. Drain on shutdown (App. H).
  - References: Google SRE Book (chapters on Addressing Cascading Failures, Handling Overload); 'Release It!' (Nygard — circuit breaker, bulkhead origin); the gRPC retry design, gRFC A6 (retry policy, backoff with jitter, retry throttling); Istio traffic-management docs; the metastable-failures research (Bronson et al., 2021).

p. 221

> Close the appendix and, since it's the last appendix, effectively close the deck's technical content. The take-aways are the imperatives: design for partial failure, timeout everything, retry carefully, bound the blast radius, use quorum for consensus, split concerns between mesh and app, and observe from the client's perspective. The references are the canonical sources: the Google SRE book's cascading-failures and overload chapters are the single best free resource; Michael Nygard's 'Release It!' is where the circuit breaker and bulkhead patterns were named for software; the gRPC retry design (gRFC A6) writes retry policy, backoff with jitter and retry throttling down as a protocol; and the metastable failures paper (Bronson et al.) is the modern formalisation of amplification loops. Encourage the audience to read the SRE cascading-failures chapter as the next step.

## [249] Feature Flags (sldId 504)

N

Progressive delivery, decoupled from deploy — OpenFeature + flagd

> This appendix adds the runtime switch that separates shipping code from releasing a feature. It is a deep-dive you keep open when you are about to roll something out gradually. The whole section is built on two CNCF, open-source projects - OpenFeature for the vendor-neutral SDK and flagd for the backend - so it runs on plain Kubernetes with no managed SaaS, like every other example in the book. The arc: why deploy is not release, the four kinds of flag, how evaluation works, the code to evaluate and target and roll out, flags as a control plane over patterns we already covered, and the lifecycle discipline that keeps flags from becoming debt.

## [250] APPENDIX N · FEATURE FLAGS · Deploy is not release (sldId 505)

p. 222

the artifact ships dark; releasing is a runtime flag flip — and so is rollback

> The reframe that makes everything else work: deploying an artifact and releasing a feature are different events, and a flag is what splits them. The artifact ships to production with the new path turned off - a non-event, visible only in the deploy log. Releasing is then a runtime flag flip: on for one percent, then a wider cohort, then everyone, each step reversible by narrowing the flag rather than rolling back a deployment. This is what lets a team merge to main many times a day yet release on its own cadence, and it is the mechanism behind every canary and every safe cutover in the book. Rollback stops being a redeploy and becomes a config change measured in seconds.

## [251] APPENDIX N · FEATURE FLAGS · Four kinds of flag (sldId 506)

p. 223

by lifetime and owner — each wants different defaults and lifecycle

> Feature flag covers four different tools, and conflating them is the root of most flag messes. They differ along two axes - how long the flag lives, and who decides to flip it. Release flags are temporary and developer-owned: they ship new code dark, ramp it, and are then removed. Experiment or A/B flags are temporary and data-owned: they split traffic across variants so a metric can be measured, and they require sticky assignment. Ops or kill-switch flags are long-lived and SRE-owned: a permanent control to disable a feature or dependency fast under load or incident. Permission or entitlement flags are long-lived and product-owned: they gate functionality by plan, tier, or region. The defaults differ too - a release flag fails off, so half-shipped code stays dark, while a kill-switch usually fails on, so the feature survives a flag-system outage.

## [252] APPENDIX N · FEATURE FLAGS · Evaluating a flag: OpenFeature + flagd (sldId 507)

p. 224

local evaluation, vendor-neutral SDK, fail-safe to the default

> Evaluation should not couple your code to a vendor. OpenFeature is the CNCF vendor-neutral API standard - one SDK surface across languages - and flagd is its lightweight open-source backend that evaluates flags from a file, ConfigMap, or synced source, in-cluster. Together they keep the whole feature-flag story open-source and running on plain Kubernetes, with no managed SaaS, and swapping flagd for another provider later is a configuration change, not a code change. Two properties matter most. First, evaluation returns the default if the provider is unreachable - a flag-system outage must never take the application down. Second, the SDK is vendor-neutral: the app calls getBooleanValue with a flag key, a default, and an evaluation context, and never names the backend. The context carries the targeting inputs - a stable key plus attributes like plan and region - that the rules act on.

## [253] APPENDIX N · FEATURE FLAGS · Evaluating a flag (sldId 508)

p. 225

[chip] java · Quarkus

```java
// OpenFeature SDK 1.23.0 + flagd provider 0.14.2 (as examples/27-feature-flags)
// startup: register the provider once (flagd.host / flagd.port from config)
void onStart(@Observes StartupEvent ev) {
  OpenFeatureAPI.getInstance().setProvider(new FlagdProvider(
      FlagdOptions.builder().host(flagdHost).port(flagdPort).build()));
}
@Path("/checkout")
public class CheckoutResource {
  @POST
  public Receipt checkout(Cart cart, @RestHeader("X-User") String user) {
    Client flags = OpenFeatureAPI.getInstance().getClient();
    var ctx = new MutableContext(user)           // targeting key
        .add("plan", cart.plan()).add("region", cart.region());
    boolean useNew = flags.getBooleanValue("new-checkout", false, ctx);
    return useNew ? newCheckout(cart) : legacyCheckout(cart);
  }
}
```

The same one line of code serves an on/off, a per-plan entitlement, or a 25% rollout.

> The provider is registered once at startup; from then on the application asks the client for a value. The crucial thing to notice is that the application code is the same one line regardless of whether the flag is a simple on/off, a per-plan entitlement, or a 5 percent rollout. All of that lives in the flag's configuration, not the code. The default is what gets returned if flagd is unreachable, so the new path stays dark on a flag-system outage rather than erroring. The targeting key is the user id, which is what makes a percentage rollout sticky. Across every language the shape is identical: register a flagd provider, get a client, build an evaluation context with a targeting key and attributes, and call getBooleanValue with a safe default.

## [254] APPENDIX N · FEATURE FLAGS · Targeting and rollout live in config (sldId 509)

p. 226

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

## [255] APPENDIX N · FEATURE FLAGS · Percentage rollout via sticky bucketing (sldId 510)

p. 227

consistent per-user assignment; instant ramp and rollback

> Sticky bucketing matters for two reasons. For a rollout, it prevents flicker - a user who got the new checkout on their first visit keeps getting it, rather than bouncing between variants on refresh. For an experiment, it is a correctness requirement: a user must stay in one arm of the test for the measurement to mean anything. The mechanism is simple - hash a stable key, the user id, into a bucket from 0 to 99, and compare it to the rollout threshold. Because the hash is stable, the same user always lands in the same bucket. Ramping the rollout is moving the threshold up; rolling back is moving it down, and both take effect in the running fleet within the sync interval with no deploy on the path of either.

## [256] APPENDIX N · FEATURE FLAGS · A kill switch (sldId 511)

p. 228

[chip] java · Quarkus

```java
// ops kill-switch - default true (fail open): on until an operator kills it
Recommendations recommend(String user) {
  if (!flags.getBooleanValue("recommendations-enabled", true, ctx(user)))
    return Recommendations.empty();        // degrade - still serve the page
  return recsClient.fetch(user);           // pairs with a circuit breaker
}
```

Default true = fail open: only an operator flipping the flag disables it. The default flips with the flag type.

> A kill switch is the operational flag you reach for during an incident: wrap a risky or expensive dependency in a flag so it can be disabled instantly without a deploy. It is the human-driven complement to the circuit breaker from the Failure Modes appendix - the breaker trips automatically on errors; an operator flips the kill switch by hand. The default flips with the flag type: a release flag defaults off so half-shipped code stays dark, while this kill switch defaults true, fail-open, so the feature survives a flag-system outage and only an explicit flip removes it. When it is killed, the page still renders - just without the recommendations - which is graceful degradation, the same idea as the load-shedding discussion in the Failure Modes appendix.

## [257] APPENDIX N · FEATURE FLAGS · Flags over the patterns you already have (sldId 512)

p. 229

a flag is a runtime control surface

> Feature flags are not a new subsystem so much as a runtime control plane over patterns already in this book. A canary is a percentage flag deciding which build a request exercises, often paired with the L7 routing from the routing appendix. A strangler-fig cutover is a flag, or the proxy's percentage, steering a widening slice from the monolith to the extracted service. A saga step can be guarded by a flag to switch a new compensation path on cautiously. And an experiment is a sticky-bucketed variant flag with a metric attached. Recognising flags as the control surface for all of these keeps you from building a bespoke mechanism for each - the same decoupling, expressed four ways.

## [258] APPENDIX N · FEATURE FLAGS · The flag lifecycle (sldId 513)

p. 230

a release flag is born with a removal ticket

> The failure mode of feature flags is not technical, it is organisational: flags that are never removed. Every flag is a branch in your code and a dimension in your test matrix, and a stale one is dead code, a hidden conditional, and a live risk surface that nobody remembers the meaning of. The discipline that keeps it healthy: give every release flag an owner and an expiry from the moment it is created, and treat removing it as part of finishing the feature, not optional cleanup. Long-lived ops and entitlement flags are exempt - they are permanent by design - which is exactly why distinguishing the four types matters. A short-lived flag that has been at 100 percent for two weeks should be deleted along with the branch it guarded.

## [259] APPENDIX N · FEATURE FLAGS · Testing, observing, and anti-patterns (sldId 514)

p. 231

  - Test both sides of every flag you depend on - a suite that only hits the default path misses the bug behind the flag.
  - Put the resolved variant on your telemetry - a span attribute and a metric label - so a latency or error change attributes to a specific flag and cohort.
- Anti-patterns: flags as a config store; release flags that never die; stacks of flags whose combinations no one reasons about; experiments without sticky assignment; business logic buried in flag rules.

> A flag multiplies the states your system can be in, so test both sides of every flag you depend on; a test suite that only exercises the default path will not catch a bug behind the flag. Keep the number of simultaneously interacting flags small, and default flags off in test environments unless a test sets them explicitly. Observability ties flags back to the Observability section: record the resolved variant as a span attribute and a metric label, so a latency or error change can be attributed to a specific flag and cohort. The recurring anti-patterns: using flags as a general configuration store - they are for release control, not for tuning timeouts; letting release flags become permanent; stacking many flags whose combinations no one reasons about; running experiments without sticky assignment, which makes the data meaningless; and putting real business logic inside flag rules instead of in code.

## [260] APPENDIX N · FEATURE FLAGS · Take-aways (sldId 515)

p. 232

- Decouple deploy from release: ship dark, release gradually, roll back by narrowing a flag.
- Distinguish the four flag types - they want different owners, defaults, and lifecycles.
- Evaluate through a vendor-neutral SDK (OpenFeature) against an OSS backend (flagd), always with a safe default.
- Keep targeting and rollout in configuration, not code, and make percentage rollouts sticky.
- Treat release flags as debt with a removal ticket; put the resolved variant on your telemetry.

References: OpenFeature spec & flagd docs (CNCF) · Hodgson, “Feature Toggles” · Accelerate / DORA · Unleash (OSS alternative).

> Close on the imperatives. Decouple deploy from release: ship dark, release gradually, roll back by narrowing a flag. Distinguish the four flag types, because they want different owners, defaults, and lifecycles. Evaluate through a vendor-neutral SDK against an open-source backend, always with a safe default so a flag outage cannot take the app down. Keep targeting and rollout rules in configuration, not code, and make percentage rollouts sticky. Treat release flags as debt with a removal ticket attached, and put the resolved variant on your telemetry so you can attribute a regression to a cohort. The canonical references are the OpenFeature specification and the flagd documentation, Pete Hodgson's Feature Toggles article for the taxonomy of flag types, and the Accelerate and DORA research for the deploy-versus-release distinction; Unleash is a capable open-source alternative backend behind the same OpenFeature SDK.

## [261] API Testing with Newman (sldId 516)

O

Postman collections as an automated gate on Docker Engine

> This appendix turns the Postman collections the team already pokes at by hand into an automated test gate, using Newman, Postman's command-line runner. It is a deep-dive you keep open when you are wiring API tests into CI. The key idea that makes it cheap: Newman tests the API as a black box over HTTP, so one collection is the conformance suite for every implementation in the book, and the only language-specific step is bringing the service under test up. The arc: why Newman, the anatomy of a collection, one collection against six backends, running it and shaping the output, data-driven cases, the CI gate on Docker Engine, and where Newman sits in the test pyramid.

## [262] APPENDIX O · API TESTING · Why Newman (sldId 517)

p. 233

the headless runner turns a Postman collection into CI-readable results

> A Postman collection is an executable contract, not just a saved list of requests. Newman runs it without the GUI and emits machine-readable results: a cli reporter for a human watching, a junit reporter that CI turns into a test report, and an html reporter to share. There is no new test framework to learn - the tests are the JavaScript assertions already supported inside Postman, and Newman is the bridge from works-when-I-click-it to verified-on-every-pull-request. The same file serves three audiences: a developer in Postman, a reviewer reading the tests, and a pipeline failing the build when an assertion breaks.

## [263] APPENDIX O · API TESTING · Anatomy of a collection (sldId 518)

p. 234

folders of requests, each with assertions; the environment supplies the variables

> A collection nests folders and requests; each request can carry a pre-request script, the HTTP call itself, and a block of tests that run against the response. The tests are small JavaScript blocks using Postman's pm API - asserting the status, the response time, the shape of the body. Environment variables supply the parts that change between runs, like the base URL and an auth token, resolved at run time. Storing a value from one response - a new order id - in a variable lets a later request chain off it, which is how a collection models a whole flow rather than isolated calls.

## [264] APPENDIX O · API TESTING · Tests live in the request (sldId 519)

p. 235

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

## [265] APPENDIX O · API TESTING · One collection, six backends (sldId 520)

p. 236

Newman tests over HTTP, so one collection validates every implementation

> Because Newman exercises the API as a black box over HTTP, the collection does not know or care which language implements the service. The same collection is the conformance suite for every implementation in this book - point it at whichever service is running and the assertions are identical. The collection is the API specification made executable. Bringing the service under test up is the only language-specific step; the Newman command that follows is the same everywhere.

## [266] APPENDIX O · API TESTING · Launch the service under test (sldId 521)

p. 237

[chip] bash · Quarkus

```bash
# Quarkus — dev mode, then the same collection
./mvnw quarkus:dev &               # http://localhost:8080
newman run orders.postman_collection.json -e local.postman_environment.json
```

Only this step is language-specific; the Newman command is identical for all six.

> The only per-language step is starting the service. Each implementation exposes the same HTTP API on the same port, so the base URL in the environment file is identical and the Newman command that follows does not change. That is the point of black-box testing: bring up Spring Boot, Quarkus, .NET, Python, C++ or Go, and run the same collection against it. In CI the services start with docker compose up -d --build --wait instead of a foreground command; locally, a background process and a newman run is the fastest loop.

## [267] APPENDIX O · API TESTING · Running Newman & shaping output (sldId 522)

p. 238

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

## [268] APPENDIX O · API TESTING · Data-driven tests (sldId 523)

p. 239

one request set, many inputs — boundary values and negative cases from a table

> Data-driven testing runs the same requests once per row of a CSV. The columns become variables in the requests, and a column can carry the expected status so a single assertion checks status against the row's expectation. This is how a handful of requests becomes broad coverage: the happy path, a zero-quantity order that must be rejected with a 422, an over-stock order that must also be rejected - all without copy-pasting requests. Keeping the cases in data rather than in duplicated requests is what makes the suite maintainable as the API grows.

## [269] APPENDIX O · API TESTING · Newman in CI (sldId 524)

p. 240

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

## [270] APPENDIX O · API TESTING · The gate on Docker Engine (sldId 525)

p. 241

the same stack you run locally, gating every pull request

> The full gate: a pull request builds the image, docker compose brings the order, payment, and inventory services up, Newman runs the collection against them, and the result gates the merge: pass merges, fail blocks. The important property is parity: the stack in CI is the stack you run locally, on the same Docker Engine, so a green run in CI means the contract holds against the running services rather than a mock.

## [271] APPENDIX O · API TESTING · Where Newman fits (sldId 526)

p. 242

the API/contract tier: on top of unit tests, under a thin end-to-end layer

> Newman does not replace unit tests; it is the layer on top of them. It owns the API/contract tier: real HTTP against a running service, fast enough to run on every pull request. Keep the base of fast unit tests broad, use Newman for the contract and integration behaviour that only shows up over real HTTP, and reserve a thin layer of full end-to-end tests for the few user flows that need the whole system. Pushing everything into Newman makes a slow, brittle suite; ignoring it leaves the contract untested. Test the failure paths as carefully as the happy path: a 401 with WWW-Authenticate, a 403, a 409 or 422 on a business rule, a 429 with RateLimit headers, and idempotency by sending the same key twice. Those cases tie this appendix back to the error-format, security, idempotency, and rate-limiting material.

## [272] APPENDIX O · API TESTING · Take-aways (sldId 527)

p. 243

- Treat the Postman collection as the executable specification - Newman runs it headlessly to guard every change.
- One collection is the conformance suite for all six implementations: Newman tests over HTTP, as a black box.
- Validate response shape against a schema, not just status codes; drive edge cases from data, not duplicated requests.
- Assert the failure paths - 401, 403, 409/422, 429, idempotency - as carefully as the happy path.
- Gate CI on plain Docker Engine so the build fails on a broken contract; keep Newman in the API/contract tier.

References: Postman docs & Newman CLI docs (reporters, --iteration-data, --bail) · Postman Learning Center (pm API, JSON-schema validation).

> Close on the imperatives. Treat the Postman collection as the executable specification of your API, and let Newman run it headlessly so the same assertions guard every change. Because Newman tests over HTTP, one collection is the conformance suite for all six implementations. Validate response shape against a schema, not just status codes; drive edge cases from data rather than duplicated requests; and assert the failure paths as carefully as the happy path. Wire it into CI on plain Docker Engine so the build fails on a broken contract, and keep Newman in its lane: the API/contract tier, on top of unit tests and under a thin end-to-end layer. The references are the Postman documentation and the Newman command-line documentation, and the Postman Learning Center guides on writing tests with the pm API and on JSON-schema validation.

## [273] Example 05 on minikube (sldId 528)

R

The same services and the same verify.sh on a single-node Kubernetes cluster

> Appendix R takes Example 05, the event-driven fan-out, from docker compose to a single-node Kubernetes cluster on minikube, in all six languages, and records what changed. Compose proves the code; a cluster adds questions compose never asks: where configuration and credentials live, how a service finds a broker that an operator manages, what restarts a process that exits, and how a request from the host reaches a pod.
>
> The arc: the runtime, the topology, the compose-to-Kubernetes mapping, one overlay per language, how images get into the node, how to run it, and the recorded results.

## [274] APPENDIX R · MINIKUBE · From compose to a cluster (sldId 529)

p. 244

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

## [275] APPENDIX R · MINIKUBE · The minikube runtime (sldId 530)

p. 245

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

## [276] APPENDIX R · MINIKUBE · One node, two namespaces (sldId 531)

p. 246

The node container holds two namespaces; the host reaches two loopback NodePorts and uses kubectl exec

> The topology. The node container cndp-k8s holds two namespaces: strimzi runs the Strimzi operator, and cndp-05 runs order-service, the shipping and notification consumers, a single-node KRaft Kafka cluster, Postgres 18, the LGTM stack and the Postgres Secret.
>
> From the host, curl and verify.sh reach order-service on 127.0.0.1:30080, a browser reaches Grafana on 127.0.0.1:30300, and kubectl exec runs the Kafka and Postgres checks inside their pods. Other minikube profiles stay stopped while this one runs.

## [277] APPENDIX R · MINIKUBE · Compose to Kubernetes (sldId 532)

p. 247

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

## [278] APPENDIX R · MINIKUBE · One overlay per language (sldId 533)

p. 248

[chip] yaml · kustomize

```yaml
# k8s/overlays/quarkus/kustomization.yaml (excerpt)
images:
  - name: order-service
    newName: localhost/cndp-05/quarkus-order-service
    newTag: v1
  # shipping-consumer and notification-consumer map the same way
# appended to each Deployment's environment by a JSON patch
- name: QUARKUS_DATASOURCE_JDBC_URL
  value: "jdbc:postgresql://cndp-postgres-rw:5432/appdb"
- name: QUARKUS_DATASOURCE_USERNAME
  value: "$(PG_USER)"
- name: QUARKUS_DATASOURCE_PASSWORD
  value: "$(PG_PASSWORD)"
- name: KAFKA_BOOTSTRAP_SERVERS
  value: "cndp-kafka-bootstrap:9092"
```

base/ is language-neutral; each overlay maps the images and appends the variables its language reads.

> The Quarkus overlay. The base Deployments are language-neutral: they run with a restricted security context (non-root, no privilege escalation, all capabilities dropped, RuntimeDefault seccomp, no fixed user ID), read PG_USER and PG_PASSWORD from the Secret, and point OTEL_EXPORTER_OTLP_ENDPOINT at the LGTM Service.
>
> Each overlay maps the three image names to localhost/cndp-05/<language>-<service>:v1 and appends the variables that language already reads in compose, so the application code is untouched. Kubernetes expands $(PG_PASSWORD) only if PG_PASSWORD is defined earlier in the list, which is why the credential variables sit in the base.

## [279] APPENDIX R · MINIKUBE · Images built on the host (sldId 534)

p. 249

docker build on the host, minikube image load into the node; pods never pull

> The cluster does not build images. Each service is built on the host with docker build, which keeps the host's BuildKit caches (a cold C++ build takes about half an hour), then copied into the node's containerd store with minikube image load.
>
> The Deployments set imagePullPolicy: Never, so a missing image fails fast with ErrImageNeverPull instead of trying a registry that does not have it. Tags are always v1; nothing uses latest.

## [280] APPENDIX R · MINIKUBE · Run it (sldId 535)

p. 250

[chip] bash · minikube

```bash
# from examples/05-event-driven/, with no other profile or container running
k8s/setup-profile.sh        # create cndp-k8s; check the published ports
k8s/build-images.sh quarkus # docker build, then minikube image load
k8s/deploy.sh quarkus       # Strimzi, Kafka, Postgres, LGTM, then the overlay
RUNTIME=kubernetes BASE=http://127.0.0.1:30080 ./verify.sh

# all six languages, a fresh namespace for each
OUT=/tmp/cndp-k8s-matrix k8s/verify-matrix.sh

# clean up: the namespace, the Strimzi release and its CRDs; then stop the profile
k8s/teardown.sh --operator
minikube stop -p cndp-k8s
```

With RUNTIME=kubernetes, verify.sh runs its container checks through kubectl exec; the ten checks are unchanged.

> The run, from the example directory. setup-profile.sh creates the profile and refuses to start while another profile or a container is running. build-images.sh builds and loads the three Quarkus images, and deploy.sh installs Strimzi, then Kafka, Postgres and LGTM, then the overlay.
>
> verify.sh is the file compose uses. Its container operations go through helper functions, and RUNTIME=kubernetes swaps them: the Kafka checks run in pod cndp-dual-role-0 and the Postgres checks in cndp-postgres-0.
>
> What to show: the ten check marks and the Results line, then Grafana on 127.0.0.1:30300. Fallback: the recorded results. teardown.sh never deletes the profile; minikube stop frees the memory and keeps the images.

## [281] APPENDIX R · MINIKUBE · Recorded results (sldId 536)

p. 251

- 10 passed, 0 failed in all six languages (Fedora 44, Docker Engine 29.8.2, minikube v1.39.0).
- Spring Boot 361 s · Quarkus 135 s · .NET 134 s · Python 116 s · C++ 103 s · Go 104 s.
- Tempo received traces from order-service, shipping-consumer and notification-consumer in every language.
- shipping-consumer scaled to 0: no shipment; back to 1: the group resumes from its committed offset.
- Stop the profile before starting compose or another cluster; the scripts refuse to run alongside them.

Times cover the image build and load, the deploy, the checks and the namespace teardown.

> The recorded run, 2026-10-11: every language passed all ten checks with a fresh namespace per language. After each run, verify-matrix.sh asked Tempo through the lgtm pod which services had sent traces, and all three services reported in every language.
>
> The scale-down check was run by hand: with the shipping consumer at zero replicas a new order produces no shipment; scaled back to one, the consumer group resumes from its last committed offset and the shipment appears. That is the event-driven contract from the Event-Driven section, observed on a cluster.

## [282] SCAN TO EXPLORE · Take it with you (sldId 537)

The site

The cloud-native design patterns, with runnable examples

Workshops & Tutorials

The whole series: every workshop, tutorial, and deck in one place

[chip] patterncatalyst.github.io/cloud-native-design-patterns

```patterncatalyst.github.iocloud-native-design-patterns
patterncatalyst.github.io/patterncatalyst-workshops-tutorials-list
```

p. 282

> That's the Quarkus edition end to end. Take it with you: on the left, the site, the cloud-native design patterns with runnable examples; on the right, the Workshops and Tutorials hub, every workshop, tutorial, and deck in the series in one place. Both are public on the Pattern Catalyst GitHub organization.
