# Designing-Cloud-Native-APIs-Cpp

Source: Designing-Cloud-Native-APIs-Cpp.pptx · 281 slides

## [001] CLOUD-NATIVE ARCHITECTURE · Designing Cloud-Native APIs (sldId 256)

From principles to a running system on Kubernetes — communication, composition, data, events, and the platform that governs them.

Robert Sedor

Chief Architect, Application Development

> Title slide. Same Red Hat brand frame as the other decks in the series. Talk track: this is the C++ entry in the Designing Cloud-Native APIs series. Like its siblings (Python/FastAPI, Java/Quarkus, Spring Boot, .NET 10, Go), it carries the same five-service running example end to end, and every line of code is idiomatic C++23.
>
> Toolchain: GCC 15 (gcc-toolset-15 on the ubi10/ubi:10.2 builder image), CMake 4.4.4 and Ninja 1.13.2 from the upstream release binaries, Conan 2.33.0 with a lockfile per project; libstdc++ is linked statically into a ubi10/ubi-minimal runtime image. Libraries: Drogon for REST and WebSocket, grpc++, librdkafka's C++ API (rdkafka++) for Kafka, libpq directly for Postgres, sw/redis++, cppgraphqlgen, OpenTelemetry C++ with spdlog. The examples run on Docker Engine with docker compose; Example 05 also runs on Kubernetes (Appendix R).

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

> The agenda: the same scope as the other decks in the series. A short setup, thirteen sections, the deep-dive appendices A to O, Appendix R and a glossary. Every section is shown in idiomatic C++23; the architecture and the running example are the same as in the other languages.
>
> Appendix R runs Example 05 on minikube with the same verify.sh as compose.
>
> Tell the audience which sections you will cover given the session length.

## [003] OVERVIEW · What we'll build, and the order we'll build it (sldId 258)

- Foundations — cloud-native principles and the canonical system we carry throughout
- Communications — REST, gRPC, GraphQL, and synchronous vs. asynchronous
- Composition & Data — gateways, federation, database-per-service, outbox, sagas
- Event-driven & Stream processing — the log, schemas, derived streams, KEDA scaling
- Workflows & Jobs — orchestration (Temporal as a service), choreography, batch and scheduled work
- The API platform — gateway, registry (Apicurio), metadata (OpenMetadata), observability
- Anti-patterns — and the heuristics that keep you out of them

p. 2

> Overview. Same ordering as the Python/Quarkus/Spring/.NET decks. Note one C++-specific framing already visible here: Temporal as an external service rather than an in-process SDK — there is no first-class C++ Temporal SDK, so we'll integrate via gRPC activity workers. We'll call this out explicitly when we get to Workflows.

## [004] SETTING UP · Why patterns matter more in the age of AI (sldId 259)

- AI tooling (Claude, Claude Code, frontier models) turns intent into code at a rate that was not possible before. The bottleneck shifted: it's no longer typing, it's knowing what to ask for and what to accept.
- Patterns are your vocabulary at three layers: design patterns (factory, strategy, observer), architecture patterns (hexagonal, microservices, event-driven), system design patterns (sagas, caching, strangler fig — the scope of this deck).
- Without that vocabulary you can't specify precisely, evaluate what comes back, tell good code from plausible-looking code, or notice when an anti-pattern is dressed as a solution. The AI is fluent; you still need to be literate.
- All architecture is the least-worst decision — every choice trades something away.
- All management is risk management — you manage the distribution of failures, not their existence.
- There is no such thing as a free lunch — every pattern has a cost; ask whether you can afford it.
- There is no problem which cannot be made worse — the wrong fix amplifies the original pain.

p. 3

> Patterns matter more under AI tooling. C++ raises the stakes here: AI tools can produce plausible-looking C++ that mismanages ownership, leaks resources, or relies on UB. Knowing the patterns, and the C++ idioms that implement them (RAII, value semantics, PMR arenas, ports & adapters), is what lets you accept or reject what a model proposes. The four maxims at the bottom carry across every deck in the series.

## [005] SETTING UP · Three layers of patterns literacy (sldId 260)

p. 4

> The three-layer model. Design patterns (Gang of Four etc.) are the code-level vocabulary; architecture patterns describe how applications fit together; system design patterns span services, data, and runtime — and they're the scope of this deck. C++ adds patterns at the bottom layer that managed-runtime languages do not have: RAII, value semantics, type erasure, CRTP. They are the vocabulary for arguing about ownership and lifetime with an AI tool.

## [006] THE RUNNING EXAMPLE · One system, carried end to end (sldId 261)

We will design every concern against these five services and a gateway — the same example, re-examined from each angle.

p. 5

> The canonical system. Five C++ services + a GraphQL gateway. Order, inventory, payment, shipping are full request/response services; notification is Kafka-consumer-only. Protocols differ per service by design: order-service exposes REST at the edge and calls others over gRPC; inventory/payment/shipping speak gRPC + GraphQL + Kafka; the gateway federates reads. For the C++ deck specifically: every backend service is a Drogon + gRPC C++ binary, the GraphQL gateway is shown both ways — as a cppgraphqlgen server in front of REST+gRPC, and as the simpler alternative of a Node/Apollo gateway over the same C++ backends. Apicurio (schema registry) and OpenMetadata (metadata) remain external seams, not in-process, the same posture every deck in the series takes.

## [007] Cloud-Native Principles (sldId 262)

01

Properties first, tools second.

> Section 01 divider: Cloud-Native
>
> Principles. Properties first, tools second.

## [008] CLOUD-NATIVE PRINCIPLES · Cloud-native is a set of runtime properties (sldId 263)

- Disposable — a process you can stop at any moment without data loss.
- Observable — every request emits correlated traces, metrics, logs.
- Resilient — failures are bounded; no single fault sinks the system.
- Elastic — capacity follows load, all the way to zero.
- Automatable — every change goes through code, not a console.
- Loosely coupled — services share contracts, not internals.
- If your API isn't disposable, observable, resilient, elastic, automatable and loosely coupled, the platform can't help it.

p. 6

> Cloud-native is properties, not tools. The same six properties show up in the CNCF definition, the 12-factor manifesto, Bilgin Ibryam's microservices patterns, and every major cloud vendor's framework. For C++ specifically: 'disposable' means the binary starts fast and exits cleanly under SIGTERM (RAII reverse-order teardown from main() — we'll come back to this in App. H). 'Observable' means the OpenTelemetry C++ SDK with the Batch span processor — never Simple, which collapses throughput. Elastic-to-zero is real in C++: a Drogon binary cold-starts in tens of milliseconds, which is what makes KEDA scale-to-zero workable.

## [009] CLOUD-NATIVE PRINCIPLES · The platform makes the properties the default (sldId 264)

- Kubernetes gives you the disposable process model: liveness/readiness probes, rolling deploys, self-healing.
- KEDA (and the http-add-on) make elasticity real — scale on lag or RPS, all the way to zero.
- Istio supplies resilience and security at the wire: timeouts, retries, circuit breaking, mTLS.
- OpenTelemetry + Tempo / Mimir / Prometheus / Grafana / Kiali make every request observable.
- Your job is to write services that lean on these — not to reimplement them per service.

p. 7

> The platform is doing most of the work. For a C++ service this means: no in-process service discovery (Kubernetes DNS), no in-process load balancing (the mesh), no in-process circuit breaker by default (Istio DestinationRule), no in-process retries beyond a single safe attempt (the mesh handles bounded retries). The temptation in C++ is to write everything yourself because you can — but every wheel you reinvent is a wheel you now have to test, monitor, and patch. The discipline is the same as in every deck in the series: lean on the platform.

## [010] CLOUD-NATIVE PRINCIPLES · Design-first: the contract precedes the code (sldId 265)

- Agree the interface before implementing it — OpenAPI for REST, .proto for gRPC, AsyncAPI for Kafka topics, SDL for GraphQL.
- The contract is the source of truth — code generators read it; humans and AI tooling produce against it. Versioning lives at the contract layer, gated by Apicurio in CI.
- Contract-first tooling in C++ is uneven across the four protocols: decide which one carries codegen and which one stays at the documentation/registry layer.
- gRPC — strongest path: protoc + grpc_cpp_plugin generates full C++ server + client stubs from .proto. The cleanest codegen of the four.
- GraphQL — strong: cppgraphqlgen generates server stubs and types from .graphql SDL. Apollo Federation over C++ REST/gRPC backends is the simpler alternative we'll revisit in §3.
- OpenAPI — workable: write the YAML first, scaffold C++ stubs with OpenAPI Generator (stable C++ server generators: cpp-pistache-server, cpp-httplib-server; none targets Drogon). Drogon does not auto-generate OpenAPI from handlers the way FastAPI does — the YAML is hand-maintained or template-generated, then versioned in Apicurio.
- AsyncAPI — documentation only: no maintained C++ generator. Register topic schemas in Apicurio; the actual codegen comes from the payload format (Protobuf via protoc, Avro via Avro-C++).
- Contract-first is non-negotiable under AI tooling — even where C++ codegen isn't strong, the YAML/SDL/proto is what defines 'done' for a model to produce against.

p. 8

> Design-first in C++, protocol by protocol. The four protocols differ sharply in how much code the contract generates. gRPC and GraphQL have first-class C++ generators: point protoc or cppgraphqlgen at the contract and you get stubs. OpenAPI is workable but doesn't have the FastAPI-style 'free' generation: the contract lives separately from the Drogon handlers and the YAML is either hand-written, scaffolded by openapi-generator-cli, or documented after the fact. AsyncAPI is the weakest — there's no actively-maintained C++ template in the AsyncAPI generator project, so it serves as registry-level documentation and the actual schema work happens via the payload format (Protobuf, Avro). None of this lets you off the hook on contract-first — the discipline is what makes AI tooling tractable, even when the codegen pipeline is partial.

## [011] CLOUD-NATIVE PRINCIPLES · The twelve-factor app, revisited (sldId 266)

- The twelve-factor app (2011) is the original recipe for software that's disposable, scalable and portable.
- Most factors are now platform concerns: the platform gives you build/release/run separation, port binding, log streaming, processes, concurrency.
- A few factors remain yours: codebase, dependencies, config, backing services, dev/prod parity, admin processes.
- For C++ specifically: dependencies pinned by Conan + a lockfile; config parsed once in main() into a const struct; backing services as URLs; logs to stdout (not a file).
- Treat it as a pre-flight check: will this survive the platform? Each factor maps to a place in our architecture.

p. 9

> 12-factor isn't dated; it's been absorbed by the platform. Worth re-reading every couple of years. For C++ the highest-yield factors to internalize are III (Config), IV (Backing services), VI (Processes: be stateless), IX (Disposability: fast startup, graceful shutdown), and XI (Logs: stdout only, never spdlog's basic_logger_mt, which opens a file and hits EROFS on a read-only rootfs). Those last three are where C++ services trip most often, and we'll spend appendix time on them.

## [012] CLOUD-NATIVE PRINCIPLES · What the twelve factors are (sldId 267)

The original 2011 checklist — most are now platform concerns; only a few are yours to write.

p. 10

> The 12 factors at a glance. Read the original at 12factor.net — Adam Wiggins wrote it in 2011 and the model has held up remarkably well. The grouping that follows sorts them by what each asks of you in a C++ service on Kubernetes.

## [013] CLOUD-NATIVE PRINCIPLES · Twelve factors, mapped to our system (sldId 268)

Most factors are now platform defaults you adopt; a few are discipline you still write.

p. 11

> Mapping the 12 factors to our C++ system. Build & ship → one repo, Conan + CMake, one image per release. Configure → parsed once in main() into a const struct, constinit for the unavoidable globals; no scattered getenv calls. Run on the platform → stateless, fast startup (RAII composition root), behind Istio. Attach resources → Postgres via libpq, Kafka (Strimzi) via librdkafka (rdkafka++), Apicurio for schemas. Operate → OpenTelemetry C++ SDK feeding the LGTM stack, admin work as Jobs/CronJobs. Note Apicurio stays a seam — same posture as every other deck in the series.

## [014] CLOUD-NATIVE PRINCIPLES · A 12-factor Drogon service, ready for the platform (sldId 269)

[chip] c++ · Drogon

```c++
// main.cpp (excerpt), examples/01-cloud-native-principles/cpp; conan.lock pins every library
using Callback = std::function<void(const HttpResponsePtr&)>;
const char* env(const char* name, const char* fallback) {   // config from env, factor III
  const char* v = std::getenv(name);  return v ? v : fallback;   // unset: the default
}
int main() {
  g_version = env("SERVICE_VERSION", "1.0.0");
  g_pool = std::make_unique<cndp::PgPool>(
      env("PG_CONNINFO", "postgresql://appuser:apppass@postgres:5432/appdb"),
      std::atoi(env("PG_POOL_SIZE", "4")));
  app().registerHandler("/healthz", [](const HttpRequestPtr&, Callback&& cb) {
    Json::Value j;  j["status"] = "ok";  cb(HttpResponse::newHttpJsonResponse(j));  // liveness
  }, {Get});
  app().registerHandler("/readyz", [](const HttpRequestPtr&, Callback&& cb) {
    const bool db_ok = db_ready();             // SELECT 1 via the libpq pool (retry elided)
    Json::Value j;  j["status"] = db_ok ? "ready" : "down";
    auto resp = HttpResponse::newHttpJsonResponse(j);
    if (!db_ok) resp->setStatusCode(k503ServiceUnavailable);   // down: out of rotation
    cb(resp);
  }, {Get});
  app().addListener("0.0.0.0", 8080).run();    // factor VII: port binding
}
```

Probes, env-config and an explicit version are the price of admission for a Kubernetes Deployment.

p. 12

> A 12-factor Drogon service, from Example 01. Configuration comes from the environment (factor III): a small env() helper returns the variable or a default, so an unset variable never turns into a null pointer, and main() reads PG_CONNINFO, PG_POOL_SIZE and SERVICE_VERSION once at start-up.
>
> /healthz answers while the process is up (liveness); /readyz runs SELECT 1 through the libpq pool and answers 200 with status ready, or 503 with status down (readiness; the probe reads the status code, not the body), so the probe that takes a Pod out of rotation is not the probe that restarts it. Handlers are lambdas with the request and callback types spelled out, which Drogon's handler binding needs.
>
> Port binding (factor VII) is explicit in main(): the binary is self-contained, with no external web server in front of it. conan.lock pins every library, and the Containerfile builds with GCC 15 on UBI 10.

## [015] Communications (sldId 270)

02

Match the interaction style to the call.

> Section 02 divider: Communications. Match the interaction style to the call.

## [016] COMMUNICATIONS · Pick the protocol for the interaction (sldId 271)

REST for reach, gRPC for internal speed, GraphQL for client-driven reads, async for decoupled facts.

p. 13

> The protocol matrix. The point of this slide is that 'pick a protocol' is a per-edge decision, not a per-service decision — one C++ service can speak REST at the edge, gRPC east-west, and publish to Kafka, all from the same binary. C++ specifics: Drogon at the REST edge (or cpp-httplib for minimal cases); grpc::Server for the gRPC surface; librdkafka's C++ API (rdkafka++) for the producer and consumer; cppgraphqlgen for native GraphQL or, as the simpler default covered in §3, a Node/Apollo gateway in front of the REST + gRPC backends with no native C++ GraphQL.

## [017] COMMUNICATIONS · REST at the edge with Drogon (sldId 272)

[chip] c++ · Drogon

```c++
// orders_controller.h — Drogon controller; OpenAPI YAML is the contract
struct OrderIn { std::string sku; int quantity; };
struct Order   { std::string id, sku, status; int quantity; };

class Orders : public drogon::HttpController<Orders> {
 public:
  METHOD_LIST_BEGIN
    ADD_METHOD_TO(Orders::place, "/orders", Post);
    ADD_METHOD_TO(Orders::list,  "/orders?after={1}&limit={2}", Get);
  METHOD_LIST_END
};
// orders_controller.cc — body validated against the YAML, 201 on create
Task<> Orders::place(HttpRequestPtr req, auto cb) {
  auto in = co_await parse_validated<OrderIn>(req);   // throws → 400
  Order o  = co_await orders.create(in);
  co_await events.publish("order.placed", o);          // emit the fact
  auto r = HttpResponse::newHttpJsonResponse(to_json(o));
  r->setStatusCode(k201Created); cb(r);
}
Task<> Orders::list(HttpRequestPtr r, auto cb, std::string a, int n) {
  cb(HttpResponse::newHttpJsonResponse(to_json(           // cursor, not offset
       co_await orders.page(a, n))));
}
```

Resource-shaped URLs, validated contracts, correct status codes, cursor pagination — the edge surface other teams depend on.

p. 14

> REST at the edge in Drogon. Two patterns to call out: (1) HttpController is the idiomatic Drogon route registration — the METHOD_LIST macros declare paths and verbs in one place, and Drogon's coroutine integration lets handlers be Task<> functions that co_await on async DB / Kafka calls without callback nesting. (2) parse_validated<OrderIn> is your seam to the OpenAPI YAML — either hand-roll it against the schema, or generate it via openapi-generator-cli and link in. Either way, Drogon handlers stay clean and the contract stays in version control. cpp-httplib is the leaner alternative for sidecars or small admin services where Drogon's machinery is more than you need.

## [018] COMMUNICATIONS · gRPC for internal service-to-service calls (sldId 273)

[chip] c++ · gRPC

```c++
// inventory.proto — the contract, registered in Apicurio
syntax = "proto3";
service Inventory {
  rpc ReserveStock (ReserveRequest) returns (ReserveReply);
}
message ReserveRequest { string sku = 1; int32 quantity = 2; }
message ReserveReply   { bool reserved = 1; int32 remaining = 2; }

// server.cc — stubs generated by protoc + grpc_cpp_plugin
class InventoryServicer final : public Inventory::Service {
 public:
  explicit InventoryServicer(Stock& s) : stock_(s) {}    // DI by ref
  grpc::Status ReserveStock(grpc::ServerContext* ctx,
                            const ReserveRequest* req,
                            ReserveReply*         reply) override {
    auto deadline = ctx->deadline();              // budget-aware
    auto [ok, remaining] = stock_.reserve(req->sku(), req->quantity());
    reply->set_reserved(ok);
    reply->set_remaining(remaining);
    return grpc::Status::OK;
  }
 private: Stock& stock_;
};
```

Schema-first, binary, multiplexed over HTTP/2 — the right default for chatty internal paths. Test with ghz.

p. 15

> gRPC internal-east-west. Three idioms: (1) sync API: we use the blocking Service base class, not the callback or async API; for most read/reserve paths the sync API is simpler and the performance gap is small. (2) deadline propagation — ServerContext::deadline() gives you the inbound budget; you pass the remainder to the DB statement_timeout and any outbound ClientContext. Blown budget surfaces as DEADLINE_EXCEEDED, never as a hung handler. (3) DI by reference — Stock& injected, owned in main(), no singletons. CMake snippet for codegen: protobuf_generate(LANGUAGE cpp) + protobuf_generate(LANGUAGE grpc PLUGIN protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin>).

## [019] COMMUNICATIONS · Synchronous coupling vs. asynchronous facts (sldId 274)

A synchronous call shares fate; an event shares a fact. Reach for async wherever immediacy isn't required.

p. 16

> Sync vs async is a coupling decision, not a perf decision. A synchronous gRPC call binds the caller's fate to the callee's availability; a Kafka event publishes a fact and walks away. C++ implications: synchronous code uses gRPC ClientContext with a deadline; asynchronous code uses a process-scoped librdkafka producer (rdkafka++, one per binary, not per request). The producer is bounded in queue, retries and memory, consistent with the 'bound everything' rule. When in doubt: async. Sync is the special case, not the default.

## [020] COMMUNICATIONS · The mesh handles the wire, not your code (sldId 275)

Istio sidecars give you mTLS, retries, timeouts and telemetry — uniformly, without per-service code.

p. 17

> The Istio sidecar handles wire concerns: mTLS, bounded retries with backoff, timeouts, outlier detection, hop-level telemetry. The C++ temptation is to write this yourself because you can — but every wheel you reinvent in-process is a wheel you have to test, monitor, patch, and document. The sidecar runs as Envoy alongside your C++ pod, and your binary stays clean. Two C++-specific notes: (1) gRPC retries from the application side should be limited to a single safe attempt — let Istio do bounded retries with backoff. (2) Don't double-instrument with both Envoy spans and your application OTel spans on the same hop — pick one boundary.

## [021] COMMUNICATIONS · Resilience as configuration, not per-call code (sldId 276)

[chip] yaml · istio

```yaml
# Istio: bounded timeout + retries for inventory-service
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: inventory }
spec:
  hosts: [inventory]
  http:
    - timeout: 2s
      retries:
          attempts: 2                # bounded — never an unbounded retry storm
          perTryTimeout: 800ms
          retryOn: connect-failure,unavailable
      route:
        - destination: { host: inventory }

---
# DestinationRule (separate doc): outlierDetection ejects bad pods,
# circuit-breaker thresholds on pending requests, max connections.
# All resilience as configuration — no per-service C++ code.
```

Bounded retries with backoff live in the mesh. Unbounded client retries are how an incident becomes an outage.

p. 18

> Resilience as YAML, not as scattered try/catch in C++. The VirtualService bounds timeouts and retries at the mesh layer; the DestinationRule adds outlier detection so a single bad pod gets ejected from rotation. Both live in Git, both are versioned, both apply uniformly to every pod in the service — no per-binary configuration. What stays in your C++ code: one safe retry where the call is idempotent (for example, with an idempotency key); deadline propagation via gRPC ClientContext::set_deadline; circuit breaking is the mesh's job, not yours. Cap the retry budget at the inbound deadline and never retry past it (cpp-statelessness Doc 07, patterncatalyst.github.io/cpp-statelessness/docs/07-state-externalization/).

## [022] Composition (sldId 277)

03

Aggregate at the edge, not inside services.

> Section 03 divider: Composition. Aggregate at the edge, not inside services.

## [023] COMPOSITION · One query, many services (sldId 278)

The gateway presents one schema and fans out to REST and gRPC back-ends, then joins and shapes the result.

p. 19

> Federation at the edge. The gateway exposes a single GraphQL schema; resolvers fan out to the owning services via REST or gRPC. Two ways to implement this gateway in our stack: (1) Native C++: cppgraphqlgen as a Drogon service that owns the schema and resolves fields against C++ REST/gRPC backends. Strongest type safety, more setup. (2) Apollo (Node.js) Federation: keep the C++ services exposing REST + gRPC only; the GraphQL concern lives in a Node gateway service. Less code in C++, less to maintain across teams. Most shops with mixed-language fleets end up here. Both appear in this section, native C++ first.

## [024] COMPOSITION · A composing resolver in cppgraphqlgen (sldId 279)

[chip] c++ · cppgraphqlgen

```c++
// schema.graphql is the contract — schemagen produces these types:
//   type Query { order(id: ID!): Order }
//   type Order { id: ID! sku: String! status: String! stock: Int! }
class OrderResolver : public object::Order {
 public:
  OrderResolver(Order o, InventoryClient& inv) : o_(std::move(o)), inv_(inv) {}
  service::AwaitableScalar<std::string> getId()     const { co_return o_.id; }
  service::AwaitableScalar<std::string> getSku()    const { co_return o_.sku; }
  service::AwaitableScalar<std::string> getStatus() const { co_return o_.status; }
  service::AwaitableScalar<int> getStock() const {      // resolved on demand
    auto reply = co_await inv_.ReserveStock_view(o_.sku);  // gRPC
    co_return reply.remaining();
  }
 private: Order o_; InventoryClient& inv_;
};
class QueryResolver : public object::Query {
 public:
  service::AwaitableObject<std::shared_ptr<object::Order>>
  getOrder(std::string id) const {
    Order o = co_await orders_.get(id);              // REST to order-service
    co_return std::make_shared<OrderResolver>(std::move(o), inv_);
  }
 private: OrdersClient& orders_; InventoryClient& inv_;
};
```

The gateway owns aggregation; each field resolves against the owning service. Simpler alternative: an Apollo (Node) gateway over the same C++ REST + gRPC backends — no native GraphQL in the C++ services.

p. 20

> Native C++ GraphQL via cppgraphqlgen. The pattern: schemagen reads schema.graphql at build time and produces Object base classes (object::Order, object::Query); you subclass them and implement the getX methods. Coroutine-based via service::AwaitableScalar / AwaitableObject. Each field is resolved against the owning service — getStock here calls inventory via gRPC, getOrder calls order-service via REST. Dependencies are injected by reference (OrdersClient&, InventoryClient&) from a composition root in main(), as in cpp-statelessness Doc 04 (patterncatalyst.github.io/cpp-statelessness/docs/04-process-scoped-state/). The trade-off: cppgraphqlgen is well maintained, but the C++ resolver code is verbose compared to Strawberry or Apollo. Many production C++ shops choose the Apollo gateway path instead — keep C++ services on REST/gRPC, write the gateway in Node where the GraphQL ecosystem is mature, and accept the extra service in the deployment topology. Either path is defensible; the choice depends on your team's polyglot tolerance.

## [025] COMPOSITION · Three ways to compose — and where each belongs (sldId 280)

Push aggregation to a gateway or BFF. Chaining calls inside services rebuilds the monolith over the network.

p. 21

> Three composition patterns. (1) Gateway federation: one schema, many backends, edge does the join. Apollo gateway or cppgraphqlgen on Drogon, as compared in the federation discussion. (2) BFF (backend-for-frontend): per-client gateway tuned for one consumer (web BFF vs mobile BFF). Same C++/Node trade-off as federation. (3) Service-to-service chaining: order-service calls inventory-service which calls payment- service. This is the anti-pattern. In C++ it's especially tempting because the call sites look cheap (gRPC client, stack allocation), but you're building a synchronous fate-shared fan-out that fails together. Push the aggregation out to the edge; let services own their own domain and emit events for what others care about. Rule of thumb: a service should never need more than one other service to satisfy its own command — if it does, aggregation belongs at the gateway, not inside the service.

## [026] Data (sldId 281)

04

Own your data; share it through contracts.

> Section 04 divider: Data. Own your data; share it through contracts.

## [027] DATA · A database per service (sldId 282)

Each service owns its schema and storage engine; no other service touches its tables directly.

p. 22

> Database-per-service is the boundary contract for data. In C++ this means: each service opens its own libpq connection pool against its own schema, and the only external surface is the API. Cross-service joins happen at the gateway (composition) or via events — never by reaching into another service's tables. Each service checks connections out through an RAII guard that invalidates a broken connection instead of returning it to the pool (ScopedConn in cpp-statelessness Doc 07, patterncatalyst.github.io/cpp-statelessness/docs/07-state-externalization/). Storage engine choice follows access pattern: PostgreSQL is the default; document stores, time-series, search indexes are per-service decisions. Apicurio holds the public schemas (API contracts), not the internal database DDL.

## [028] DATA · CQRS — Command Query Responsibility Segregation (sldId 283)

Separate the write model from the read model. They have different shapes, scales and even different stores.

p. 23

> CQRS as a pattern: the write model optimises for invariants and transactions; the read model optimises for query shape. They live in different stores when needed (Postgres for writes, Elasticsearch or a denormalised Postgres view for reads). Projections, built by consuming events from the write side, keep the read store in sync. Don't apply CQRS by default; reach for it when read and write loads, shapes, or consistency needs diverge enough that a single model becomes a compromise. The C++ implementation is mechanical once you accept the pattern.

## [029] DATA · CQRS in practice (sldId 284)

[chip] c++ · libpq + kafka

```c++
// Write side — command handler (one txn, outbox row, no broker call)
Task<> Orders::place(HttpRequestPtr req, auto cb) {
  auto in = co_await parse_validated<OrderIn>(req);
  PgTxn txn = co_await pg_.begin();                  // one local txn
  Order o   = co_await txn.exec(insert_order_sql, in);
  co_await txn.exec(insert_outbox_sql,
      "order.placed", o.id, to_json(o));             // same txn
  co_await txn.commit();                             // CDC publishes
  cb(HttpResponse::newHttpJsonResponse(to_json(o)));
}
// Read side — queries a different, denormalised store
Task<> Orders::summary(HttpRequestPtr req, auto cb, std::string oid) {
  auto row = co_await read_pg_.fetch_opt(
      "SELECT * FROM order_summary WHERE order_id = $1", oid);
  if (!row) throw grpc::Status{NOT_FOUND, "unknown order"};
  cb(HttpResponse::newHttpJsonResponse(to_json(*row)));
}
// Projection — consumes events, upserts the read model (idempotent)
std::unique_ptr<RdKafka::Message> msg(consumer->consume(100));   // rdkafka++
if (msg->err() == RdKafka::ERR_NO_ERROR) {
  read_pg_.exec(upsert_order_summary_sql, deserialize(payload_of(*msg)));
  consumer->commitSync(msg.get());                   // after the upsert
}
```

Write side, read side, projection — three flows, one consistent story. At-least-once delivery + idempotent upsert.

p. 24

> Three flows in one slide. Write side: a single libpq transaction writes the row and an outbox row, then commits — CDC publishes the fact, never the app code. Read side: queries a different store (here a denormalised order_summary table; could be Elasticsearch, Redis, anything). Projection: a librdkafka consumer applies events to keep the read model fresh and commits offsets after the upsert succeeds; at-least-once delivery with an idempotent ON CONFLICT DO UPDATE is the standard pattern. PgTxn stands for a small RAII wrapper over a libpq transaction (BEGIN on construction, ROLLBACK in the destructor unless commit() ran); Example 04 writes the same BEGIN, COMMIT and ROLLBACK with libpq calls directly. The consumer is process-scoped; the exception path on the read side uses grpc::Status which we'd translate at the handler boundary.

## [030] DATA · Log tailing — the database commit log is the event stream (sldId 285)

Debezium tails the WAL and publishes every committed row as a Kafka event. No dual-write.

p. 25

> Log tailing (CDC) is the answer to the dual-write problem. Debezium runs as a Kafka Connect task, tails the Postgres WAL via logical replication, and publishes every committed row to Kafka. From the C++ service's perspective: you commit to Postgres and you're done. The broker may be down for hours — the events still arrive, in commit order, once CDC catches up. This is the pattern that makes 'exactly-once effect' achievable from at-least-once delivery: the database commit is the source of truth, and the Kafka event is its replication.

## [031] DATA · Dual-write is unsafe — use the outbox (sldId 286)

Write state and the outbox row in one transaction; CDC relays the committed fact to Kafka.

p. 26

> Dual-write is the classic distributed-systems bug: write to DB, then write to Kafka. Either can fail without the other, leaving an inconsistency you can't reconcile after the fact. The outbox pattern is the fix: write state and an outbox row in one local transaction; let a separate process (Debezium, or a custom relay) read the outbox and publish to Kafka. C++ implementation is unchanged from any other language — the transaction discipline is the interesting part. Pair with idempotent consumers (ON CONFLICT DO NOTHING / DO UPDATE) and you get exactly-once effect from at-least-once delivery.

## [032] DATA · The outbox write — one transaction, no lost events (sldId 287)

[chip] c++ · libpq

```c++
// order-service (excerpt): order row + outbox row in one libpq transaction
PGresult* res = PQexec(conn, "BEGIN");                // single local txn
if (PQresultStatus(res) != PGRES_COMMAND_OK) { /* 500, nothing written */ }
PQclear(res);
const char* params_order[4] = {id.c_str(), sku.c_str(), quantity_s.c_str(), status.c_str()};
res = PQexecParams(conn,
    "INSERT INTO orders (id, sku, quantity, status) VALUES ($1, $2, $3, $4)",
    4, nullptr, params_order, nullptr, nullptr, 0);   // the state change
// on any error: PQexec(conn, "ROLLBACK") and answer 500
const char* params_outbox[3] = {id.c_str(), "order.placed", payload_str.c_str()};
res = PQexecParams(conn,
    "INSERT INTO outbox (aggregate_id, event_type, payload) VALUES ($1, $2, $3::jsonb)",
    3, nullptr, params_outbox, nullptr, nullptr, 0);  // atomic with the state change
res = PQexec(conn, "COMMIT");                         // Debezium publishes the row
// No Kafka call on the request path: if the broker is down the order
// still commits, and the event is delivered when CDC catches up.
```

The database commit is the source of truth. The outbox + CDC turns it into a guaranteed, ordered event.

p. 27

> The outbox write in the C++ example uses libpq directly. Three things to call out: (1) BEGIN, the orders insert, the outbox insert and COMMIT run on one connection; any failure rolls back and answers 500, so the order and its event are written together or not at all. (2) No Kafka call inside the request path: calling a producer from the handler would reintroduce the dual-write the outbox removes. (3) Debezium runs as Kafka Connect and publishes the committed outbox rows; the order-service has no Kafka-publish code. The cost is one extra process and a small outbox table; the benefit is an event for every committed order with no distributed-transaction machinery.

## [033] DATA · Consistency without distributed transactions: the saga (sldId 288)

A chain of local transactions; failures trigger compensating actions, never a cross-service rollback.

p. 28

> Sagas are how you get cross-service consistency without two-phase commit. Each step is a local transaction in one service; if a later step fails, earlier steps are compensated (refunded, released, marked-cancelled — semantically reversed, not rolled back). In C++ we implement the saga itself with boost::sml as a finite state machine — strongly typed, header-only, ~200 lines for an order-fulfillment saga. The FSM state is persisted to Postgres in the same transaction as each step, so crash recovery is automatic: on restart, load the state, see which step we were on, and resume. Appendix D goes into the boost::sml implementation in detail.

## [034] Event-Driven (sldId 289)

05

Emit facts; let consumers decide.

> Section 05 divider: Event-Driven. Emit facts; let consumers decide.

## [035] EVENT-DRIVEN · The event backbone — one fact, many reactions (sldId 290)

order.placed fans out to consumers the producer never names. Add a consumer without touching the producer.

p. 29

> Event-driven coupling is the loosest coupling you can achieve while still cooperating. order-service publishes order.placed; inventory-service, payment-service, notification-service, analytics, audit, and three more services you haven't built yet can all consume it. The producer doesn't know they exist. Concretely for C++: a single RdKafka::Producer instance, process-scoped, owned in main(), shared by reference. Topic partitioning is done by message key (usually the aggregate ID — order.id) so all events for one entity land in the same partition and stay ordered. Consumers commit offsets after their side effects succeed.

## [036] EVENT-DRIVEN · Producing and consuming with librdkafka (sldId 291)

[chip] c++ · rdkafka++

```c++
// Producer (excerpt): process-scoped, built once in main() (librdkafka C++ API, rdkafka++)
std::unique_ptr<RdKafka::Conf> conf(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));
conf->set("bootstrap.servers", cfg.kafka_bootstrap, err);
conf->set("acks", "all", err);                  // wait for ISR ack: durable
conf->set("dr_cb", &delivery_report, err);      // DeliveryReportCb logs failures
std::unique_ptr<RdKafka::Producer> producer(RdKafka::Producer::create(conf.get(), err));
void publish_order_placed(const Order& o) {
  auto value = serialize(o);
  producer->produce("order.placed", RdKafka::Topic::PARTITION_UA,
                    RdKafka::Producer::RK_MSG_COPY, value.data(), value.size(),
                    o.id.data(), o.id.size(), 0, nullptr);   // key = order id
  producer->poll(0);                            // serve delivery reports
}
std::unique_ptr<RdKafka::KafkaConsumer> consumer(
    RdKafka::KafkaConsumer::create(cconf.get(), err));
consumer->subscribe({"order.placed"});   // notification-group, enable.auto.commit=false
while (running) {
  std::unique_ptr<RdKafka::Message> msg(consumer->consume(1000));
  if (msg->err() != RdKafka::ERR_NO_ERROR) continue;   // timeout / partition EOF
  send_email(deserialize(payload_of(*msg)));            // idempotent handler
  consumer->commitSync(msg.get());                      // after the side-effect
}
```

Commit offsets after the side-effect, and make handlers idempotent — at-least-once delivery is the contract.

p. 30

> librdkafka's C++ API (rdkafka++) is the C++ binding that ships with librdkafka, the C client that most Kafka clients build on; the examples pin librdkafka 2.14.2 from ConanCenter. Three patterns: (1) the producer is process-scoped: one instance per binary, owned in main(), shared by reference, never one per request; poll() serves the delivery reports. (2) acks=all waits for every in-sync replica before the delivery report; add enable.idempotence=true when a producer retry must never write the record twice.
>
> (3) Commit after the side-effect succeeds: with enable.auto.commit=false and commitSync after the handler, the offset never advances past work that did not finish, and a restart re-delivers instead of losing events. Handlers are idempotent because at-least-once delivery means a record can arrive twice. The loop exits on a shutdown flag, which gives a graceful drain instead of an abrupt termination.

## [037] EVENT-DRIVEN · Schemas are the contract — the registry enforces them (sldId 292)

Apicurio holds versioned schemas; compatibility is checked at publish time so breaking changes are rejected early.

p. 31

> Schema registry (Apicurio) is non-optional for production event-driven systems. Without it, a producer can ship a breaking schema change and silently corrupt consumers across the fleet. With it, breaking changes are rejected at publish time. For C++: protobuf is the natural schema choice — schemas live in .proto files, register to Apicurio at deploy time, codegen via protoc gives you typed structs both sides. Avro is also supported (Avro-C++ for serialisation, Apicurio for the registry). JSON Schema works but loses the binary efficiency. Compatibility mode (BACKWARD, FORWARD, FULL) is set per topic — BACKWARD is the safe default: old consumers can read new messages.

## [038] EVENT-DRIVEN · Event sourcing vs. event streaming (sldId 293)

Two patterns, often confused. Sourcing: the events are the state. Streaming: events are the transport.

p. 32

> These two patterns get conflated constantly. Event sourcing means events are the state: you don't store the current order; you store the sequence of events that produced it, and you derive current state by replay. Event streaming means events are how state changes are transported — the order row in Postgres is the truth; Kafka is the wire. Most production systems use event streaming (with Postgres + outbox + CDC, as we've shown). Event sourcing is a much bigger commitment: your storage is the event log, your queries are replays or projections, and snapshotting becomes a first-class concern. Adopt event sourcing where the audit log and the temporal queries are the primary use case (financial ledgers, regulated workflows, debugging-heavy domains).

## [039] EVENT-DRIVEN · Event-driven tools landscape — Kafka, Pulsar, Flink, NiFi (sldId 294)

Different jobs, often together: substrate (Kafka, Pulsar), compute (Flink), movement (NiFi, Debezium).

p. 33

> Three layers of the event-driven stack: (1) substrate — Kafka (Strimzi on Kubernetes) and Pulsar are the durable log. Pick Kafka by default; reach for Pulsar when geo-replication or tenant isolation is a first-class need. (2) compute — Flink for stateful stream processing, windowed aggregations, and complex event processing. (3) movement — NiFi for routing and transformation between systems; Debezium for database CDC. For C++ services specifically: we're producers and consumers on the substrate. Compute lives in Flink (Java/Scala) — the Stream Processing section frames this as 'stream processing as a pipeline'. Movement is operational tooling, not application code. None of these have native C++ alternatives we'd recommend over the JVM-based incumbents.

## [040] EVENT-DRIVEN · The log is the source of truth (sldId 295)

Consumers track their own offset; replay is just rewinding. Kafka (Strimzi) and Pulsar are logs, not queues.

p. 34

> The mental model shift: Kafka is not a queue. A queue is a one-shot delivery mechanism where consuming the message destroys it. Kafka is an append-only log; the message stays until the retention policy says otherwise, and every consumer (group) tracks its own position. Implications for C++ services: (1) Reprocessing is just seeking to an earlier offset. A bug in your handler? Fix it, reset the offset, replay. (2) New consumers can join with auto.offset.reset=earliest and catch up from the beginning of retained history. (3) Retention is a real configuration concern — a topic with retention=7days is forgetful; a compacted topic remembers the latest value per key forever. Choose retention per topic.

## [041] Stream Processing (sldId 296)

06

Streams in, derived streams out.

> Section 06 divider: Stream
>
> Processing. Streams in, derived streams out.

## [042] STREAM PROCESSING · Derive new streams from streams (sldId 297)

A streaming app is a topology of sources, stateful processors and sinks — joins, windows and aggregates.

p. 35

> Stream processing is the second layer of the event-driven story: not just transport, but transformation. The topology is sources → stateful processors → sinks; the processors hold windowed state and emit derived streams. For C++ specifically, heavyweight stream processing belongs in Flink (JVM). What's tractable in-process for a C++ service is windowed aggregation over librdkafka's C++ API — small state, bounded windows, no joins across topics. The in-process pattern fits small, bounded state; production-grade joins, CEP and large state belong in Flink, with C++ services as producers and consumers.

## [043] STREAM PROCESSING · In-process windowed aggregation (sldId 298)

[chip] c++ · rdkafka++

```c++
// stream-processor (excerpt, simplified): order.placed -> per-merchant tumbling
// windows -> revenue.by-merchant. Bounded state fits in-process; joins: Flink.
std::unordered_map<std::string, cndp::MerchantWindows> merchants_;  // open windows

void aggregate(const std::string& merchant, int64_t ts, const cndp::Decimal& amount) {
  auto it = merchants_.try_emplace(merchant,
                cndp::MerchantWindows(window_seconds_)).first;   // WINDOW_SECONDS
  auto update = it->second.apply(ts, amount);    // nullopt: late record, dropped
  if (!update) return;
  send("revenue.by-merchant", merchant,           // running total for the window
       cndp::revenue_json(merchant, *update), 0);
}

bool commit_batch() {                            // after each batch of up to 500
  producer_->flush(30000);                       // outputs delivery-reported first
  if (reports_.failed() > 0) return false;       // else exit, replay from last commit
  consumer_->commitSync();                       // then commit the input offsets
  return true;
}
// The example re-keys order.placed through a repartition topic first, so each
// merchant's records land on one partition and one instance.
```

In-process is fine for small, bounded windowed state; outputs are delivered before offsets commit. For joins, CEP or large state, deploy Flink.

p. 36

> The in-process stream-processing pattern from the C++ example. Three things to call out: (1) state is bounded by design: one MerchantWindows per merchant holds only the open tumbling windows, and a window closes when stream time passes its end, so a late record is dropped. (2) Every update is a running total keyed by merchant and window start; consumers of revenue.by-merchant keep the latest record per window. (3) Outputs first, offsets second: after each batch the producer flushes, and the input offsets are committed only when every output was delivery-reported; a failed delivery stops the process so the batch replays.
>
> The example also re-keys order.placed through a repartition topic so each merchant lands on one partition, and it sums money as exact fixed-point decimals. When this pattern stops scaling (joins across topics, long retention, exactly-once aggregation), deploy a Flink job and keep the C++ service as a producer and consumer.

## [044] STREAM PROCESSING · KEDA scales workers on the signal that matters (sldId 299)

Scale Kafka workers on consumer lag and HTTP services on request rate — both down to zero when idle.

p. 37

> KEDA (Kubernetes Event-Driven Autoscaler) is the right answer for both async workers and synchronous HTTP services. For Kafka consumers, the signal is consumer lag — when order.placed lag exceeds the threshold, scale up; when it drops back under, scale down, potentially to zero. For HTTP services (Drogon), the signal is concurrent requests, measured by the KEDA http-add-on which fronts the service. Why this matters for C++: a Drogon binary cold-starts in tens of milliseconds, which makes scale-to-zero viable; the latency of the first request after a cold start is well within typical HTTP timeout budgets. This is one of the real wins of choosing C++ for cloud-native services.

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
# HTTP: scale the Drogon service on concurrent requests (KEDA http-add-on)
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

> Two KEDA objects, one mechanism. The Kafka ScaledObject scales the payment-consumer deployment based on consumer-group lag — 100 events of lag per replica is a reasonable default, tune to your workload. The HTTPScaledObject (from the KEDA http-add-on) puts an interceptor in front of the service that measures concurrent requests and scales pods to match. Both go to zero when idle — for a C++ binary this is realistic because cold start is fast. For Python or JVM services the scale-to-zero math is harder because the first-request latency dominates. Worth checking your specific Drogon image's cold-start time in your environment before relying on min=0 in production.

## [046] Workflows and Jobs (sldId 301)

07

Not every unit of work is a request.

> Section 07 divider: Workflows
>
> and Jobs. Not every unit of work is a request.

## [047] WORKFLOWS AND JOBS · Orchestration vs. choreography (sldId 302)

A coordinator that commands keeps the flow in one place; events that trigger each other decouple but hide the flow.

p. 39

> Two ways to coordinate multi-step business processes across services. Orchestration has a central coordinator that commands each step; choreography has services react to each other's events with no central authority. C++-specific framing — orchestration in production normally rides on Temporal or Cadence. There is no first-class Temporal C++ SDK; in our deck, C++ services participate in a Temporal workflow as activities, invoked via gRPC from a Temporal worker written in Go, Java, or TypeScript. The workflow code itself lives in that polyglot worker; the C++ service exposes the activity's grpc::Service. This is the integration pattern we'll lean on whenever a workflow engine appears in the architecture.

## [048] WORKFLOWS AND JOBS · Choosing between the two (sldId 303)

Orchestration

- One coordinator owns the saga and its state
- Flow is explicit and centrally observable
- One place to reason about, change and audit
- Risk: the orchestrator becomes a god-service
- Good for complex, long-lived business processes
- C++ integrates as Activities, invoked over gRPC from a Temporal worker

Choreography

- Each service reacts to the previous event
- Maximally decoupled; no central bottleneck
- Flow is emergent — harder to see end-to-end
- Risk: nobody owns the overall process
- Good for simple, additive event reactions
- C++ subscribes to topics with rdkafka++; in-process saga via boost::sml

p. 40

> When to pick which. Orchestration excels when there's clear ownership of a multi-step business process and the steps are complex or long-lived (order fulfillment, claims processing, multi-day approvals). The orchestrator becomes a real service, but the trade is explicit ownership and end-to-end visibility. Choreography excels when steps are simple and the additive list of consumers grows over time — analytics, audit, notifications fanning out from order.placed. C++-specific note (italic rows): orchestration means C++ services are Activities behind a Temporal worker in another language; choreography means C++ services own boost::sml state machines and react to Kafka topics directly. Both are workable; the choice is about your process complexity and your team's polyglot tolerance.

## [049] WORKFLOWS AND JOBS · Jobs, CronJobs and queue workers (sldId 304)

Long, batch or periodic work belongs in Jobs/CronJobs or a scaled queue worker — never on the request path.

p. 41

> Three Kubernetes-native patterns for non-request work. (1) Job: a one-shot batch — run a data migration, a backfill, a nightly export. The Job spec runs the same C++ binary you'd serve from, with a different argv. (2) CronJob: a scheduled Job — nightly reconciliation, weekly cleanup. (3) Queue worker: a long-running deployment that consumes from Kafka or a queue, scaled by KEDA on backlog. C++-specific note: the same Drogon binary can serve HTTP, consume Kafka, run as a Job, or run as a CronJob — pick the argv-driven mode in your image. Or split into separate binaries per CMake target if you prefer; both patterns work. The point: never put a 30-second operation on the synchronous request path.

## [050] API Management (sldId 305)

08

Treat the API surface as a platform.

> Section 08 divider: API
>
> Management. Treat the API surface as a platform.

## [051] API MANAGEMENT · Four cooperating planes (sldId 306)

Gateway and mesh at runtime; registry for contracts; metadata for discovery; observability for signals.

p. 42

> API management is four planes that have to cooperate. (1) Runtime: gateway at the edge, service mesh east-west. (2) Contract: schema registry (Apicurio) holds versioned OpenAPI/proto/AsyncAPI/SDL contracts. (3) Discovery & lineage: metadata catalogue (OpenMetadata) tracks who owns what, who depends on what, where signals come from. (4) Observability: OpenTelemetry feeding the LGTM stack stitches it all together. For C++ specifically, all four planes are external to the service binary. Your C++ code speaks Drogon/gRPC/Kafka; the platform handles the rest. This is the cleanest possible API-management story — the language is just a producer of contracts and signals.

## [052] API MANAGEMENT · Versioning and evolution are part of management (sldId 307)

- Evolve additively — new optional fields and endpoints; never repurpose or remove without a new version.
- Carry a major version in the path (/v2) or media type; deprecate with headers and a sunset date.
- The registry's compatibility rules (BACKWARD / FORWARD / FULL) enforce this mechanically at publish time.
- Run old and new side by side; migrate consumers off the old contract before you retire it.
- Per-protocol mechanics: proto3 fields are optional by default (additive is safe); OpenAPI requires explicit deprecation markers; GraphQL SDL evolves by deprecating fields, not bumping versions.
- Lifecycle: design → register → publish → consume → deprecate → retire — each step has an owner and a gate.

p. 43

> Versioning at the contract layer is the discipline that lets the rest of the API platform do its job. Five rules, one principle: evolve additively. C++-specific notes: protobuf field numbers are forever — adding a new field is safe, removing or repurposing one is a hard break that protoc-generated stubs can't paper over. OpenAPI in C++ is hand-maintained or scaffolded (see §1 design-first), so the discipline of deprecation markers and major-version paths lands on you, not on auto-generation. cppgraphqlgen regenerates from the SDL; deprecated fields stay in the generated code with a @deprecated annotation surfaced in introspection. The registry (Apicurio) gates breaking changes at publish time — BACKWARD compatibility is the right default for most topics.

## [053] API Registry (sldId 308)

09

One versioned home for every contract.

> Section 09 divider: API Registry. One versioned home for every contract.

## [054] API REGISTRY · Apicurio: contracts, versioned and gated (sldId 309)

OpenAPI, AsyncAPI, proto and Avro/JSON schemas live in one registry with compatibility rules and CI gating.

p. 44

> Apicurio is the central registry for every contract in the system: OpenAPI YAML for REST, .proto for gRPC, AsyncAPI for Kafka topics, Avro/JSON Schema for event payloads. One versioned, governable home. C++-specific framing: of these contract types, .proto and Avro are the ones with strong C++ codegen (protoc, Avro-C++). OpenAPI and AsyncAPI in C++ are documentation-first: Apicurio still holds them with compatibility rules, but the codegen pipeline is partial or absent (see design-first in §1). Apicurio's value to a C++ shop is the same as to any other: gate-keeping breaking changes before they ship.

## [055] API REGISTRY · Gate breaking changes in CI (sldId 310)

[chip] c++ · Apicurio

{% raw %}
```c++
// publish_schema.cc — invoked from CI after the build, before the merge.
// Apicurio answers 400 when a version breaks the artifact's rule (e.g. BACKWARD).
#include <httplib.h>
#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>
int publish(const std::string& group, const std::string& artifact_id,
            const std::string& schema) {
  httplib::Client cli{"http://apicurio.registry.svc"};
  cli.set_read_timeout(10);
  auto path = "/apis/registry/v3/groups/" + group +
              "/artifacts/" + artifact_id + "/versions";
  nlohmann::json body = {{"content", {{"content", schema},     // v3 CreateVersion
                                      {"contentType", "application/json"}}}};
  auto res = cli.Post(path, body.dump(), "application/json");
  if (!res) return 2;                          // unreachable: retry or page on-call
  if (res->status == 400) {                    // RuleViolationException
    spdlog::error("incompatible schema change, blocking the merge: {}", res->body);
    return 1;
  }
  if (res->status >= 300) { spdlog::error("{}", res->body); return 2; }
  return 0;                                    // 200: compatible, version created
}
```
{% endraw %}

The CI job fails the build on an incompatible change — the contract is enforced before code ships, not after.

p. 45

> Small, single-purpose binary you run as part of CI. cpp-httplib (header-only, MIT, github.com/yhirose/cpp-httplib) is the lean HTTP client; libcurl (curl license, curl.se) is the heavier alternative when you need richer auth or HTTP/2 multiplexing. Exit codes are meaningful: 0 = registered OK, 1 = incompatible (fail the merge), 2 = transient (retry or page). The CI step is `publish_schema build/schema.json` and the merge is blocked iff the registry rejects. The schema text travels as the content field of the v3 CreateVersion body with its content type (application/json for Avro and JSON Schema, application/x-yaml for OpenAPI or AsyncAPI, application/x-protobuf for a .proto); Apicurio stores it as given. Compatibility rules are configured once per artifact, not per push.

## [056] API Metadata (sldId 311)

10

If they can't find it, it doesn't exist.

> Section 10 divider: API Metadata. If they can't find it, it doesn't exist.

## [057] API METADATA · Discovery, lineage and ownership (sldId 312)

OpenMetadata ingests from services, the registry and Kafka to build a searchable catalog with lineage.

p. 46

> OpenMetadata is the discovery layer. It crawls the registry (Apicurio), the broker (Kafka topic list and schemas), the databases (table schemas), and the services (OpenAPI specs fetched from /openapi.json or equivalent endpoints) to build one searchable catalog with ownership, lineage, and quality signals. For a C++ shop the ingestion story is identical to any other language — OpenMetadata doesn't care that your service is C++; it cares that the service exposes its OpenAPI spec at a known URL. The C++ team's job is to publish that spec (the Apicurio-registered YAML) at a discovery endpoint and tag the service with its owning team and tier.

## [058] API METADATA · What the catalog gives every consumer (sldId 313)

- Discovery — search across APIs, topics and tables; find the owning team and how to get access.
- Trust — published SLOs, data-quality test results, freshness, and a tier/criticality rating.
- Lineage — column- and topic-level lineage answers 'if I change this, who breaks?' before you change it.
- Ownership & governance — tags, classifications (PII), and accountable owners attached to every asset.
- Ingestion runs as a scheduled connector against OpenAPI specs, the registry, Kafka and Postgres.
- For C++ services: publish the OpenAPI YAML at a known endpoint (e.g. /openapi.json), tag the service with team + tier in OpenMetadata — the ingestion connector does the rest.

p. 47

> Four concrete things a catalog gives you, plus the discipline they depend on: ownership and freshness are enforced at ingest time, not just collected. The bold final bullet is the only C++-specific thing here — the integration is mechanical, but the discipline of keeping the OpenAPI YAML accurate (since C++ doesn't auto-generate it the way FastAPI does) becomes more visible at this layer. If the YAML is stale, the catalog is stale, and consumers find out the hard way.

## [059] Observability (sldId 314)

11

Instrument once; correlate everything.

> Section 11 divider: Observability. Instrument once; correlate everything.

## [060] OBSERVABILITY · Three signals, one correlated story (sldId 315)

OpenTelemetry emits traces, metrics and logs; the LGTM-style stack stores them and Grafana joins them.

p. 48

> The classic three pillars: traces (what happened in this request), metrics (aggregates and trends), logs (the detail). OpenTelemetry is the single instrumentation API that emits all three; the LGTM stack (Loki / Grafana / Tempo / Mimir) stores them; Grafana correlates across by trace_id. For C++ this means the OpenTelemetry C++ SDK (opentelemetry-cpp, Apache 2.0, actively released), with the OTLP exporter pointing at your Collector. The Collector handles fan-out to Tempo / Mimir / Loki and the per-backend formatting; your C++ binary just speaks OTLP. Critical config: use the Batch span processor, never Simple in production, because Simple flushes synchronously and collapses throughput. cpp-statelessness Doc 04 shows the BatchSpanProcessor setup (patterncatalyst.github.io/cpp-statelessness/docs/04-process-scoped-state/).

## [061] OBSERVABILITY · The signals in depth — traces, metrics, logs, baggage, profiles (sldId 316)

Three classic pillars plus two that matter more every year. OpenTelemetry emits all five; one trace_id correlates them.

p. 49

> Three classic signals plus two that are now first-class in OpenTelemetry. Baggage carries request-scoped context (tenant_id, user_tier) along the trace; profiles tell you which function is burning CPU or holding locks, continuously, in production. For C++ all five are supported by the OpenTelemetry C++ SDK and OTLP. Profiling specifically is where C++ shines — eBPF-based profilers like Parca or Pyroscope work natively against C++ binaries with DWARF symbols and don't need a runtime agent. Most teams turn on profiling in C++ services much earlier than they would in JVM or Python because the data is so much more directly actionable.

## [062] OBSERVABILITY · What each signal answers — and when to reach for it (sldId 317)

- Traces — 'where did the time go in this request, which hop failed?' Reach for it when debugging latency or a specific failed request. Stored in Tempo / Jaeger.
- Metrics — 'what is the aggregate rate / error / latency trend, is it getting worse?' RED for request-driven services; USE for resources. Stored in Prometheus / Mimir.
- Logs — 'what exactly happened in this component at this instant?' Structured (JSON via spdlog), keyed by trace_id. Stored in Loki / ELK.
- Baggage — 'carry a value (tenant_id, user_tier) along the whole request so downstream services and their telemetry can use it.' Set once at the edge, readable everywhere.
- Profiles — 'which function is burning CPU / allocating memory / holding locks, continuously, in production?' Pyroscope / Parca with DWARF symbols on the C++ binary.
- Discipline: traces + metrics + logs always; add baggage when downstream needs request-scoped context; add profiling when you have CPU/memory mysteries a trace can't resolve.

p. 50

> One question per signal. The trick is knowing which signal to reach for first. Latency for one request → trace. Latency trend across all requests → metric. The exact string that came back from this DB call → log. 'Why is this slow for this tenant?' → baggage filter on the trace. 'Why is steady-state CPU 30% higher than last week?' → continuous profile diff. C++ specifically: spdlog with the stdout sink is the standard log path; the spdlog sink in opentelemetry-cpp-contrib bridges into the OTel pipeline. Never spdlog::basic_logger_mt: that's a file sink which dies on a read-only root filesystem (the 'logs to stdout, not a file' rule of cpp-statelessness Doc 08, patterncatalyst.github.io/cpp-statelessness/docs/08-ephemeral-filesystem/).

## [063] OBSERVABILITY · Auto-injection vs. instrumentation — three distinct things (sldId 318)

- Manual instrumentation — you write the spans. tracer->StartSpan(...), span->SetAttribute(...), span->AddEvent(...). Needed for business operations the libraries can't know about ('reserve_stock', 'score_fraud').
- Auto-instrumentation — a library wraps known frameworks for you. For C++: opentelemetry-cpp-contrib ships log bridges (spdlog, glog, Boost.Log, log4cxx) and nginx and Apache httpd modules; gRPC, Drogon, librdkafka and libpq spans are written by hand.
- Auto-injection — the OpenTelemetry Operator mutates pods at admission to inject an agent. Native auto-injection support for C++ is more limited than for JVM or Python; in practice you ship the OTel SDK statically linked into the binary and configure via env vars.
- How they layer for C++: link the OTel SDK into your binary → add manual middleware spans for Drogon/Kafka boundaries → add manual business spans on top. Less framework auto-coverage than Python; more deterministic.
- Trade-off: manual costs effort but produces precise, low-noise traces. Auto in C++ covers fewer frameworks than in Python/JVM, so most C++ services run mostly-manual with a thin instrumentation library.

p. 51

> Where C++ OTel auto-instrumentation stands. Python and JVM have far more ready-made auto-instrumentation libraries; for C++, opentelemetry-cpp-contrib covers logging bridges and the nginx and httpd modules, while gRPC, Drogon, librdkafka, libpq and most C++ frameworks need the boundary spans written by hand (opentelemetry-cpp's examples/grpc shows the context propagation). This is more work but produces cleaner traces: fewer spurious framework spans, and every span you see exists for a reason. Auto-injection: the OTel Operator's auto-injection (where Kubernetes mutates the pod to add a sidecar agent) is JVM/Python/Node-first; C++ services typically link the SDK in and configure with OTEL_EXPORTER_OTLP_ENDPOINT and friends from env vars. Cleaner deploy story either way.

## [064] OBSERVABILITY · Auto-instrument Drogon with OpenTelemetry (sldId 319)

[chip] c++ · OpenTelemetry

```c++
// otel_init.cc — initialise once in main(), before serving traffic
#include <opentelemetry/sdk/trace/tracer_provider.h>
#include <opentelemetry/exporters/otlp/otlp_http_exporter_factory.h>
#include <opentelemetry/sdk/trace/batch_span_processor_factory.h>

namespace otel = opentelemetry;
void init_tracing(std::string_view service_name) {
  auto exporter  = otel::exporter::otlp::OtlpHttpExporterFactory::Create({});
  auto processor = otel::sdk::trace::BatchSpanProcessorFactory::Create(   // batch, not simple
      std::move(exporter), { /* max_queue_size, schedule_delay */ });
  auto provider  = otel::sdk::trace::TracerProviderFactory::Create(std::move(processor));
  otel::trace::Provider::SetTracerProvider(std::move(provider));
}

// Drogon middleware — one span per request, attributes per route
Task<> trace_middleware(HttpRequestPtr req, auto next) {
  auto tracer = otel::trace::Provider::GetTracerProvider()->GetTracer("order-service");
  auto span   = tracer->StartSpan(req->getPath());
  auto scope  = tracer->WithActiveSpan(span);
  span->SetAttribute("http.method", req->getMethodString());
  co_await next(req);                                // child spans nest naturally
  span->End();
}
```

Init once in main(); add boundary middleware for HTTP / gRPC / Kafka; manual spans for business operations. trace_id flows automatically downstream.

p. 52

> Two parts, both essential. init_tracing() goes in main() before any handlers register; it sets the global TracerProvider with the Batch span processor (never Simple, which flushes synchronously and crushes throughput). The Drogon middleware creates one parent span per request and registers it as the active span; any child spans you start inside the handler nest naturally because OTel's Context API tracks active spans per-thread. Outbound calls do not pick up the context on their own: inject it with the W3C trace-context propagator into a carrier (the gRPC ClientContext metadata, the Kafka message headers). opentelemetry-cpp's examples/grpc shows the carrier; opentelemetry-cpp-contrib has no gRPC interceptor.

## [065] OBSERVABILITY · How correlation works — context propagation (sldId 320)

The trace context rides in-band with the request (W3C traceparent). The same trace_id at every hop is what stitches the story.

p. 53

> Trace propagation in one mental model: every protocol header carries a traceparent. HTTP request headers (W3C traceparent), gRPC metadata (grpc-trace-bin in some setups, but most use the standard W3C header), Kafka record headers (the OTel Kafka extension adds them automatically when configured). Each receiver extracts the parent context and creates its own span as a child. C++ specifically: the OTel context propagators (HttpTraceContext, B3) are configured once via SetGlobalPropagator at startup; from then on, your Drogon middleware extracts inbound context from request headers and the gRPC OTel interceptor injects outbound context into ClientContext metadata. The work is wiring once; the runtime behaviour is automatic.

## [066] OBSERVABILITY · Baggage in practice — carry request context downstream (sldId 321)

[chip] c++ · OpenTelemetry

```c++
// Set baggage at the edge — it rides the whole trace, every downstream hop
#include <opentelemetry/baggage/baggage.h>
#include <opentelemetry/context/context.h>

namespace otel = opentelemetry;
Task<> baggage_middleware(HttpRequestPtr req, auto next) {
  auto bag = otel::baggage::Baggage::GetDefault()
      ->Set("tenant_id", req->getHeader("X-Tenant").value_or("unknown"))
      ->Set("user_tier", lookup_tier(req));
  auto ctx   = otel::baggage::SetBaggage(
      otel::context::RuntimeContext::GetCurrent(), bag);
  auto token = otel::context::RuntimeContext::Attach(ctx);
  co_await next(req);                              // propagates automatically
}

// Read baggage anywhere downstream — even in a Kafka consumer
void handle_event(const auto& msg) {
  auto bag = otel::baggage::GetBaggage(
      otel::context::RuntimeContext::GetCurrent());
  auto tenant = bag->GetValue("tenant_id").value_or("unknown");
  otel::trace::Tracer::GetCurrentSpan()
      ->SetAttribute("tenant_id", tenant);         // filterable in Tempo
}
```

Set once at the edge; read anywhere downstream. Pin to the span as an attribute to filter traces by tenant_id.

p. 54

> Baggage is a separate concern from trace context — they ride together but carry different data. Trace context (traceparent) tells you 'this is part of trace X'; baggage carries named key-value pairs that downstream services can read. Set once at the edge in a middleware (tenant_id from a header, user_tier from a lookup), and it propagates with the active context through Drogon → gRPC → Kafka → downstream consumer. To filter traces by these values, pin baggage onto the current span as an attribute (last three lines) — baggage itself isn't queryable in Tempo, but span attributes are. Watch the cardinality of what you put in baggage — every baggage entry rides every request as a header. Tenant_id is fine; user-agent strings are not.

## [067] OBSERVABILITY · A single trace stitches the whole request (sldId 322)

One trace_id propagates from the edge REST call through gRPC, Kafka and the consumer — five services, one story.

p. 55

> This is what 'instrument once, correlate everything' looks like. One client request enters at the edge, hits order-service over REST, fans out via gRPC to inventory and payment, emits order.placed to Kafka, which notification-service consumes. One trace_id binds the whole story. Operational reality: in Tempo / Grafana you click the latency outlier in your dashboard, see the trace spanning all five services, see which hop spent the time, drop into the logs for that exact span (correlated by trace_id), and you're debugging in seconds instead of minutes. This is the payoff for the instrumentation work — it's not free, but every production incident pays it back.

## [068] OBSERVABILITY · Sampling — head vs. tail (sldId 323)

You can't store every trace at scale. Head decides at the start (cheap, blind); tail decides at the end (smart, costly).

p. 56

> Sampling is the only reason a trace pipeline scales — full retention at production volume is prohibitively expensive in storage and bandwidth. Two families: head sampling decides at the start of the trace (cheap, but blind, since you don't yet know if this trace will fail or be slow); tail sampling decides at the end, after buffering the whole trace at the Collector (smart: keep all errors, all slow traces, plus a percentage of the rest).

## [069] OBSERVABILITY · Choosing a sampling strategy (sldId 324)

- Probabilistic (head) — keep a fixed percentage (e.g. 10%). Simplest; predictable volume; blind to errors. Good baseline for high-traffic, low-stakes services.
- Rate-limiting (head) — keep at most N traces/sec per service. Protects your backend from traffic spikes; good when load is bursty.
- Parent-based (head) — honour the upstream's sampling decision (carried in traceparent flags). Essential: stops a trace being sampled at A but dropped at B, which gives you broken half-traces.
- Tail-based (Collector) — buffer the whole trace, then keep by rule: all errors, all traces over a latency threshold, rare routes, plus a small % of the rest. Gold standard; costs Collector memory + CPU.
- Recommended setup: parent-based head sampling at 1–10% baseline, plus tail sampling at the Collector to guarantee every error and slow trace is kept.
- Don't sample metrics the way you sample traces (metrics aggregate everything). Keep logs in full with retention limits, or sample on a separate policy keyed by trace_id.

p. 57

> Sampling is a per-pipeline configuration decision, but the rules are universal. Five named strategies; the production answer is almost always parent-based head + tail at the Collector. C++ specifics: the OpenTelemetry C++ SDK supports all of these sampler types (AlwaysOnSampler, AlwaysOffSampler, ParentBasedSampler, TraceIdRatioBasedSampler), configured at TracerProvider construction time. Tail sampling lives in the Collector config, not in your C++ code. The metrics-vs-traces note matters: don't get confused and apply head sampling to metrics. Metrics are aggregates over every request; if you sample at 10%, your error-rate metric is off by 10x. Logs are separate again — keep them in full but on a shorter retention than traces, and sample by trace_id so a kept trace keeps its logs.

## [070] OBSERVABILITY · Prove it with simple tools before you ship (sldId 325)

- curl / Postman — exercise REST contracts and inspect status codes, headers and pagination.
- hey — quick HTTP load to watch latency, error rate and the KEDA http-add-on scale the Drogon service from zero.
- ghz — load-test gRPC endpoints and confirm timeouts (gRPC ClientContext::set_deadline) and Istio retries behave under pressure.
- GraphQL Playground — explore the composed schema and watch the gateway fan out across services in Tempo.
- Kiali — read the live service-mesh topology, mTLS status and request flow during a load test.
- perf / eBPF (Parca, Pyroscope) — profile the C++ binary continuously; flame graphs against DWARF symbols make hotspots obvious.
- Apicurio UI — visually inspect the registered contracts and their compatibility rules before you push a breaking change.

p. 58

> Six tools that pay for themselves before you ever hit production. The pattern across all of them: exercise the system from outside, watch what the platform reports back, fix the gap between expectation and observation. C++ specific: perf and eBPF-based profilers are far more useful in C++ than in managed runtimes — flame graphs against DWARF symbols show you the actual function names, no interpreter or JIT layer to peel back. Pyroscope's eBPF profiler can attach to a running Drogon binary with zero source changes and produce continuous flame graphs in Grafana. Worth turning on in staging from day one.

## [071] Security (sldId 326)

12

Defence in depth, in layers.

> Section 12 divider: Security. Defence in depth, in layers.

## [072] SECURITY · The 4 C's of cloud-native security (sldId 327)

Cloud → Cluster → Container → Code. Concentric layers, each layer protects what is inside.

p. 59

> The 4 C's model (Cloud, Cluster, Container, Code) is the CNCF's framing for defence in depth. Each layer protects what's inside it; controls at the wrong layer give false confidence — network ACLs can't save you from SQL injection in your handler. For C++ specifically, the Container and Code layers carry slightly different idioms than managed runtimes: minimal base images get even smaller (no JVM, no Python interpreter — a statically-linked C++ binary in distroless or scratch is realistic), and the Code layer gets help from compiler hardening flags (-fstack-protector-strong, -D_FORTIFY_SOURCE=2, PIE/ASLR) and sanitisers (ASan, UBSan) in CI. The Container and Code controls compound.

## [073] SECURITY · The 4 C's — what each layer enforces, and who owns it (sldId 328)

- Cloud — IAM (least privilege), VPC isolation, KMS for keys, audit logging, region & data-residency controls. Owner: platform / cloud admin.
- Cluster — RBAC, NetworkPolicy (default-deny + targeted allows), Pod Security Standards (restricted), admission control (Gatekeeper / Kyverno), secret encryption at rest. Owner: platform / SRE.
- Container — minimal base images (distroless, UBI-minimal; statically linked C++ can run on scratch), non-root, read-only rootfs, image signing (Cosign), vuln scanning (Trivy). Owner: app + platform.
- Code — parameterised queries (libpq with $1, $2, never string concatenation), input validation at the trust boundary, dependency scanning (Conan + OSV-Scanner), no secrets in source, threat modeling. Owner: app team.
- C++-specific code controls: ASan/UBSan in CI; -fstack-protector-strong + -D_FORTIFY_SOURCE=2 + PIE in release builds; std::string_view for non-owning views (no buffer-overrun escape).
- Cross-cutting: observability (who did what), incident response, threat modeling per service, regular dependency updates. A control at the wrong layer is the most common source of false confidence.

p. 60

> The 4 C's in detail with C++-specific notes added at each layer where they matter. Container: a C++ binary compiled with all dependencies statically linked can run on gcr.io/distroless/static-debian12 or even FROM scratch — image sizes in the single-digit MB are routine, attack surface is minimal. Code: the C++ controls (compiler hardening flags, sanitisers in CI) catch a class of bugs that managed runtimes don't have at all but the C++ ecosystem has tooling for. Pin them in your CMake preset and they're free thereafter. The cross-cutting rule is the headline: defence in depth means controls at every layer, not just the one you find convenient.

## [074] SECURITY · Seven patterns to know (sldId 329)

- Sidecar — move security concerns out of the app into a companion process. mTLS, JWT, audit, rate-limiting belong there.
- Valet Key — hand the client a short-lived signed token to access a resource directly. Less app proxying, less attack surface.
- Strangler Fig (for security modernisation) — encapsulate legacy auth behind an API gateway, replace pieces over time.
- Zero-Trust / Identity-Aware Proxy — every request authenticated and authorised. Perimeter trust is dead.
- Policy-as-Code — security gates declared in Git, evaluated at admission and at build. No human runs a checklist.
- Bulkhead — isolate resources so one failure (or compromise) cannot starve or cascade into others.
- Claim-Check — send a reference, not the payload. Keeps PII out of message bus history and limits the blast radius if a topic leaks.
- The seven appear in different layers and combine. Each slide that follows shows the pattern, then implementation — platform config where it's mostly YAML, C++ code where it's mostly code.

p. 61

> Seven security patterns, each with a concept and an implementation. They're not a checklist; production systems combine them per concern. The framing for this section: each pattern gets a concept slide (diagram) and an implementation slide (YAML or C++ code). Where it's platform configuration (Sidecar, Policy-as-Code, Zero-Trust mostly), the implementation is YAML and language-neutral. Where it's app code (Valet Key, Bulkhead, Claim-Check), we show idiomatic C++.

## [075] SECURITY · SIDECAR · Sidecar pattern — push security out of the app (sldId 330)

mTLS, JWT validation, rate limiting, audit logging — a companion process in the same Pod handles them all.

p. 62

> The sidecar is the security pattern that covers the most ground in a Kubernetes deployment. Istio's istio-proxy (Envoy) sidecar handles mTLS, JWT validation, rate limiting, and audit logging uniformly across every workload — your C++ binary, your Java binary, your Python binary all get the same security guarantees with the same config. Cost: one extra container per Pod (~20-50 MB memory, sub-second startup). For a fleet of C++ services where each binary is itself only a few MB, the sidecar can be larger than the app. That's fine — the security guarantee is what you're paying for. The app never re-implements what the sidecar does. No JWT library in your C++ binary, no mTLS in your code. The sidecar does it; the app reads trusted headers.

## [076] SECURITY · SIDECAR · Reading the sidecar's trusted headers (sldId 331)

- The sidecar handles mTLS, JWT validation, policy decisions — the app trusts the headers the sidecar attaches and reads them as plain values.
- X-Forwarded-Client-Cert — the validated client identity from mTLS, includes the SPIFFE ID (spiffe://cluster.local/ns/orders/sa/order-service). The app must reject requests that don't have it.
- JWT claims — the sidecar validates the signature, then passes claims forward as headers. The app reads sub, aud, scope; it never re-validates the signature.
- X-Request-Id — attached by the sidecar for traceability. Log it; propagate it to downstream calls; correlate with audit logs.
- Trust only when the sidecar is in front. Direct-to-Pod traffic (port-forward, debugging) could spoof these headers — use a NetworkPolicy to ensure traffic only enters via the sidecar's mTLS port.
- C++ in Drogon: read req->getHeader("X-Forwarded-Client-Cert") in a guard middleware; reject the request with 401 if missing. jwt-cpp stays unused — the sidecar did it. Examples: Istio Envoy, Linkerd2-proxy, OPA Sidecar. All Apache 2.0.

p. 63

> The trust contract between the app and the sidecar. The sidecar is the auth perimeter; the app reads the conclusions it reached. For C++ this changes what jwt-cpp is for: it is the deck's JWT library, but in a sidecar-fronted deployment its only job is to handle internal token minting or decoding tokens from contexts the sidecar didn't see. The default case, validating tokens from the client, is the sidecar's job, not yours. Always pair the sidecar headers with a NetworkPolicy. If a developer port-forwards or a sidecar fails injection, traffic could reach the Pod without going through the sidecar, and the headers become spoofable. The NetworkPolicy enforces that direct Pod-to-Pod traffic is blocked.

## [077] SECURITY · VALET KEY · Valet key pattern — short-lived signed token, direct access (sldId 332)

App mints a scoped, time-bound token; client uses it directly against the resource. App never proxies the bytes.

p. 64

> The valet key pattern keeps bytes out of your service's request path. Instead of uploading a file through the C++ service to object storage, the service hands the client a signed ticket with a short expiry, scoped to one key and one operation; the client uploads directly. Why this matters more in C++: a single Drogon worker thread occupied for 30 seconds of upload time is a thread you can't use for other requests. The valet key pattern eliminates that — the C++ service mints the ticket in microseconds, the upload goes directly to the object store, and the thread is back in the pool immediately. The math compounds in any system handling user-uploaded content.

## [078] SECURITY · VALET KEY · Valet key — scoped, time-bound, op-restricted (sldId 333)

[chip] c++ · Drogon + jwt-cpp

```c++
// valet.hpp (excerpt), examples/12-security/cpp: the valet key is an HS256 JWT (jwt-cpp)
inline Minted mint(const std::string& secret, const std::string& resource,
                   const std::string& operation,
                   std::chrono::seconds ttl = std::chrono::minutes(5)) {   // time-bound
    const auto now = std::chrono::system_clock::now();
    const auto exp = std::chrono::time_point_cast<std::chrono::seconds>(now + ttl);
    auto token = jwt::create()
                     .set_type("JWT")
                     .set_issuer(kIssuer)                         // "order-service"
                     .set_issued_at(now)
                     .set_expires_at(exp)
                     .set_payload_claim("res", jwt::claim(resource))   // one object
                     .set_payload_claim("op", jwt::claim(operation))   // one operation
                     .sign(jwt::algorithm::hs256{secret});
    return {std::move(token), exp.time_since_epoch().count()};
}
// verify(): HS256 pinned ("none" and RS256 never reach the verifier), then iss, res, op
const auto decoded = jwt::decode(token);
if (decoded.get_algorithm() != "HS256") return false;
jwt::verify().allow_algorithm(jwt::algorithm::hs256{secret}).with_issuer(kIssuer)
    .with_claim("res", jwt::claim(resource)).with_claim("op", jwt::claim(operation))
    .verify(decoded);                                  // signature + exp; throws on failure
```

The Drogon worker thread is free in microseconds; the upload happens directly to object storage with a signature that cannot be forged or extended.

p. 65

> The handler mints a ticket that authorises one operation (GET or PUT) on one resource for five minutes; after that it is worthless. In Example 12 the ticket is an HS256 JWT signed with jwt-cpp: the res and op claims carry the scope, exp the expiry, iss the issuer. POST /valet-key returns the resource, the operation, the expiry and the token.
>
> The verifier (GET /verify-valet in the example, the storage gateway in a real system) reads the header first and rejects anything but HS256, so alg=none or an RS256 token never reaches the verifier; then jwt::verify checks the signature, the expiry, the issuer and the res and op claims, and the exp must equal the expiry the client presents. Any mismatch is a 403.
>
> The application stays out of the data path: the client presents the ticket to the storage side directly. Most object stores, open-source ones included, accept signed URLs of the same shape: the method, the object key and the expiry signed into the URL. A user-scoped resource path also lets the store's policy restrict each user to their own prefix as defence in depth. What this saves: the Drogon worker thread is back in the pool before the upload starts.

## [079] SECURITY · STRANGLER FIG · Strangler Fig for security modernisation (sldId 334)

- Use case: encapsulate legacy authentication (LDAP-only, HTTP Basic, hardcoded session cookies) behind a modern API gateway, then replace the legacy auth path one service at a time.
- Step 0: introduce the gateway in front of the monolith. Clients hit the gateway, which forwards to the legacy auth. Day-zero behaviour unchanged.
- Step 1: the gateway terminates TLS, validates JWTs from a modern IdP (Keycloak, Dex), and translates to whatever the legacy expects; it speaks both languages.
- Step 2: per route, switch the gateway from 'forward legacy headers' to 'forward only the JWT claims to the new service'. Legacy auth is no longer in the path for that route.
- Step 3: when no routes still need legacy auth, remove it.
- Bounded blast radius: each route's auth migration is a config change in the gateway, reversible without a release.
- For C++ services: the new auth path is sidecar-validated (see the sidecar pattern); your Drogon code reads X-Forwarded-Client-Cert and JWT claim headers, never the legacy session cookie. The migration touches the gateway, not the service.

p. 66

> Strangler Fig applied to authentication, not business logic. The pattern is the same as App K (monolith decomposition): proxy, redirect, replace, retire. The key insight: the gateway is the translator. It speaks both the modern protocol (OIDC + JWT) and the legacy protocol (whatever the monolith expects), per route. New C++ services never need to know the legacy auth existed. Why this works incrementally: each route is a config change. If a route's migration breaks, you flip it back in seconds. Compare that to the Big Bang migration where you replace auth everywhere at once and find out at 3am what you forgot.

## [080] SECURITY · ZERO-TRUST · Zero-trust / Identity-Aware Proxy (sldId 335)

Every request authenticated and authorised, on every hop. Perimeter trust is dead. SPIFFE inside, IAP at the edge.

p. 67

> Zero-trust is the default posture for any system with users you don't control. The perimeter (VPN, IP allow-list) is no longer the auth boundary — every request, on every hop, is authenticated and authorised. Two layers in this model. At the edge, an Identity-Aware Proxy (Pomerium or OAuth2 Proxy) terminates TLS, validates identity against your IdP (OIDC), applies the route's access policy, and issues a JWT that downstream services see. Inside the cluster, Istio + SPIFFE assigns every workload an X.509 identity, and every service-to-service call is mutually authenticated. For C++ services this is all platform — your Drogon binary reads X-Forwarded-Client-Cert and JWT claims and never touches OIDC or X.509 directly.

## [081] SECURITY · ZERO-TRUST · Implementing zero-trust (sldId 336)

- Edge (IAP): Pomerium or OAuth2 Proxy in front of an OIDC provider such as Keycloak — terminate TLS, validate identity (OIDC against your IdP), apply the route's access policy, issue a JWT downstream services see in X-Forwarded-* headers.
- Inside the cluster (mTLS): Istio + SPIFFE assigns every workload an X.509 cert identifying its service account (spiffe://cluster.local/ns/orders/sa/order-service). Every service-to-service call is mutually authenticated.
- Authorization: Istio AuthorizationPolicy declares 'order-service can call payment-service /charge but nothing else, only when carrying a valid customer JWT.' Per-workload, fine-grained, declarative.
- Policy decisions: OPA / Cedar evaluate context (user, time, device, target, action) and return allow/deny. Out-of-process so policy can change without redeploying every service.
- C++ app-side discipline: read X-Forwarded-Client-Cert in a guard middleware; reject calls that arrive without it; log every authorization decision (the audit trail lives in your logs, not just the sidecar's).
- License notes: Istio, SPIFFE/SPIRE, OPA, Cedar — all open source (Apache 2.0). Pomerium (Apache 2.0) and OAuth2 Proxy (MIT) are open source too.

p. 68

> Zero-trust is a posture implemented across four layers, not one product. Each layer is open source and well-maintained; this is real, not aspirational. C++-specific note in the fifth bullet: even though the sidecar handles the work, your audit log entries in spdlog should record who made each request (read from JWT claims) and what they were authorised to do. The sidecar's logs are separate; your app's logs are what your team grep through during incident response. Make them informative.

## [082] SECURITY · POLICY-AS-CODE · Policy-as-Code — security gates in Git (sldId 337)

OPA Gatekeeper / Kyverno enforce declarative policies at admission. CI runs the same policies pre-merge.

p. 69

> Policy-as-Code is the discipline that makes every other security pattern enforceable. Without it, there's a checklist somewhere, and somebody is supposed to run through it, and they don't, and a Pod ships without a non-root user, and three months later you find out. With it, the cluster's admission controller rejects the Pod before it ever runs, and the CI pipeline rejects the manifest before the merge. For a C++ shop the policy authoring is the same as for any other shop (Rego or Kyverno-flavoured YAML), but the policies often look at C++-specific concerns: image must come from registry.acme.com, base image must be distroless, must run non-root, must specify CPU/memory limits.

## [083] SECURITY · POLICY-AS-CODE · OPA Gatekeeper ConstraintTemplate (Rego) (sldId 338)

[chip] yaml · Gatekeeper

```yaml
# ConstraintTemplate — reusable policy logic in Rego
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata: { name: k8srequiresignedimages }
spec:
  crd:
    spec:
      names: { kind: K8sRequireSignedImages }
      validation:
        openAPIV3Schema:
          properties: { allowedRegistries: { type: array, items: { type: string } } }
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: |
      package k8srequiresignedimages
      violation[{"msg": msg}] {
        container := input.review.object.spec.containers[_]
        not startswith(container.image, input.parameters.allowedRegistries[_])
        msg := sprintf("image %v not from an allowed registry", [container.image])
      }

# A separate Constraint resource binds the template to actual Pods with
# allowedRegistries=["registry.acme.com/", "quay.io/redhat/"]. Same Rego;
# different param values per environment.
```

Policy in Git, enforced at admission. CI runs the same policy pre-merge via conftest — feedback loop in seconds, not after deployment.

p. 70

> Two-document pattern, identical to the Istio VirtualService/DestinationRule split we saw in §2. The ConstraintTemplate defines the reusable logic in Rego; the Constraint applies the template to actual resources with specific parameters. What this catches in a C++ deployment: an unsigned image shipped from a developer workstation, a Pod that pulls from Docker Hub instead of the internal registry, a CI bypass. The admission controller refuses the Pod — it never runs. Run the same policy in CI via conftest before the merge: same Rego, evaluated against the proposed manifest. Feedback at PR time is much cheaper than feedback at deploy time. Kyverno is the YAML-only alternative if you want to skip learning Rego; same admission control story.

## [084] SECURITY · BULKHEAD · Bulkhead — isolate resources, bound the blast radius (sldId 339)

Per-tenant / per-call / per-priority pools. One tenant's storm cannot starve others. One compromise cannot cascade.

p. 71

> The bulkhead pattern (named for ship hull compartments) isolates resources so a failure or abusive load in one partition can't drain the whole pool. The classic example: a tenant's retry storm or a buggy customer integration shouldn't be able to consume every worker thread in your service and starve everyone else. For C++ specifically: bulkheads can be enforced at multiple levels — thread pool, connection pool, memory arena. PMR per-request arenas bound memory per request (cpp-statelessness Doc 03, patterncatalyst.github.io/cpp-statelessness/docs/03-pmr/); bulkheads bound concurrency per tenant. Both matter, and both are straightforward to implement in C++.

## [085] SECURITY · BULKHEAD · Per-tenant bulkheads with an atomic counter (sldId 340)

[chip] c++ · std::atomic

```c++
// examples/12-security/cpp/order-service/src/main.cpp (excerpts)
struct TenantBulkhead {                                     // a lock-free counter per tenant
    static constexpr int CAPACITY = 5;                        // 5 concurrent per tenant
    std::atomic<int> active{0};
    bool try_acquire() {
        int current = active.load();
        while (current < CAPACITY) {
            if (active.compare_exchange_weak(current, current + 1)) return true;
        }
        return false;                                         // full: refuse, don't queue
    }
    void release() { active.fetch_sub(1); }
};

// POST /orders (a coroutine handler): A's storm can't drain B's capacity
auto& bulkhead = bulkhead_manager.get_or_create(tenant);     // map + mutex, one per tenant
if (!bulkhead.try_acquire()) {
    co_return reply(k429TooManyRequests, detail("tenant bulkhead full"));
}
BulkheadPermit permit{bulkhead};   // released when the handler finishes, however it finishes
```

5 concurrent requests per tenant; the sixth gets 429 at once instead of waiting in a queue.

p. 72

> The bulkhead from Example 12: one TenantBulkhead per tenant, created on first use in a map guarded by a mutex. Each holds a lock-free std::atomic<int> with a compare-and-swap loop, so taking a slot never blocks; there is no maintained C++ resilience library on ConanCenter to take it from.
>
> A refused request gets 429 with tenant bulkhead full at once: refuse, don't queue, because a queue in front of a saturated tenant becomes the bottleneck. The order handler is a Drogon coroutine, and a BulkheadPermit gives the slot back however the handler ends. Per-tenant connection pools at the libpq or gRPC layer are a separate bulkhead: the counter caps concurrency, the pool caps sockets.

## [086] SECURITY · CLAIM-CHECK · Claim-check — send a reference, not the payload (sldId 341)

Large or sensitive payload goes to a secure store; the message bus carries only an opaque token to fetch it.

p. 73

> Claim-check keeps the message bus small and the PII contained. Instead of publishing {order: {customer_email, payment_card, address, items: [...]}} to Kafka, the producer writes the payload to encrypted object storage and publishes only {claim_id: 'abc-123', uri: 'https://objects.internal/claims/abc-123'} to Kafka. Two wins: (1) the message bus stays small — Kafka topics with 30-day retention don't become PII archives. (2) Access control on the payload is in object storage, where you can use per-object access policies, KMS keys, audit logs — Kafka topic ACLs are coarser. The cost: an extra fetch hop in every consumer. Worth it when the payload is large or sensitive; overkill for small public facts like order.placed events with just IDs.

## [087] SECURITY · CLAIM-CHECK · Producer mints claim, consumer fetches payload (sldId 342)

[chip] c++ · rdkafka++ + jwt-cpp

{% raw %}
```c++
// claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key
void publish_with_claim(const std::string& order_id, const std::string& body) {
  const auto key = "payloads/" + order_id;
  store_.put(key, body, /*encrypt=*/true);                     // 1. store: encrypted, ACL'd
  auto ticket = cndp::valet::mint(VALET_SECRET, key, "GET", std::chrono::minutes(15));
  auto claim = nlohmann::json{{"order_id", order_id},
                              {"uri", "https://objects.internal/" + key},
                              {"token", ticket.token}, {"expires", ticket.expires}}.dump();
  producer_->produce("order.documents", RdKafka::Topic::PARTITION_UA,
                     RdKafka::Producer::RK_MSG_COPY, claim.data(), claim.size(),
                     order_id.data(), order_id.size(), 0, nullptr);   // 2. claim only
}
// Consumer: consume the claim, fetch the payload, then handle
std::unique_ptr<RdKafka::Message> msg(consumer_->consume(100));
if (msg->err() == RdKafka::ERR_NO_ERROR) {
  auto claim = nlohmann::json::parse(payload_of(*msg));
  auto body = store_.get(claim["uri"].get<std::string>(),
                         claim["token"].get<std::string>());     // the store checks the ticket
  handle(body);                                                // PII never touched the topic
  consumer_->commitSync(msg.get());                            // after handle
}
```
{% endraw %}

Payloads sit in encrypted object storage; Kafka carries only the claim and its ticket. PII never crosses the broker.

p. 74

> Two halves. The producer writes the payload to an encrypted object store under payloads/<order id>, mints a GET-only ticket for that key with Example 12's cndp::valet::mint (15 minutes), and publishes only a small claim (order id, URI and the ticket) to order.documents with rdkafka++. The PII is never on Kafka's wire.
>
> The consumer decodes the claim, fetches the payload with the token, processes it, then commits the offset (at-least-once delivery, so the handler must be idempotent). The store verifies the ticket before it serves the object and logs every fetch with the principal, an audit trail plain Kafka does not give.
>
> Size the ticket's lifetime to the consumer's worst-case lag. No runnable example covers claim-check; store stands for any encrypted object store. Set a lifecycle rule that expires claims after the retention period, so a replayed message points at nothing.

## [088] SECURITY · Choosing the right pattern (sldId 343)

- Sidecar — when you want one security policy uniformly across every workload, regardless of language. Cost: an extra container per Pod.
- Valet Key — when clients need direct access to a large or specific resource (file upload, image download). Cost: storage system must validate tokens (most do).
- Strangler Fig (auth) — when you have legacy authentication you can't change all at once. Cost: a gateway running translation logic during the transition.
- Zero-Trust / IAP — the default model for any system with users outside your immediate control. Cost: mTLS everywhere has real CPU + ops overhead.
- Policy-as-Code — always. The cost of not having it (drift, inconsistency, forgotten reviews) is much higher than the cost of adopting OPA / Kyverno.
- Bulkhead — any multi-tenant system, any system with mixed-priority workloads. Cost: pools are extra moving parts to size and tune.
- Claim-Check — when payloads carry PII or are large enough to bloat the message bus. Cost: an extra fetch hop and the store-and-bus must agree on token semantics.
- Most production systems combine all of these, not as a checklist but as a decision per concern.

p. 75

> Each pattern has a concrete trigger condition. The headline at the bottom: production systems use combinations — sidecar + zero-trust + policy-as-code is the table-stakes baseline, with valet-key + bulkhead + claim-check added wherever the workload calls for them. For C++ specifically, the patterns that have C++ code (valet-key, bulkhead, claim-check) are the ones the dev team owns; the others (sidecar, zero-trust, policy-as-code) are platform team territory. The split tracks ownership, not difficulty.

## [089] SECURITY · Take-aways and references (sldId 344)

- Defence in depth across the 4 C's: cloud, cluster, container, code. A control at the wrong layer is false confidence.
- Identity is the new perimeter. mTLS + SPIFFE inside; IAP / OIDC at the edge. Every request authenticated and authorised, on every hop.
- Policy in Git, enforced by the cluster. OPA Gatekeeper or Kyverno at admission; conftest in CI for early feedback.
- PII never crosses your message bus in cleartext. Claim-check or end-to-end encrypt.
- Isolate by tenant, by call, by priority. Bulkheads bound the blast radius of both incidents and outages.
- C++-specific: ASan/UBSan in CI; -fstack-protector-strong + -D_FORTIFY_SOURCE=2 + PIE in release; the sidecar handles auth so jwt-cpp stays out of the hot path; Example 12 mints valet-key tickets with jwt-cpp, and a claim check carries the same ticket.
- References: NIST SP 800-204A; CNCF Cloud Native Security Whitepaper; OWASP API Security Top 10; OpenSSF SLSA; Istio AuthorizationPolicy docs; OPA Gatekeeper library. Open-source pillars all Apache 2.0.

p. 76

> Five take-aways for security, plus one C++-specific line. The headline: security is layered, platform-driven, and Git-tracked. Your C++ code participates by reading trusted headers, implementing the three app-side patterns (valet-key, bulkhead, claim-check), and emitting audit logs. The platform does the rest.

## [090] Anti-Patterns (sldId 345)

13

Most outages re-couple what you separated.

> Section 13 divider: Anti-Patterns. Most outages re-couple what you separated.

## [091] ANTI-PATTERNS · How cloud-native API systems go wrong (sldId 346)

Each anti-pattern reintroduces the coupling the architecture worked to remove.

p. 77

> Every anti-pattern in this section is the same shape: coupling sneaking back in. The distributed monolith looks like microservices until you try to deploy one without the others. Shared databases look like fast development until two teams change the same table. Synchronous chains look efficient until one slow hop takes the whole flow down. For C++ specifically, the temptation profile is slightly different from Python or JVM. C++ developers reach for in-process shared state readily because it's cheap; the discipline of 'in-process is per-service, never cross-service' has to be enforced explicitly. cpp-statelessness covers the per-service in-process state patterns, PMR arenas and RAII connection pools (patterncatalyst.github.io/cpp-statelessness/docs/04-process-scoped-state/); the anti-pattern is when that state becomes a shared assumption across services.

## [092] ANTI-PATTERNS · The heuristics that keep you out of them (sldId 347)

- If two services must deploy together, they are one service — merge them or fix the contract.
- One writer per dataset; everyone else reads through the API or subscribes to its events.
- Push aggregation to a gateway/BFF; forbid service-to-service call chains deeper than one hop.
- No contract in the registry, no merge — and every retry has a timeout and a bound.
- If you can't trace it, you can't run it: observability is a launch requirement, not a follow-up.
- C++-specific: no shared mutable state across services, ever — not via shared memory, not via mmap'd files, not via a 'shared utility binary'. Each C++ service owns its process space.

p. 78

> Six heuristics — five universal, one C++-specific. The universal ones come straight from the Python deck; the C++-specific one matters because C++ makes shared memory tempting in a way Python or JVM don't. mmap, shared memory segments, even a static library that wraps a 'singleton config': all of these become coupling that the deployment topology hides until something breaks. The shipping rule: every C++ service is a process. Two services that 'happen to share a memory region' are one service with extra steps. If they need to share, use a data store or message bus; pay the deserialisation cost and get the operational benefits.

## [093] IN CLOSING · The whole talk, in five lines (sldId 348)

- Cloud-native is a set of properties; the platform exists to make them the default.
- Match each interaction to its style (REST, gRPC, GraphQL or async) and compose at the edge.
- Own your data; share it as contracts and facts, never as shared tables.
- Make the contract a governed artifact: registry to enforce it, metadata to find it, observability to run it.
- Every anti-pattern is coupling sneaking back in. Design to keep things apart.
- C++ in this picture: a clean, fast producer of contracts and signals. Drogon at the edge, gRPC east-west, librdkafka for facts, OpenTelemetry C++ for visibility. RAII makes the discipline cheap to keep.

p. 79

> The five-line summary, with one extra C++-specific line. The point: C++ services are first-class participants in a cloud-native architecture, with their own ecosystem of production-grade libraries (Drogon, gRPC, librdkafka, OpenTelemetry C++, jwt-cpp) that integrate with the same platform every other language plugs into. The language stops being the interesting question; the architecture starts being the interesting question.

## [094] REFERENCES · The shoulders this stands on (sldId 349)

- Cloud-Native Patterns and Architecture
- Building Microservices, 2nd ed. — Sam Newman (O'Reilly)
- Designing Data-Intensive Applications, 2nd ed. — Martin Kleppmann & Chris Riccomini (O'Reilly)
- Building Event-Driven Microservices, 2nd ed. — Adam Bellemare (O'Reilly)
- Cloud Native Patterns — Cornelia Davis (Manning)
- Patterns of Distributed Systems — Unmesh Joshi (Addison-Wesley)
- Architecture Modernization — Nick Tune & Jean-Georges Perrin (Manning)
- Cloud Native Anti-Patterns — Gerald Bachlmayr et al. (Packt)
- API Design
- Principles of Web API Design — James Higginbotham (Addison-Wesley)
- Patterns for API Design — Olaf Zimmermann et al. (Addison-Wesley)
- API Design Patterns — JJ Geewax (Manning)
- Domain modelling
- Learning Domain-Driven Design (O'Reilly) and Balancing Coupling in Software Design (Addison-Wesley) — Vlad Khononov
- The full list, with publisher links: patterncatalyst.github.io/cloud-native-design-patterns/bibliography/

p. 80

> The reference list. These are the books that the architectural patterns in this deck draw from — read them in roughly the order listed if you're building up the model from scratch; cherry-pick if you're filling in a specific gap. Newman and Kleppmann are the table-stakes baseline; Bellemare is the event-driven deep dive; Khononov on coupling is the synthesis that ties API design to domain modelling. For C++-specific references on the implementation side: the C++ Core Guidelines, Sutter & Alexandrescu's C++ Coding Standards, and two Apache-2.0 companion projects: cpp-statelessness (patterncatalyst.github.io/cpp-statelessness/) on stateless C++ services in containers, and the C++ container optimization tutorial (patterncatalyst.github.io/cpp-container-optimization-tutorial/). The full list, with a publisher link for every title, is on the site's Bibliography page (patterncatalyst.github.io/cloud-native-design-patterns/bibliography/).

## [095] THANK YOU · Questions? (sldId 350)

Designing Cloud-Native APIs · C++23 · Drogon · gRPC · Kafka · Kubernetes

> Closing slide. Use the Q&A as a chance to circle back to the running example — show how the canonical five-service system threads through every section in the deck. If audience questions go deep on a specific section (Data, Event-Driven, Security are common pull points), the appendices have the depth: A Protocols, B Versioning, C Pinning, etc.

## [096] REFERENCE · Glossary of acronyms (1 of 2) — protocols, data, events (sldId 351)

- Protocols & APIs — REST (Representational State Transfer); RPC (Remote Procedure Call); gRPC (Google's RPC framework, over HTTP/2 + Protobuf); HTTP (HyperText Transfer Protocol); TLS / mTLS (Transport Layer Security / mutual TLS); SSE (Server-Sent Events); BFF (Backend-For-Frontend); SDK (Software Development Kit); API (Application Programming Interface).
- Messaging & integration — AMQP (Advanced Message Queuing Protocol); ESB (Enterprise Service Bus); DLQ (Dead-Letter Queue, where un-processable messages go); SerDe (Serializer / Deserializer); pub/sub (publish-subscribe).
- Data & persistence — CQRS (Command Query Responsibility Segregation); CDC (Change Data Capture); WAL (Write-Ahead Log: the DB's commit-ordered durable log); ACID (Atomicity, Consistency, Isolation, Durability); TTL (Time-To-Live); LRU (Least Recently Used: cache eviction policy); SETEX (Redis 'SET with EXpiry'); ORM (Object-Relational Mapping); libpq (C library for PostgreSQL: the C++ driver in this deck); nlohmann::json (the canonical header-only C++ JSON library).
- Domain modelling & flow — DDD (Domain-Driven Design); OHS (Open Host Service: a published, stable interface a context offers others); ACL (Anti-Corruption Layer in DDD, which translates between models; ACL also means Access Control List in security); Saga (not an acronym: a sequence of local transactions with compensating actions).

p. 81

> Glossary 1 of 2 — protocols, data, events. Two C++-specific entries swapped in: libpq (replaces Python's asyncpg) and nlohmann::json (replaces Pydantic for the JSON-handling concern; serialisation and validation are separate concerns in C++ — nlohmann::json does the deserialisation, validation rides on top via something like JSON Schema or hand-rolled checks).

## [097] REFERENCE · Glossary of acronyms (2 of 2) — platform, security, telemetry (sldId 352)

- Kubernetes & cloud — K8s (Kubernetes); RBAC (Role-Based Access Control); HPA (Horizontal Pod Autoscaler); KEDA (Kubernetes Event-Driven Autoscaling); PSS (Pod Security Standards); CRD (Custom Resource Definition); IAM (Identity & Access Management); KMS (Key Management Service); VPC (Virtual Private Cloud); CNI (Container Network Interface).
- Identity & security — SPIFFE (Secure Production Identity Framework For Everyone); SPIRE (the SPIFFE Runtime Environment); OPA (Open Policy Agent); IAP (Identity-Aware Proxy); JWT (JSON Web Token); OIDC (OpenID Connect); OAuth (Open Authorization); MFA (Multi-Factor Authentication); PII (Personally Identifiable Information); SLSA (Supply-chain Levels for Software Artifacts); CVE (Common Vulnerabilities & Exposures); SBOM (Software Bill of Materials).
- Observability — OTel (OpenTelemetry); RED (Rate, Errors, Duration: the request-driven metrics method); USE (Utilisation, Saturation, Errors: the resource metrics method); MDC (Mapped Diagnostic Context: per-thread log context); LGTM (Loki, Grafana, Tempo, Mimir); SLO / SLI / SLA (Service-Level Objective / Indicator / Agreement); p99 (99th-percentile latency); spdlog (the canonical C++ structured logging library, used throughout this deck); DWARF (the C++ binary debug format that makes eBPF profilers actionable).
- C++ build & runtime — Conan (the C++ package manager used in this deck); CMake (the build system generator); RAII (Resource Acquisition Is Initialization: the central C++ ownership idiom); PMR (Polymorphic Memory Resource: the standard arena allocators, since C++17); DI (Dependency Injection); DTO (Data Transfer Object); ABI (Application Binary Interface); LTO (Link-Time Optimization).

p. 82

> Glossary 2 of 2 — platform, security, observability, plus a C++ build & runtime row replacing the Python deck's WSGI/ASGI/GIL/venv row.

## [098] Protocols in Depth (sldId 353)

Appendix A

REST, gRPC and GraphQL: how they differ.

> Section Appendix A divider: Protocols
>
> in Depth. REST, gRPC and GraphQL: how they differ.

## [099] APPENDIX A · PROTOCOLS · Three paradigms and their mental models (sldId 354)

REST models resources, gRPC models procedures, GraphQL models a typed graph — the same intent, three shapes.

p. 83

> Each protocol has its own mental model. REST's primitive is the resource: nouns and verbs. gRPC's primitive is the call: services and methods. GraphQL's primitive is the typed graph: nodes and edges. The same business intent can be modelled in any of them; the shape changes more than the function. For C++ this means three different library shapes too: Drogon's HttpController for REST, grpc::Service for gRPC, cppgraphqlgen's object:: types for GraphQL. Ports and adapters (Appendix F, Example 19) let you write the business logic once and adapt it to all three boundaries, though in practice most C++ services pick one or two protocols and commit.

## [100] APPENDIX A · PROTOCOLS · Over-fetching, under-fetching and round trips (sldId 355)

REST trades round trips or bespoke endpoints for simplicity; GraphQL shapes one response; gRPC is a typed call.

p. 84

> The fetching trilemma: over-fetch (REST returns the whole resource when you needed two fields), under-fetch (REST returns too little, you make N more round trips), or bespoke endpoint (REST grows /orders/{id}/with-customer-and-totals, which doesn't scale). GraphQL solves over- and under-fetch by shaping the response client-side. gRPC sidesteps it by being a typed call with a typed response — the caller knows what they're getting. C++ implications: for chatty internal paths, gRPC's typed responses and HTTP/2 multiplexing dramatically outperform multiple REST calls. For client-facing aggregation across services, the GraphQL gateway (cppgraphqlgen or Apollo) handles the shaping.

## [101] APPENDIX A · PROTOCOLS · The wire: transport, encoding and streaming (sldId 356)

Reach and caching, or raw speed, or client-shaped responses — choose on the wire properties you need.

p. 85

> The wire-level differences. REST: HTTP/1.1 by default (HTTP/2 sometimes), text JSON, cacheable via standard headers, ubiquitous browser support. gRPC: HTTP/2 always, binary protobuf, bidirectional streaming, no browser support without grpc-web. GraphQL: HTTP/1.1 POST by default (with WebSocket subscriptions for live data), text JSON over the wire, single endpoint. C++ wire considerations: protobuf's binary encoding is meaningfully smaller and faster to parse than JSON — for high-volume internal paths the CPU saving compounds. JSON parse cost in C++ with nlohmann::json is competitive with Java/.NET but slower than protobuf by 5-10x for the same payload.

## [102] APPENDIX A · PROTOCOLS · Choosing between them in practice (sldId 357)

- Public or partner-facing, browser or third-party clients, caching matters → REST. C++ at the edge: Drogon.
- Internal service-to-service, low latency, high call volume, streaming → gRPC. C++ east-west: grpc::Service with the sync API.
- Aggregating many back-ends for varied clients that each want different fields → GraphQL at the gateway. C++ option: cppgraphqlgen on Drogon, or front C++ REST/gRPC services with an Apollo (Node) gateway.
- A fact that many consumers react to, decoupled in time → none of these; emit an event. C++ producers: librdkafka (rdkafka++).
- Real systems use all four; standardizing on one wire for everything is itself an anti-pattern.

p. 86

> Picking a protocol is a per-edge decision, not a per-service one. A single C++ service often speaks REST at the public edge (Drogon), gRPC internally (grpc::Service), and publishes events on Kafka (rdkafka++) — all from the same binary. The ports-and-adapters structure of Appendix F keeps the business logic clean of any protocol concerns; each adapter lives at its boundary and translates.

## [103] APPENDIX A · PROTOCOLS · Common mistakes with each (sldId 358)

- REST: verbs in URLs (/createOrder), 200-for-everything, offset pagination instead of cursors, ignoring cache headers.
- gRPC: exposing it directly to browsers without grpc-web; treating it as REST-with-protobuf and ignoring streaming.
- GraphQL: the N+1 resolver explosion; no query depth/complexity limits; using it for simple single-resource reads.
- All three: leaking internal database models straight onto the wire, so you can never evolve them.
- Async: using a queue when you needed a log (no replay), or a request when you needed a fact.
- C++-specific traps: parsing JSON repeatedly in a hot path instead of caching the parsed result; copying protobuf messages across boundaries instead of passing const-ref; using grpc::Status as a return value when an exception fits better. Decide which boundary errors cross.

p. 87

> Five universal anti-patterns and one C++-specific row. The C++ traps are all about ownership and copies — the things C++ makes explicit that other languages hide. JSON parsing is expensive (nlohmann::json builds a tree); protobuf messages contain owned strings and submessages that copy by value unless you std::move them; grpc::Status as a return-vs-throw decision is one you should make consciously and apply consistently.

## [104] Versioning & Evolution (sldId 359)

Appendix B

REST, proto breaking changes, GraphQL evolution.

> Section Appendix B divider: Versioning
>
> & Evolution. REST, proto breaking changes, GraphQL evolution.

## [105] APPENDIX B · VERSIONING · Four ways to version a REST API (sldId 360)

URI versioning is common and visible; media-type versioning keeps URLs stable — the more RESTful choice.

p. 88

> Four mechanisms for REST versioning, in roughly decreasing order of how RESTful they are: media-type (Accept header), custom header (X-API-Version), query string (?v=2), and URI (/v2/orders). URI is the most visible and easiest to debug; media-type is the most RESTful because the URL remains the resource and the representation is negotiated. For C++ services the implementation differs by mechanism: URI versioning means two Drogon HttpControllers registered at different paths; media-type versioning is one controller branching on the Accept header. Both are mechanical; pick whichever your consumers find more workable.

## [106] APPENDIX B · VERSIONING · Media-type versioning with Drogon (sldId 361)

[chip] c++ · Drogon

```c++
// Media-type versioning in Drogon — one stable URL, two representations
constexpr auto V1 = "application/vnd.acme.order+json";        // legacy
constexpr auto V2 = "application/vnd.acme.order.v2+json";     // adds currency

Task<> Orders::get(HttpRequestPtr req, auto cb, std::string oid) {
  Order order = co_await orders_.get(oid);
  auto accept = req->getHeader("Accept").value_or(V1);
  if (accept == V2) {                              // negotiate the rep
    json body = order.to_json();
    body["currency"] = order.currency;
    auto r = HttpResponse::newHttpJsonResponse(body);
    r->setContentTypeString(V2);
    cb(r); co_return;
  }
  auto r = HttpResponse::newHttpJsonResponse(order.to_json()); // v1
  r->setContentTypeString(V1);
  cb(r);
}
// The URL never changes; clients opt into a representation via Accept.
// New clients ask for V2; old clients keep getting V1.
```

The resource URL is stable; the representation is negotiated. Add fields by minting a new media type; old clients see the old shape.

p. 89

> Media-type versioning in idiomatic Drogon. Key things to note: (1) the URL /orders/{oid} never changes — it's the resource, not a version. (2) The Accept header is the version selector; clients opt in. (3) The handler builds the appropriate JSON shape and pins the Content-Type to match what was requested. Compared to URI versioning, this is harder to test from a browser (you can't just type /v2/orders in the URL bar) but cleaner long-term — there's no /v3 endpoint waiting to explode. For partner APIs where the consumers are programs, this is the better choice; for human-explored APIs, URI versioning is often more pragmatic.

## [107] APPENDIX B · VERSIONING · gRPC / protobuf: what is a breaking change (sldId 362)

Field numbers are the contract — names and order are not. Never reuse or renumber a field.

p. 90

> protobuf's contract is the field numbers, not the field names. This means renaming a field is safe on the wire (old serialised bytes still parse), but renumbering or reusing a number is catastrophic — an old client that sees tag 4 with new semantics will misinterpret the data silently. For C++ specifically: protoc-generated C++ classes use the field names for accessor methods (set_sku, sku, has_sku) but the numbers for wire encoding. Renaming breaks your build but not other consumers; renumbering compiles cleanly but breaks everyone. The compiler is the wrong tool for catching this — the registry (Apicurio's BACKWARD compatibility rule for proto) is the right one.

## [108] APPENDIX B · VERSIONING · Evolving a .proto safely (sldId 363)

[chip] protobuf

```protobuf
// Evolving a .proto safely — add with new tags, reserve what you remove
syntax = "proto3";
message Order {
  string id     = 1;
  string sku    = 2;
  int32  qty    = 3;
  reserved 4;                 // tag 4 once held 'notes' — never reuse it
  reserved "notes";
  string currency    = 5;     // safe: brand-new field, new tag number
  PaymentState state = 6;     // safe: new field; old clients ignore it
}
enum PaymentState {
  PENDING  = 0;                // proto3: 0 must exist as the default
  PAID     = 1;
  REFUNDED = 2;
}

// breaking (don't):
//   qty's type from int32 -> int64 (silent corruption on overflow)
//   moving 'sku' to tag 7 (old clients read garbage from tag 2)
//   reusing tag 4 for a different field (old data deserialises wrong)
```

Add with new tags, reserve what you remove, and never change an existing field's number or type. Apicurio BACKWARD enforces this in CI.

p. 91

> The four rules of safe proto evolution, in one example: (1) add new fields at new tag numbers (currency=5, state=6). (2) Use `reserved` for any tag number and name that's been retired — protoc enforces that you can never accidentally re-use them. (3) Never change a field's type — int32 → int64 looks innocent but old wire data interprets differently. (4) Enum 0 must exist as the default; proto3 doesn't distinguish 'unset' from 'zero', so the zero value is your sentinel. These rules look universal but the failure modes differ in C++: protoc-generated C++ classes will compile fine after a renumber, and you'll only see the corruption when an old peer sends data on the wire — the test suite needs to include cross-version data samples, not just round-trips through fresh code.

## [109] APPENDIX B · VERSIONING · GraphQL versions by evolution, not by number (sldId 364)

There is no /v2 in GraphQL: add fields, mark old ones @deprecated, watch usage, then retire.

p. 92

> GraphQL has no version numbers because it doesn't need them. The query selects fields; adding new fields can't break existing queries (they don't ask for them). The migration lifecycle is: add the new field additively, mark the old field @deprecated with a reason, measure usage through field-level metrics, and retire when usage drops to zero. For C++ via cppgraphqlgen: the schemagen tool produces deprecated wrappers automatically from @deprecated annotations in the .graphql file; introspection surfaces the deprecation to client tooling (GraphQL Playground, Apollo Studio); usage metrics need to be wired into the resolver (one OTel span attribute per resolved field is enough).

## [110] APPENDIX B · VERSIONING · Deprecating a field in cppgraphqlgen (sldId 365)

[chip] graphql + c++

```graphql+c++
# schema.graphql — deprecate additively, never break
type Order {
  id: ID!
  total: Float
    @deprecated(reason: "Use totalMinor (integer cents) instead.")
  totalMinor: Int!              # the replacement field, added additively
}

// schemagen produces deprecated wrappers from @deprecated in the SDL.
// cppgraphqlgen surfaces the deprecation in introspection automatically.
// Wire one OTel span attribute per resolved field to track usage:
class OrderResolver : public object::Order {
 public:
  service::AwaitableScalar<float> getTotal() const {
    auto span = tracer_->StartSpan("resolve.Order.total");
    span->SetAttribute("graphql.deprecated", true);  // usage signal
    co_return order_.total;
  }
  service::AwaitableScalar<int> getTotalMinor() const {
    co_return order_.total_minor;
  }
};
// When the 'deprecated=true' span attribute drops to zero,
// the field is safe to remove. No /v2 endpoint ever exists.
```

Additive change plus @deprecated plus usage metrics replaces versioning entirely. Retirement is data-driven, not date-driven.

p. 93

> Field-level deprecation in cppgraphqlgen. The SDL is the contract; the @deprecated annotation surfaces in introspection and client tooling. The OTel span attribute trick at the bottom is how you make the retirement decision data-driven: every time a deprecated field is resolved, you tag the span. Aggregating in your metrics backend gives you 'how many requests still pull Order.total per day' — when that number drops to zero (or close enough that the remaining callers can be migrated manually), the field is safe to remove. Compare to REST where there's no analogous field-level usage signal — you'd have to log every request, then parse to see which fields the response included. GraphQL makes this ergonomic, which is one of its real wins for evolution.

## [111] APPENDIX B · VERSIONING · Principles that cut across all three (sldId 366)

- Additive change is always safe; removal and mutation are where you break people.
- Make compatibility mechanical — the registry's BACKWARD / FORWARD / FULL rules, checked in CI (publish_schema from §9), not by reviewers' memory.
- Never break silently: deprecate with a reason, a replacement and a sunset date; measure who's still on the old version.
- Run old and new in parallel and migrate consumers before retiring — retirement is the only step that can break.
- Version data the same way you version APIs: event schemas in Apicurio follow the identical rules.
- C++ specifics: protoc-generated stubs CRT-link cleanly across compatible proto changes (good); but C++ ABI is fragile, so when you re-link a service, all dependencies must rebuild against the new proto. Pin generated stubs via Conan, regenerate via CMake, never copy generated .pb.cc into Git.

p. 94

> Five universal versioning principles plus a C++-specific row about the C++ ABI / Conan / CMake interplay. The point of the C++ row: generated proto stubs are build output, not source — they should not live in Git; they should be regenerated from the .proto in CI. When you upgrade protobuf itself to a new major version, every consumer rebuilds against the new stubs at the same time. A committed Conan lockfile (conan.lock, as every C++ example here has) is the mechanism that keeps this manageable; cpp-statelessness Doc 11 shows the profiles around it (patterncatalyst.github.io/cpp-statelessness/docs/11-build-tooling/).

## [112] WebSockets at Scale (sldId 367)

Appendix C

Drogon, pod pinning, the backplane, binary framing, reconnection.

> Section Appendix C divider: WebSockets
>
> at Scale. Drogon, pod pinning, the backplane, binary framing, reconnection.

## [113] APPENDIX C · WEBSOCKETS · A WebSocket endpoint in Drogon (sldId 368)

[chip] c++ · Drogon

```c++
// Drogon WebSocket endpoint — per-pod state, scaling problem starts here.
class ChatWs : public drogon::WebSocketController<ChatWs> {
 public:
  WS_PATH_LIST_BEGIN
    WS_PATH_ADD("/ws/{user_id}");
  WS_PATH_LIST_END
  void handleNewConnection(const HttpRequestPtr& req,
                           const WebSocketConnectionPtr& conn) override {
    auto uid = req->getPathParameter("user_id");
    std::lock_guard lk{mu_};
    clients_[uid] = conn;                  // this pod now owns the user
  }
  void handleNewMessage(const WebSocketConnectionPtr& conn,
                        std::string&& msg,
                        const WebSocketMessageType& t) override {
    handle(msg);                            // full-duplex, long-lived
  }
  void handleConnectionClosed(const WebSocketConnectionPtr& conn) override {
    std::lock_guard lk{mu_};
    erase_if(clients_, [&](auto& kv){ return kv.second == conn; });
  }
 private:
  std::mutex mu_;
  std::unordered_map<std::string, WebSocketConnectionPtr> clients_;  // per-pod
};
```

Short to write, but clients_ is per-pod. That single member is the entire scaling problem.

p. 95

> Drogon's WebSocketController is the natural C++ entry point. The code is mechanical (registration, message handler, disconnect cleanup), but the clients_ map is the foundation of the scaling problem. Per-pod state, by definition not shared. Boost.Beast is the alternative if you need lower-level control or want to host WebSocket logic outside Drogon's HttpAppFramework — Beast gives you the raw protocol; you build the connection registry yourself. The Drogon path is simpler for most cases. Either way, the scaling problem and its solutions are the same.

## [114] APPENDIX C · WEBSOCKETS · Why WebSockets fight Kubernetes scaling (sldId 369)

A long-lived connection pins to one pod; new pods get no existing connections and scale-down drops them.

p. 96

> Kubernetes is built on the assumption that pods are interchangeable and requests are short. WebSockets violate both. A connection lives for hours; the LB can't migrate it without dropping it. New replicas only receive new connections — existing hotspots stay hot. Scale-down severs whatever connections were on the evicted pods. For C++ this is the same problem as for any language: C++ can handle tens of thousands of concurrent sockets per pod (vs Python's few thousand), which delays the problem but does not solve it. The backplane, graceful drain and resume are the fixes.

## [115] APPENDIX C · WEBSOCKETS · The scaling problem, stated precisely (sldId 370)

- Pinning: a connection is bound to one pod; the LB can't move it without dropping it.
- Uneven load: new replicas only receive new connections, so existing hotspots persist.
- Rollouts hurt: every deploy or scale-down severs the connections on the affected pods.
- Cross-pod delivery: to push to user X you must reach whichever pod holds X — which you don't track.
- Connection limits & memory: each socket is held-open state; pods cap out on file descriptors, not CPU.
- C++ angle: each connection in Drogon is cheap (~10-20 KB resident plus the kernel socket); a single C++ pod can hold 30-50k connections — but it still pins, still drops on scale-down. Capacity doesn't solve coupling.

p. 97

> Five precise failure modes, plus a C++-specific note about per-connection cost. The headline: C++'s low per-connection memory footprint changes the scale of the problem (you need fewer pods) but not its nature (you still need a backplane for cross-pod delivery, graceful drain on rollout, and resume on reconnect). Operational reality: a C++ pod at 50k connections is approaching FD limits (ulimit -n = 65536 by default); raise the limit explicitly, monitor it, and don't pack pods past where graceful drain becomes painful.

## [116] APPENDIX C · WEBSOCKETS · Scaling out: a pub/sub backplane (sldId 371)

Each pod owns only its own sockets; a Redis or Kafka backplane fans a message out to whichever pod holds the client.

p. 98

> The pub/sub backplane is the architectural fix. Each pod owns only its own sockets and subscribes to a Redis or Kafka channel; when any pod wants to push to user X, it publishes to the channel; every pod sees the message and forwards it to user X if they happen to hold that socket. C++ implementation: sw/redis++ for the Redis backplane (lightweight, fast publish/subscribe), librdkafka (rdkafka++) if you're already running Kafka and want the durability. Redis is simpler and faster for ephemeral fan-out; Kafka is the right choice if missed messages would matter (offline users coming back online and wanting their queue). Either way: the backplane is process-scoped — one subscriber per pod, not per connection.

## [117] APPENDIX C · WEBSOCKETS · Binary framing with protobuf — fast and versioned (sldId 372)

[chip] protobuf + c++

```protobuf+c++
// envelope.proto — version the message, not the URL
message Envelope {
  uint32 version = 1;        // bump for incompatible payload changes
  string type    = 2;        // "order.updated", "ping", ...
  bytes  payload = 3;        // protobuf-encoded body for `type`
  uint64 seq     = 4;        // monotonic per-connection — drives resume
}

// Server: send compact binary frames instead of JSON text
void send_order_update(WebSocketConnectionPtr conn,
                       const Order& order, uint64_t seq) {
  Envelope env;
  env.set_version(2);
  env.set_type("order.updated");
  env.set_payload(order.SerializeAsString());
  env.set_seq(seq);
  conn->send(env.SerializeAsString(),
             WebSocketMessageType::Binary);    // binary, not text
}
// Client checks env.version on each frame; unknown major →
// reconnect and renegotiate. seq drives resume after a drop.
```

Protobuf frames are smaller and faster than JSON; the versioned envelope and seq number enable evolution and resume.

p. 99

> Binary framing is a meaningful win for high-frequency WebSocket traffic. JSON text frames cost CPU on both ends (parse, stringify) and 2-3x the bytes of the equivalent protobuf. The envelope pattern adds version and seq fields so the client can detect incompatible server upgrades and the server can drive resume after a reconnect. C++ specifics: protobuf in C++ is fast — both serialise and parse run at memory-copy speed for typical message sizes. The cost is in the heap allocations for owned strings; for hot paths a protobuf arena (google::protobuf::Arena::Create<Envelope>(&arena); CreateMessage is no longer public in protobuf 6.33) amortises that cost. Keep the two allocators apart: protobuf messages on their arena or the default allocator, handler internals on the PMR request arena, with the boundary explicit in code review (cpp-statelessness Doc 03, patterncatalyst.github.io/cpp-statelessness/docs/03-pmr/).

## [118] APPENDIX C · WEBSOCKETS · Failure handling: resume, don't restart (sldId 373)

Heartbeats detect dead links; the client reconnects with backoff and resumes from the last acknowledged sequence.

p. 100

> WebSocket connections die — TCP RST, NAT timeout, pod restart, network glitch. The client side must reconnect; the question is what state survives across the gap. Heartbeats (ping/pong) detect dead links well before TCP-level timeouts. The seq number from the envelope is what enables resume — the client sends 'last seq I saw' on reconnect; the server replays from there. C++ server-side: keep a per-connection ring buffer of the last N frames (sized to your expected disconnect duration × message rate), discard frames older than the buffer holds. Give each connection its own PMR arena (the per-request arena of cpp-statelessness Doc 03, applied to a connection's lifetime) so its allocations are released on disconnect. Backoff with jitter is the client's job: exponential backoff capped at 30s, plus 0-1s random jitter to avoid thundering herd on server recovery.

## [119] APPENDIX C · WEBSOCKETS · A cloud-native WebSocket checklist (sldId 374)

- Externalize fan-out to a backplane (Redis via sw/redis++ or Kafka via rdkafka++); never assume one pod holds the client.
- Scale and trigger on connection count and memory, not CPU; set realistic per-pod connection caps (50k is reachable for a C++ pod; tune to your messages/sec).
- Drain gracefully on shutdown: stop accepting (std::stop_token blocks new), signal clients to reconnect, let exponential backoff + jitter spread the herd.
- Heartbeat to detect dead links; reconnect with exponential backoff + jitter; resume via a per-connection seq number.
- Use binary frames with a versioned envelope; authenticate on connect (sidecar JWT or per-connection token) and re-check on resume.
- Per-connection state in a PMR arena (the cpp-statelessness Doc 03 pattern): arena destructs on disconnect, no leaks across long-lived connections.

p. 101

> Six rules for WebSockets that scale on Kubernetes. The first five carry across any language; the sixth (PMR per-connection arenas) is the C++-specific win.

## [120] Saga State & Compensation (sldId 375)

Appendix D

boost::sml, persistence, compensation, the step-B-needs-A's-data problem.

> Section Appendix D divider: Saga State
>
> & Compensation. boost::sml, persistence, compensation, the step-B-needs-A's-data problem.

## [121] APPENDIX D · SAGAS · Where a C++ saga keeps its state (sldId 376)

Memory won't survive a pod restart — persist every step transition in a DB, an event log, or a workflow engine.

p. 102

> Three options for saga state durability. (1) Database row — one row per saga, row-locked for the duration of advance(); cheapest for short sagas. (2) Event log (Kafka) — append every step transition as an event; the current state is the fold of the log; replay is trivial. (3) Workflow engine — Temporal / Cadence owns the state; your code is just activity implementations. For C++ specifically: option (1) is the default in this deck because it pairs cleanly with the libpq + PgTxn RAII patterns. Option (3) means C++ services are Temporal activities behind a workflow worker written in Go/Java/TS (since C++ has no first-class Temporal SDK). Option (2) requires an event-sourcing commitment across the whole system; reach for it when audit and time-travel queries matter.

## [122] APPENDIX D · SAGAS · A persisted saga state machine with boost::sml (sldId 377)

[chip] c++ · boost::sml

```c++
// saga_machine.hpp (excerpt): the saga lifecycle as a boost::sml state machine
struct StepSucceeded {}; struct StepFailed {}; struct AllStepsDone {}; struct Compensated {};
struct Progress { int step_index = 0; int total_steps = 0; };

struct Lifecycle {
  auto operator()() const {
    using namespace sml;
    auto all_done = [](Progress& p) { return p.step_index >= p.total_steps; };
    auto advance  = [](Progress& p) { ++p.step_index; };
    return make_transition_table(
      *state<Running> + event<StepSucceeded> / advance = state<Running>,
       state<Running> + event<AllStepsDone>[all_done]  = state<Completed>,
       state<Running> + event<StepFailed>              = state<Compensating>,
       state<Compensating> + event<Compensated>        = state<Compensated_>);
  }
};
// main.cpp advance(): one step per transaction, under a row lock (libpq)
//   BEGIN; SELECT status, step_index, context FROM sagas WHERE id = $1 FOR UPDATE;
//   restore(sm, status); run g_steps[step_index]; context[step.name] = result;
//   sm.process_event(StepSucceeded{}); UPDATE sagas ...; COMMIT
```

A typed lifecycle in four transitions; status, step_index and context persisted to Postgres on every step. Crash = reload the row and call advance() again.

p. 103

> boost::sml (header-only, Boost Software License) is the natural C++ choice for typed state machines. The example models the saga lifecycle, not the individual steps: RUNNING advances step by step, AllStepsDone moves to COMPLETED when the guard holds, StepFailed moves to COMPENSATING, and Compensated ends in COMPENSATED. The machine owns no I/O: the orchestrator runs a step, reports the outcome as an event, and the machine decides the next status.
>
> Postgres holds status, step_index and context. Each advance() is one transaction under SELECT ... FOR UPDATE, so one saga moves one step at a time and no two workers advance the same saga. restore() rebuilds the machine from the persisted status, which is how a restarted orchestrator resumes a RUNNING saga.

## [123] APPENDIX D · SAGAS · Compensating transactions unwind a failed saga (sldId 378)

Each committed step has an inverse; on failure they run in reverse order — there is no cross-service rollback.

p. 104

> Sagas don't roll back — they compensate. Each forward step has a defined inverse (charge_payment → refund_payment, reserve_stock → release_stock, book_shipping → cancel_shipping). When a saga fails midway, compensations run only for the steps that completed, in reverse order. Important property: compensations are semantic, not transactional. A refund is a new transaction in payment-service; it doesn't undo the original charge, it issues a new movement that nets to zero. This is why every compensation needs to be idempotent with an idempotency key — retries are expected and must not double-refund.

## [124] APPENDIX D · SAGAS · Running compensations in reverse (sldId 379)

[chip] c++ · boost::sml

```c++
// main.cpp (excerpt): COMPENSATING undoes the completed steps, newest first
if (status == "COMPENSATING") {
  for (int i : cndp::saga::compensation_order(progress.step_index)) {  // n-1 .. 0
    auto& step = g_steps[i];             // charge_payment -> refund_payment, ...
    if (!logStep(db.conn, sagaId, step.compensationName, "compensate",
                 step.compensate(context))) { abandon(); return; }
  }
  sm.process_event(cndp::saga::Compensated{});
  setState(db.conn, sagaId, cndp::saga::status_of(sm), progress.step_index, nullptr);
  exec(db.conn, "COMMIT");                  // one transaction for the unwind
}

// A forward step that throws is logged, then StepFailed moves the saga
// from RUNNING to COMPENSATING; the next advance() runs the block.
catch (const std::exception& e) {
  logStep(db.conn, sagaId, step.name, "failed", failResult);
  sm.process_event(cndp::saga::StepFailed{});
  setState(db.conn, sagaId, cndp::saga::status_of(sm), progress.step_index, nullptr);
}
```

Compensate only completed steps, in reverse, with an idempotency key per (saga, step) so a retry never double-refunds.

p. 105

> Compensation in the example is a separate phase of the same lifecycle. When a step throws, the orchestrator logs the failure and sends StepFailed, which moves the saga to COMPENSATING. The next advance() undoes the completed steps in reverse order (compensation_order returns step_index-1 down to 0), logs each compensation (refund_payment, release_stock, cancel_shipping), then sends Compensated and commits.
>
> The state machine guarantees that only steps that committed are compensated. In a production system each compensation call also carries an idempotency key such as the saga id plus the step name, because a restart between the compensation and the commit repeats it.

## [125] APPENDIX D · SAGAS · When step B needs data only step A produced (sldId 380)

Don't make B call A. Persist A's output into the saga context and pass it forward; on resume, read it back.

p. 106

> The classic saga data-dependency trap: B needs the reservation_id that A produced. Naive fix: B calls A to fetch it. This rebuilds the synchronous coupling the saga was meant to break. Correct fix: A's output goes into the saga's context blob (JSON column on the saga row); B reads it from the persisted context. If A re-runs (it shouldn't, but if a bug forces it), it must produce identical output for the same idempotency key — this is what makes the saga deterministic across restarts.

## [126] APPENDIX D · SAGAS · Carrying context forward — and resuming after a crash (sldId 381)

[chip] c++ · boost::sml

```c++
// Every step's output lands in context[step.name], the sagas.context jsonb column
// (saga-orchestrator/src/main.cpp, jsoncpp Json::Value).
//   after reserve_stock: context["reserve_stock"] = {"reservation_id": ..., "sku": ...}

// A later step reads A's output from the persisted context, never from A:
[](const Json::Value& ctx) {                    // book_shipping execute()
  const auto& reserved = ctx["reserve_stock"];  // B reads A's data
  Json::Value r;
  r["shipment_id"]    = generateId("shp-");
  r["reservation_id"] = reserved["reservation_id"].asString();
  return r;
}

// advance(), after the step succeeds, in the same transaction as the status:
Json::Value result = step.execute(context);
context[step.name] = result;                    // carried forward
setState(db.conn, sagaId, status_of(sm), progress.step_index, &context);
// Crash between A and B: the next advance() reloads the row; context
// already holds A's output, so B runs with it and A is never called again.
```

B reads A's result from the persisted context, never from A. Resume = reload the row and continue at the next step.

p. 107

> The saga context as a JSON column in Postgres is the simplest persistence model and fits the C++ + libpq + jsoncpp (Drogon's Json::Value) toolchain naturally. Every successful step appends to context[step_name]; every step that needs upstream data reads from context[upstream_step]. Type safety trade-off: the JSON column is untyped at the DB layer, which is fine because the type is enforced in the C++ code that produces and consumes it. The step name (compile-time constant) is the schema key. For larger saga payloads, compress (jsonb_compress) or move detail to a separate object-storage claim and store only the reference in context — the same claim-check pattern from §12.

## [127] API Error Handling (sldId 382)

Appendix E

One discipline, four wire formats.

> Section Appendix E divider: API Error
>
> Handling. One discipline, four wire formats.

## [128] APPENDIX E · ERRORS · One error model, four wire formats (sldId 383)

The same five facts in every error; only the encoding changes per protocol.

p. 108

> Five facts that every error needs to carry, regardless of protocol: (1) a stable machine code (STOCK_UNAVAILABLE), never a string the client has to parse. (2) A safe human message: no SQL, no stack traces, no internal class names. (3) A trace_id, so server-side logs and traces can be looked up. (4) A retryable flag: does the client back off and try again, or fail permanently. (5) Field details: for validation errors, which field failed why. The four protocols encode these differently: RFC 9457 problem+json for REST, google.rpc.Status for gRPC, errors[] with extensions for GraphQL, DLQ + retry topics for Kafka. The facts stay the same; only the encoding changes.

## [129] APPENDIX E · ERRORS · REST: status, then Problem Details (sldId 384)

The status code is the category; the problem+json body carries the machine code and specifics.

p. 109

> RFC 9457 (formerly RFC 7807) Problem Details is the IETF standard for REST error bodies. HTTP status code is the broad category (4xx client, 5xx server); the body carries the specifics in a standardised JSON shape. Why use problem+json instead of your-favourite-format: every API gateway, every client SDK, every observability tool already understands it. Standardising on it across a fleet of C++ services means error handling code is shared, not duplicated per service.

## [130] APPENDIX E · ERRORS · REST errors with Drogon (sldId 385)

[chip] c++ · Drogon

```c++
// One central exception → wire mapping; Drogon middleware catches and shapes.
struct StockError : public std::exception {
  std::string detail;
  explicit StockError(std::string d) : detail(std::move(d)) {}
  const char* what() const noexcept override { return detail.c_str(); }
};

// Drogon error-handling middleware — one place: domain → wire
Task<> error_middleware(HttpRequestPtr req, auto next) {
  try { co_await next(req); }
  catch (const StockError& e) {
    json body = {
      {"type",   "https://errors.acme.io/stock"},
      {"title",  "Insufficient stock"},
      {"status", 409},
      {"detail", e.detail},
      {"code",   "STOCK_UNAVAILABLE"},          // stable
      {"traceId", current_trace_id()},          // correlate
    };
    auto r = HttpResponse::newHttpJsonResponse(body);
    r->setStatusCode(k409Conflict);
    r->setContentTypeString("application/problem+json");  // RFC 9457
    co_yield r;
  }
}
```

Map every domain error to problem+json in one middleware — stable code, safe message, trace id; never a raw stack trace.

p. 110

> One central middleware translates exceptions to problem+json. The exception type (StockError, ValidationError, NotFoundError) carries the domain detail; the middleware adds the wire shape (status code, problem+json content type, stable machine code, trace id from OTel current span). Discipline: handlers throw typed exceptions; they never format error responses themselves. This keeps the wire shape consistent across the entire service and means a registry-level review only has to look at the middleware to validate the contract.

## [131] APPENDIX E · ERRORS · gRPC: status codes + rich details (sldId 386)

A small fixed set of canonical codes, plus structured google.rpc.Status details in the trailers.

p. 111

> gRPC's error model is two layers: (1) one of ~16 canonical codes (OK, CANCELLED, UNAVAILABLE, NOT_FOUND, etc.) — a small enum, well-defined retry semantics, every client library understands them. (2) Optional google.rpc.Status proto with rich details — ErrorInfo (machine code, domain, metadata), RetryInfo (back-off duration), BadRequest (field violations), LocalizedMessage (i18n), and more. Picking the canonical code is the most important decision — UNAVAILABLE means retryable, INVALID_ARGUMENT means don't bother, NOT_FOUND has its own semantics. Get this right and clients behave correctly without reading your docs.

## [132] APPENDIX E · ERRORS · gRPC errors with rich status details (sldId 387)

[chip] c++ · gRPC

```c++
// gRPC rich status: code + ErrorInfo + RetryInfo. C++ via grpc++ + google::rpc.
#include <google/rpc/status.pb.h>
#include <google/rpc/error_details.pb.h>

grpc::Status Inventory::ReserveStock(grpc::ServerContext* ctx,
                                     const ReserveRequest* req,
                                     ReserveReply*         reply) {
  if (inventory_down_) {
    google::rpc::Status status;
    status.set_code(static_cast<int>(grpc::StatusCode::UNAVAILABLE));
    status.set_message("inventory temporarily down");
    google::rpc::ErrorInfo info;                  // machine detail
    info.set_reason("STOCK_DOWN");
    info.set_domain("inventory");
    google::rpc::RetryInfo retry;                 // back-off hint
    retry.mutable_retry_delay()->set_seconds(2);
    status.add_details()->PackFrom(info);
    status.add_details()->PackFrom(retry);
    return ::grpc::Status(
        ::grpc::StatusCode::UNAVAILABLE, status.message(),
        status.SerializeAsString());              // in trailer
  }
  // ... success path ...
  return grpc::Status::OK;
}
```

Pick the canonical code (UNAVAILABLE = retryable) and attach ErrorInfo + RetryInfo so clients back off correctly.

p. 112

> Rich status in C++ gRPC is more verbose than Python but mechanically identical. The google.rpc.Status proto is serialised into the binary trailer; client SDKs unpack it and surface ErrorInfo + RetryInfo to caller code. Helper utility worth writing once: a make_grpc_error(code, machine_code, message, retry_delay) function that does this boilerplate. Drop it in a shared header used by every C++ gRPC service. The discipline that matters: every error path returns a well-shaped Status, not the default grpc::Status::CANCELLED.

## [133] APPENDIX E · ERRORS · Kafka: retry topics and a dead-letter queue (sldId 388)

Commit the offset, route the failed record aside, and keep consuming — a poison record never blocks the partition.

p. 113

> Kafka's failure model is unique: there's no synchronous client to return an error to; you have a stream you must keep consuming. A 'poison' record (malformed, persistent downstream failure) that you keep retrying will block the partition behind it — every subsequent record waits. The standard pattern: bounded in-place retries → delayed-retry topic → DLQ. Always commit the offset for the original record so the head-of-line is free; the retried version lives on a different topic with its own consumer.

## [134] APPENDIX E · ERRORS · Kafka retry + DLQ with librdkafka (sldId 389)

[chip] c++ · rdkafka++

```c++
// Bounded in-place retries, then a delayed-retry topic, then a DLQ.
constexpr int MAX_RETRIES = 3;
while (!stop_token.stop_requested()) {
  std::unique_ptr<RdKafka::Message> msg(consumer->consume(100));
  if (msg->err() != RdKafka::ERR_NO_ERROR) continue;
  try {
    handle(*msg);
    consumer->commitSync(msg.get());                 // success
  } catch (const PoisonError& e) {
    int  attempts = read_header(*msg, "retries", 0);
    auto value    = std::string(payload_of(*msg));
    if (attempts < MAX_RETRIES) {
      auto* h = RdKafka::Headers::create();
      h->add("retries", std::to_string(attempts + 1));
      produce_with_headers(*producer, "orders.retry.30s", value, h);   // delayed retry
    } else {
      auto* h = RdKafka::Headers::create();
      h->add("error", "poison");
      h->add("traceId", current_trace_id());
      produce_with_headers(*producer, "orders.DLQ", value, h);         // DLQ
    }
    consumer->commitSync(msg.get());                 // free head-of-line
  }
}
```

Retry a bounded number of times, then DLQ — and always commit, so one poison record can't stall the partition.

p. 114

> Three-tier failure handling: in-place retry attempts in headers, delayed-retry topic (consumed by a separate worker after a delay), DLQ for inspection. The critical discipline: commit after you've routed the failure (to the retry topic or the DLQ), never before. If you crash between the route and the commit you'll re-deliver to the retry topic, which is fine; if you commit before the route and crash you've lost the record. Delayed-retry topic mechanism: a dedicated consumer reads orders.retry.30s, sleeps until 30s after the record's timestamp, then republishes to the original topic. Cheap to implement, gives you exponential backoff across multiple retry topics (retry.30s, retry.5m, retry.30m).

## [135] APPENDIX E · ERRORS · GraphQL: partial success with errors[] (sldId 390)

One HTTP 200; the failed field is null and explained in errors[] with a machine code in extensions.

p. 115

> GraphQL's error model is fundamentally different from REST or gRPC: the HTTP layer is always 200 OK (unless the request didn't parse). Failures live in the body's errors[] array, paired with null values in the data field for the failed paths. Other fields still return — partial success is the default. This is a feature, not a bug: a client querying { order { id, total, stock } } where inventory is down gets the order and total but null for stock. The client decides whether the partial result is useful.

## [136] APPENDIX E · ERRORS · GraphQL field errors with cppgraphqlgen (sldId 391)

[chip] c++ · cppgraphqlgen

{% raw %}
```c++
// In cppgraphqlgen, throw service::schema_exception to null a single field.
// Other fields in the same query still return data.

class OrderResolver : public object::Order {
 public:
  service::AwaitableScalar<int> getStock() const {     // one resolver
    try {
      co_return co_await inventory_.remaining(order_.sku);
    } catch (const Unavailable& e) {
      throw service::schema_exception{ {
        service::schema_error{
          "inventory unavailable",                  // safe message
          {{ "path", "order.stock" }},               // the field
          {{ "extensions", {
              { "code",      "UNAVAILABLE" },         // machine
              { "retryable", true            },
              { "traceId",   current_trace_id() },
          }}}
        }
      } };
    }
  }
  // getId(), getSku(), getTotal() still return normally — partial response
};
```
{% endraw %}

Throw from the field resolver: cppgraphqlgen nulls just that field and adds it to errors[] with your extensions — the rest of data still returns.

p. 116

> cppgraphqlgen's schema_exception is the mechanism for field-level errors. Each entry in the exception's errors list becomes one entry in the response's errors[] array; the exception's path attribute tells GraphQL which field's data to null. The extensions block is where the five-fact discipline lives: code (machine), retryable (bool), traceId (correlate). Clients have a stable shape to react to.

## [137] APPENDIX E · ERRORS · How a retry storm forms — and how to stop it (sldId 392)

Naive retries multiply load on a struggling service; bounded, spaced, circuit-broken retries break the feedback loop.

p. 117

> The retry storm is the classic distributed-systems amplification failure. A downstream service slows down; clients retry; the retries add to the load; the service slows down more; clients retry more aggressively; the service dies; clients all retry now that the service is back; the service dies again. Three controls break the loop: (1) bounded retries — small max (2-3), exponential backoff with jitter. (2) Circuit breaker — after N failures, fail-fast for a window without trying. (3) Retry budget — system-wide cap on retries-per-second per client/service pair. C++ specifics: the Istio sidecar handles (1) and (3) per the §2 resilience-as-config pattern. Circuit breaking is the mesh's job; your C++ code stays clean of retry logic in the common case. If you need in-process retries (a sidecar isn't deployed), no widely adopted C++ retry library exists: write the loop with capped exponential backoff and jitter, as Example 26 does (retry_with_backoff in edge-service).

## [138] APPENDIX E · ERRORS · Error-handling heuristics across all four (sldId 393)

- One contract, four encodings: a stable code, a safe message, a trace id, a retryable flag, field details — everywhere.
- The category lives in the protocol: HTTP status, gRPC code, GraphQL errors[] entry, Kafka DLQ vs retry topic.
- Make retryability explicit and honour it: Retry-After, RetryInfo, extensions.retryable — don't make clients guess.
- Never leak internals: no stack traces, SQL, or class names on the wire; map them to a code and log the detail server-side (spdlog with trace_id).
- Bound every retry (timeout, small max, backoff + jitter, circuit breaker, retry budget) and make handlers idempotent.
- C++ specific: a typed exception hierarchy (StockError, ValidationError, NotFoundError) with one centralized middleware per protocol is dramatically cleaner than per-handler error code. RAII unwind via PgTxn destructor cleans up partial state without explicit catch blocks.

p. 118

> Five universal heuristics plus one C++-specific row about exception-driven error handling.

## [139] DDD & Hexagonal (sldId 394)

Appendix F

Bounded contexts, ports & adapters, the architectural language of API design.

> Section Appendix F divider: DDD &
>
> Hexagonal. Bounded contexts, ports & adapters, the architectural language of API design.

## [140] APPENDIX F · DDD · Why DDD belongs in an API talk (sldId 395)

- DDD gives you the language to talk about where service boundaries belong — bounded contexts map directly to deployable services.
- Strategic DDD (subdomains, bounded contexts, context maps) is the macro-architecture decision: what services exist, who talks to whom.
- Tactical DDD (aggregates, entities, value objects, domain events) is the in-service code structure: how each service is organized internally.
- Hexagonal architecture (ports & adapters) is the implementation pattern that keeps the domain pure and the I/O at the edge — a clean fit for C++.
- Without this vocabulary, every architecture discussion devolves into 'where do we put X' arguments that have no resolution. With it, you can name what you disagree about.
- C++ note: a composition root in main() wiring adapters into ports (Example 19) is hexagonal architecture. The DDD framing puts the architectural reasoning in front of the C++ idiom.

p. 119

> DDD has been around since 2003 (Eric Evans' blue book). It earned its place in modern API design by giving us the conceptual tools we needed to decompose monoliths into services without creating the distributed-monolith anti-pattern. For C++ specifically, the hexagonal pattern (which is just well-applied DI + interface segregation) maps directly to how you'd write a testable, refactorable C++ service: domain code depends on abstract interfaces (ports); concrete implementations (REST handler, libpq adapter, Kafka adapter) live at the edge and are wired in at startup.

## [141] APPENDIX F · DDD · Strategic DDD: subdomains & bounded contexts (sldId 396)

Core / supporting / generic subdomains, with bounded contexts as the technical boundary inside each.

p. 120

> Strategic DDD has two layers. Subdomains are business: core (your competitive advantage, where most effort goes), supporting (necessary but not differentiating: payments, shipping), generic (commoditised: auth, logging, billing platform). Bounded contexts are technical: a context is one cohesive model with its own ubiquitous language. Two contexts can both have 'Customer' but mean different things; the context boundary is where the translation happens. Practical rule for C++ services: one bounded context = one deployable service = one binary. Multiple contexts in one binary breeds the distributed-monolith inside-the-process. The CMake project structure should reflect this — one top-level directory per context.

## [142] APPENDIX F · DDD · A bounded context is a service-and-API boundary (sldId 397)

- Inside the context, one model. Order means one thing; Customer means one thing. The ubiquitous language is consistent.
- At the context boundary, translation. The same business concept (Customer in CRM vs Customer in Billing) carries different attributes and rules — anti-corruption layers translate.
- Bounded contexts become services in cloud-native architectures. The API is the context boundary, made explicit and contractual.
- The contract published to other contexts is the Published Language; the API documentation is the language specification.
- C++ structure: one CMake project per context; the wire contracts (.proto / OpenAPI YAML) are the Published Language; internal headers stay private to the binary.

p. 121

> This is where DDD stops being theoretical and starts being deployable. A bounded context in a cloud-native system is the unit of independent deployability — one binary, one database, one team, one contract. The C++-specific framing: CMake project boundaries should match context boundaries. Public include directories are the published language; private headers are internal model details that other contexts don't see. Shared libraries that span contexts are a smell — they're either a misidentified context (merge them) or they're a generic subdomain that should be its own service or its own well-versioned library.

## [143] APPENDIX F · DDD · Context mapping: how contexts integrate (sldId 398)

Customer/Supplier, Conformist, Anti-Corruption Layer, Open Host Service, Published Language — the named patterns.

p. 122

> Context maps name the relationships between bounded contexts. The vocabulary lets a team say 'we're the Conformist to Billing's model' or 'we need an ACL because their model leaks legacy concerns we don't want'. The most useful patterns in practice: Customer/Supplier (who serves whom; the supplier owns the contract), Anti-Corruption Layer (the protective translation buffer when you must integrate with a model you don't control), Open Host Service + Published Language (a stable, well-documented protocol any consumer can adopt). Most of our §1-§13 architectural patterns implement these context-mapping patterns: the OHS is the registered API; the ACL is the gateway translation layer; the Customer/Supplier relationship is enforced by the SLA on the supplier's contract.

## [144] APPENDIX F · DDD · Open-Host Service & Published Language (sldId 399)

- Open-Host Service (OHS) — a context publishes a stable, well-documented protocol that any other context can integrate with, without bespoke per-consumer agreements.
- Published Language — the explicit, versioned vocabulary of that protocol. In cloud-native terms: the OpenAPI YAML, the .proto file, the AsyncAPI document, the GraphQL SDL.
- Critical property: the published language is the published language for all consumers. There is no per-consumer dialect; if a consumer needs a different shape, an Anti-Corruption Layer translates on their side, not yours.
- Versioning lives in the Published Language (App B's discipline). Deprecation is announced through the language; removal happens only when usage drops to zero.
- Apicurio (§9) is the registry where Published Languages live; OpenMetadata (§10) is the catalog where consumers discover them.
- C++ specific: the public headers exposed by your service are not the Published Language. The wire contracts (YAML, .proto, SDL) are. C++ ABI stability is a private internal concern; wire-level compatibility is what consumers depend on.

p. 123

> OHS and Published Language are the DDD names for what App A-E spent slides on: contracts as governed artifacts. The framing is helpful because it forces the question 'who is this API published to?' — your own internal team, your partner teams, third-party developers? The audience changes the discipline. The C++-specific bullet: C++ ABI is a header-and-link concern that only matters between binaries that link together. The wire contract is what matters between services. Don't conflate them — a Drogon service that exposes its OpenAPI publicly can freely refactor its internal C++ headers without affecting consumers.

## [145] APPENDIX F · HEXAGONAL · Hexagonal architecture: ports & adapters (sldId 400)

Domain in the centre. Ports are interfaces the domain declares. Adapters at the edge implement them.

p. 124

> Hexagonal (Alistair Cockburn, 2005) — the same idea as ports & adapters, sometimes also called 'clean architecture'. The shape of the diagram is incidental; the property is what matters: domain code depends only on interfaces it declares (ports), never on concrete I/O implementations. The concrete implementations (adapters) sit at the edge and are wired in at startup. Why this matters for C++ specifically: testing without mocking frameworks (just provide a test adapter implementing the port); swapping technology choices without touching domain code (libpq for Postgres → libmariadb for MySQL is an adapter swap, not a rewrite); compile-time dependency reversal via abstract base classes or concepts.

## [146] APPENDIX F · HEXAGONAL · Ports & adapters in C++ (sldId 401)

[chip] c++ · hexagonal

```c++
// domain/ports.hpp — the domain declares the interfaces it needs (no framework)
struct OrderRepository {                                   // outbound port
  virtual ~OrderRepository() = default;
  virtual void save(const Order& order) = 0;
  virtual std::optional<Order> find_by_id(const std::string& id) = 0;
};
struct EventPublisher {                                    // outbound port
  virtual ~EventPublisher() = default;
  virtual void publish(const OrderPlaced& event) = 0;
};
// domain/service.hpp — the use case: pure logic, depends only on ports
class PlaceOrderUseCase {
 public:
  PlaceOrderUseCase(OrderRepository& repo, EventPublisher& publisher)
      : repo_(repo), publisher_(publisher) {}
  Order execute(const PlaceOrderCmd& cmd) {
    if (cmd.quantity <= 0) throw std::invalid_argument("quantity must be positive");
    Order order{generate_uuid(), cmd.sku, cmd.quantity, "placed"};  // aggregate
    repo_.save(order);
    publisher_.publish(OrderPlaced{order.id, order.sku, order.quantity});
    return order;
  }
 private: OrderRepository& repo_; EventPublisher& publisher_;
};  // adapters/: rest_adapter.cpp (Drogon), pg_repository.hpp (libpq), log_publisher
```

The domain depends only on ports it declares; REST, CLI, Postgres and log adapters are wired in at startup. Swap or add one without touching PlaceOrderUseCase.

p. 125

> Hexagonal in idiomatic C++. Two design choices to call out: (1) ports are abstract base classes with virtual functions, not concepts. Concepts are great for compile-time polymorphism in templates, but ports need runtime polymorphism (the composition root selects which adapter at startup). (2) Dependency injection by reference, not shared_ptr — the composition root in main() owns the lifetime; PlaceOrderUseCase just uses the dependencies it was given. cpp-statelessness Doc 04 describes the same composition-root idiom (patterncatalyst.github.io/cpp-statelessness/docs/04-process-scoped-state/). Testing: write a TestOrderRepository that records save() calls in a std::vector. PlaceOrderUseCase doesn't know it's not the real one. No mocking framework needed.

## [147] APPENDIX F · DDD · Aggregates and domain events (sldId 402)

- An aggregate is a consistency boundary inside a context: a small cluster of entities + value objects that change together, accessed via a root.
- Order with OrderLines is an aggregate; the Order is the aggregate root; you never reach into OrderLines except through the root. This is what makes the boundary defensible.
- Transactions stay within one aggregate; cross-aggregate consistency happens through domain events (asynchronously, eventually).
- Domain events name what happened at the business level: OrderPlaced, PaymentRefunded, StockReserved — not 'row inserted'. Same name in the C++ struct, the wire protobuf, and the conversation in the team meeting.
- C++: aggregate roots are value-semantic structs with private invariant-enforcing constructors and factory functions; you can copy them, move them, store them in containers. Aggregates as references-with-shared-state is an anti-pattern.

p. 126

> Aggregates are the tactical-DDD pattern that maps the consistency-boundary discipline into code. The rule of thumb: one transaction = one aggregate. If you find yourself needing to modify two aggregates atomically, either (a) they should be one aggregate, or (b) the consistency should be eventual via a domain event. C++ aggregates as value types is non-negotiable in idiomatic code: structs with private constructors enforcing invariants, factory functions to create them, value semantics throughout. A PMR request arena makes this affordable: you pay arena cost per request instead of a heap allocation per aggregate (cpp-statelessness Doc 03, patterncatalyst.github.io/cpp-statelessness/docs/03-pmr/).

## [148] APPENDIX F · DDD · How DDD maps to our API stack (sldId 403)

- Bounded contexts → independently deployed services. One context per CMake project, one binary per service.
- Open-Host Services → published REST / gRPC / GraphQL APIs. Apicurio holds the Published Language; OpenMetadata makes it discoverable.
- Anti-Corruption Layers → API gateways (Apollo for GraphQL aggregation, Drogon services exposing a clean facade over messier internals).
- Domain events → Kafka topics. The event name in the topic matches the domain event name in C++. rdkafka++ producers per service.
- Aggregate roots → resource URLs in REST, top-level types in GraphQL, root messages in .proto. They name the thing the consumer interacts with.
- Hexagonal ports & adapters → a composition root in main() plus adapters (Example 19). Domain code is testable without any infrastructure spinning up.

p. 127

> The full DDD-to-stack mapping. Each row is something we've seen elsewhere in this deck — DDD names what we were already doing and gives us a vocabulary for arguing about it. The headline: DDD isn't extra work. It's a label for the disciplined parts of the work you should be doing anyway. Once you have the labels, the architectural discussions get shorter and the implementation discipline gets clearer.

## [149] Balancing Coupling (sldId 404)

Appendix G

Strength, distance, volatility — balance them, don't eliminate them.

> Section Appendix G divider: Balancing
>
> Coupling. Strength, distance, volatility — balance them, don't eliminate them.

## [150] APPENDIX G · COUPLING · Coupling is necessary — balance it, don't eliminate it (sldId 405)

- Two services that never interact are not coupled, and they are not cooperating either. Useful systems require coupling somewhere.
- The question is not 'how do I have no coupling' but 'where do I put the coupling I need, and how strong is it?'
- Coupling is local. Two services can be tightly coupled in one dimension (shared schema) and loosely in another (independent deploys).
- Optimal coupling depends on volatility: things that change together at the same rate should be coupled; things that change at different rates should be decoupled.
- Khononov's framing (Balancing Coupling, Addison-Wesley) is the synthesis: three dimensions of coupling, balanced against the distance between the coupled things.
- C++ specific: in-process coupling (one binary) is the strongest; cross-process same-host coupling is next; cross-host network coupling is weakest. Architectural decisions about coupling are also decisions about deployment topology.

p. 128

> Khononov's book is the best synthesis of coupling thinking I've seen. The headline insight: 'low coupling' as a slogan is wrong; the right framing is balanced coupling — matching the strength of coupling to the rate of co-change between the coupled things. For C++ specifically, the in-process / cross-process / cross-host hierarchy is meaningful because each step adds latency, failure modes, and operational complexity. A monolith with three tightly-coupled internal modules can be faster and more reliable than a microservices system that fakes loose coupling at the boundaries while still being tightly coupled in business logic.

## [151] APPENDIX G · COUPLING · Coupling has three dimensions (sldId 406)

Strength (integration intensity), distance (organisational + technical separation), volatility (rate of change).

p. 129

> Three dimensions, each measurable. STRENGTH: how intensely are the two things coupled — shared memory? shared schema? shared events? shared concepts only? DISTANCE: how far apart are they — same binary? same team? same company? same industry? VOLATILITY: how often does each thing change. The optimization rule: strength should match distance, and both should match co-volatility. Tightly coupled things at low distance changing together fast — that's a healthy relationship. Tightly coupled things at high distance, changing at different rates, cause pain.

## [152] APPENDIX G · COUPLING · The three dimensions, in practice (sldId 407)

- STRENGTH — the type of dependency: shared memory > shared schema > shared events > shared concepts > unrelated. Stronger means changes propagate more directly.
- DISTANCE — how far apart: same function > same class > same binary > same team > same company > unrelated parties. More distance means slower communication.
- VOLATILITY — rate of change: things change every day, every quarter, every year, never. Co-change is what matters; things that change together need short distance.
- Pain happens when strength is high but distance is also high — a shared-schema dependency between two teams that can't sync schedules. The dependency cost compounds.
- Health happens when strength matches both distance and co-volatility. Modules within a service can be tightly coupled because they're co-located, co-deployed, co-changed.
- Re-balancing: if strength and distance are mis-matched, move one or the other. Merge services (reduce distance), or extract the shared piece into a contract (reduce strength).

p. 130

> Practical guidance for spotting bad coupling. The strongest signal is the friction of co-ordinated changes — when a single business change requires syncing three teams to deploy on the same day, you have a strength/distance mismatch. The rebalancing tools: merge services to reduce distance (the strangler-fig in reverse), or factor the coupling into an explicit contract (a Published Language) to reduce implicit strength.

## [153] APPENDIX G · COUPLING · Integration strength: a ladder, worst to best (sldId 408)

Shared internal model is the worst; events with versioned schemas are the best. Most teams sit somewhere in the middle.

p. 131

> The ladder, from worst (top of coupling stack, hardest to evolve) to best (loosest, easiest to evolve): shared schema or shared model → shared library with breaking changes → synchronous RPC → REST contract → events with versioned schemas. Each step down adds a layer of indirection that absorbs change. Events with schema compatibility rules in Apicurio (§5, §11) are the best practical coupling for cross-service communication — the producer changes safely, the consumer changes safely, the registry rejects the breaking combination.

## [154] APPENDIX G · COUPLING · Strength in our system (sldId 409)

- Inside one C++ service: function/class coupling. Strength is high, distance is zero (same binary), co-volatility is high — this is healthy.
- Between C++ services via gRPC: contract coupling on .proto. Apicurio gates breaking changes; backwards-compatible evolution is mechanical.
- Between C++ services via Kafka: event-schema coupling. Lowest strength of all our patterns — producer and consumer are decoupled in time too.
- Between C++ services via shared library (libstateless, libtelemetry): API coupling, distributed via Conan with explicit version pins. Strength is moderate; co-deployment isn't required if ABI is stable.
- Between C++ services via shared database: avoid. This is the worst position — high strength, high distance, no rebalancing without effort. If you're here, treat it as a strangler-fig migration target.
- C++ ABI is a strength multiplier when it appears. Conan + a committed conan.lock pins versions; if every service rebuilds against the same Conan profile, coupling stays manageable. Drift breeds incidents.

p. 132

> Mapping the strength ladder to our specific stack. The C++-specific entries: shared C++ libraries (for example a libtelemetry wrapping OTel boilerplate) are a real form of coupling to manage explicitly. Conan lockfile discipline is what keeps it manageable. Every binary in the system pins to the same versions; upgrading the shared library means a coordinated re-lock across all consumers. The cost is non-trivial but bounded; the win is a single canonical implementation of cross-cutting concerns.

## [155] APPENDIX G · COUPLING · Balancing coupling: strength vs. distance (sldId 410)

High strength at low distance is healthy. High strength at high distance is pain. The balance defines architectural quality.

p. 133

> Khononov's balance diagram. Strength on one axis, distance on the other; the diagonal is the healthy zone. Off the diagonal on the strong-and-far side is the pain zone; on the weak-and-close side is wasted indirection that probably should be merged. Practical use: take any architectural review, plot each significant dependency on the grid, and look for the off-diagonal ones. Those are your improvement targets — either move them along strength (factor a contract) or along distance (merge or split services).

## [156] APPENDIX G · COUPLING · Distance and volatility (sldId 411)

- Co-volatility means two things change at the same time, in the same direction, in response to the same business or technical drivers. It's the third axis of balance.
- Co-volatile + close + strong = healthy: changes are local and coordinated.
- Co-volatile + distant + weak = pain: changes need to ripple, but the coupling layer absorbs and delays them.
- Independent volatility + distant + weak = excellent: things change on their own schedules without cross-team coordination.
- Independent volatility + close + strong = waste: you're paying coupling cost for things that don't need to move together. Re-decompose.
- C++ specific: a shared header file that ten services include is a strong, close coupling. If those services have independent volatility, every change to that header drags ten services into a coordinated release. That's a smell; factor the contract into a versioned wire interface.

p. 134

> Co-volatility is the most predictive of the three dimensions. Two things that don't change together don't need to be tightly coupled, regardless of how convenient it seems. Two things that do change together need to be close enough for that change to be cheap. Detection signal: count the recurring co-deploys. If service A and service B have to deploy together ten times a year, either they should be one service (merge) or their shared dependency needs to become a stable contract (factor).

## [157] APPENDIX G · COUPLING · Coupling and our APIs (sldId 412)

- REST contracts are moderate strength — additive change is safe, breaking change requires consumer migration. The registry gate prevents accidental breaks.
- gRPC contracts are moderate strength — same shape as REST but proto field numbers add an extra layer of permanence. Reserved tags prevent accidental reuse.
- GraphQL contracts are low strength on read paths (additive evolution + @deprecated) but moderate on write paths (mutation input changes).
- Event contracts (Kafka + Apicurio) are lowest strength — producer and consumer don't synchronize; the schema rules absorb most changes; replay is always possible.
- Cross-API coupling: the gateway/BFF (§3 composition) is an Anti-Corruption Layer — it absorbs strength so individual services don't have to.
- C++ specific: gRPC stubs are C++ code generated from .proto. The stub coupling is real (an ABI-incompatible protoc upgrade breaks every consumer). Pin protobuf in Conan; regenerate stubs in CI, never commit them.

p. 135

> Mapping the four wire protocols (App A's framing) to the coupling-strength axis. The general progression: REST and gRPC sit in the middle; events sit at the loose end; shared schemas sit at the tight end. C++-specific gotcha: gRPC stubs are generated C++ that gets compiled into every consumer. The stub generator (protoc) has its own version that must be consistent across consumers, and the .proto contract does not show it. Pin protobuf in Conan, regenerate in CI, and you're fine. Drift creates incidents.

## [158] APPENDIX G · COUPLING · Heuristics for balanced coupling (sldId 413)

- Match coupling strength to co-volatility. Things that change together should be coupled strongly enough that the change is one act, not three coordinated ones.
- Match coupling distance to coupling strength. Strong coupling at high distance is pain; the diagonal is where architectures are healthy.
- If two services always deploy together, merge them. If a single service has two pieces that never change together, split it.
- Make breaking changes explicit. The registry's BACKWARD/FORWARD rules + deprecation markers + sunset dates are how strong coupling stays manageable.
- Prefer events over RPC for cross-service coupling unless immediacy is required. The fire-and-forget-a-fact pattern is the lowest-strength practical coupling.
- C++ specific: in-process coupling between aggregates in one service is free — value semantics, RAII, type-checking at compile time. Don't break apart a healthy in-process design just because microservices are fashionable.

p. 136

> Six heuristics. The headline: coupling decisions are architecture decisions. Make them explicitly, not by accident. The C++-specific final bullet: a well-designed C++ monolith with clean in-process aggregates can outperform a poorly decomposed microservices system on latency, reliability, operational cost and developer velocity. The microservices decision should be driven by real DDD-bounded contexts and independent volatility, not by language fashion.

## [159] Graceful Shutdown (sldId 414)

Appendix H

RAII, std::stop_token, SIGTERM: the C++ toolkit.

> Section Appendix H divider: Graceful
>
> Shutdown. RAII, std::stop_token, SIGTERM: the C++ toolkit.

## [160] APPENDIX H · SHUTDOWN · Disposability is a promise you have to keep (sldId 415)

- Twelve-Factor IX (Disposability) — processes start fast and shut down gracefully. Kubernetes assumes this; it terminates pods constantly for scale-down, rollouts, node maintenance.
- Graceful means: stop accepting new work, finish in-flight work within a bounded window, release resources cleanly, exit. Not 'just die when SIGTERM arrives'.
- Failure modes when you skip it: dropped HTTP requests mid-response, uncommitted Kafka offsets (re-delivery), open DB transactions (held locks), partial saga steps (orphaned compensations).
- C++ has the strongest tools for this of any common language: RAII destructors run automatically on scope exit, std::stop_token (since C++20) propagates shutdown cooperatively, deterministic destruction order makes the cleanup sequence predictable.
- Where it gets hard: long-lived connections (WebSockets, SSE), in-flight saga steps, batch jobs. Each workload type has its own graceful-drain shape.

p. 137

> Graceful shutdown is where C++ has a clear advantage in cloud-native architecture. The language gives you tools (RAII, std::stop_token, deterministic destruction) that managed runtimes don't have, but you have to apply them consistently. This appendix is the architectural framing; Example 21 is the runnable C++ version, and cpp-statelessness Doc 09 covers the readiness and signal-handling side (patterncatalyst.github.io/cpp-statelessness/docs/09-health-checks/).

## [161] APPENDIX H · SHUTDOWN · What happens when Kubernetes stops a pod (sldId 416)

preStop hook (optional) → SIGTERM → terminationGracePeriodSeconds countdown → SIGKILL. Your job is to finish before SIGKILL.

p. 138

> The Kubernetes termination sequence in detail. (1) The pod is marked Terminating; Endpoints controller removes it from Service endpoints (this is async — there's a brief window where traffic can still arrive). (2) preStop hook runs if configured (useful for additional drain delays). (3) SIGTERM is sent to PID 1. (4) terminationGracePeriodSeconds countdown starts (default 30s). (5) SIGKILL if you haven't exited. The race condition in step 1: traffic can still arrive for a few seconds after SIGTERM. The response is to fail the readiness probe first, so the Service stops sending new traffic, before you stop accepting. The preStop hook is one common way to do this.

## [162] APPENDIX H · SHUTDOWN · The contract with Kubernetes (sldId 417)

- On SIGTERM, you have terminationGracePeriodSeconds to exit cleanly. Default 30s; set to whatever your slowest in-flight workload needs.
- Fail readiness first. The Service controller takes seconds to react to your readiness flip; start the countdown early so you stop receiving traffic before you stop accepting.
- Drain in-flight work bounded by the grace period. Reject new work immediately on SIGTERM; finish in-flight work for up to grace_period minus a safety margin.
- Release external resources (DB connections, Kafka consumer group membership, file locks) before exit so the next pod can take over cleanly without waiting for timeouts.
- Exit with 0. Non-zero exit codes get logged as 'crashed' and trigger restart policies you don't want during a normal scale-down.
- C++ specific: signal handlers must be async-signal-safe — set an atomic flag, don't call destructors or take locks. The flag is consumed by your main loop (or the std::stop_source) which does the real cleanup.

p. 139

> Six rules for the K8s graceful-shutdown contract. Five universal, one C++-specific. The async-signal-safety rule matters because installing a signal handler that does non-trivial work (taking locks, calling destructors, even calling printf) is undefined behaviour in C++. The correct pattern: atomic flag in the signal handler, main thread checks the flag and orchestrates shutdown. The main thread can then call std::stop_source::request_stop(), which propagates to every std::stop_token in the program; call it outside the handler, never inside it.

## [163] APPENDIX H · SHUTDOWN · Graceful means something different per workload (sldId 418)

HTTP server: finish in-flight responses. Kafka consumer: commit offsets, leave group. WebSocket: signal reconnect. Batch job: checkpoint.

p. 140

> Different workloads, different drain shapes. HTTP servers (Drogon): stop accepting new requests, finish in-flight responses, close connections. Kafka consumers: stop polling, commit the last successful offset, leave the consumer group cleanly so the group doesn't have to wait for session timeout to rebalance. WebSocket servers: signal clients to reconnect (close frame with reason), let the backplane fan-out continue on other pods. Batch jobs: checkpoint state, exit on a clean boundary. The C++ binary should have one shutdown coordinator that knows the order. A complete sequence: stop accepting → drain HTTP → stop Kafka poll → commit offsets → close DB pool → exit (cpp-statelessness Doc 09 walks through the signal-handler side, patterncatalyst.github.io/cpp-statelessness/docs/09-health-checks/).

## [164] APPENDIX H · SHUTDOWN · Graceful shutdown in Drogon (sldId 419)

[chip] c++23 · Drogon

```c++23
// order-service (excerpt), examples/21-graceful-shutdown/cpp: one SIGTERM drives the drain
std::atomic<bool> g_shutting_down{false};     // /readyz answers 503 once it is set
std::atomic<int>  g_in_flight{0};             // RAII InFlightGuard: one per request
extern "C" void sigterm_handler(int) {        // async-signal-safe: one atomic store
  g_shutting_down.store(true, std::memory_order_release);
}
void shutdown_watcher() {                     // outside signal context
  while (!g_shutting_down.load(std::memory_order_acquire))
    std::this_thread::sleep_for(50ms);        // (also returns on g_watcher_stop)
  const int delay = std::atoi(env("DRAIN_DELAY_SECONDS", "5"));
  std::this_thread::sleep_for(std::chrono::seconds(delay));    // endpoints update
  const auto deadline = std::chrono::steady_clock::now() + 20s; // bounded in-flight wait
  while (g_in_flight.load() > 0 && std::chrono::steady_clock::now() < deadline)
    std::this_thread::sleep_for(100ms);
  app().quit();                               // stop the listeners: run() returns
}
int main() {
  app().registerBeginningAdvice([] { std::signal(SIGTERM, sigterm_handler); });  // after init
  std::thread watcher(shutdown_watcher);      // ... handlers, addListener("0.0.0.0", 8080)
  app().run();  g_watcher_stop.store(true);  watcher.join();
  g_pool.reset();                             // close the database connections; exit 0
}
```

One SIGTERM → fail readiness → serve DRAIN_DELAY_SECONDS → drain in-flight (20 s) → quit → close the pool.

p. 141

> The application side of graceful shutdown, from the C++ example; one SIGTERM, the only signal Kubernetes sends before SIGKILL, drives all of it. (1) The SIGTERM handler only stores an atomic flag, which is async-signal-safe: no locks, no allocation, no destructors. Drogon installs its own SIGTERM handler that quits at once, so the example replaces it after initialisation with registerBeginningAdvice. /readyz answers 503 once the flag is set, which removes the pod from the Service endpoints while the process keeps serving the requests already routed to it.
>
> (2) A watcher thread does the rest outside signal context: it sees the flag, keeps serving for DRAIN_DELAY_SECONDS (5 s in Example 21; it plays the part of a preStop sleep) so the endpoint removal propagates, waits up to 20 seconds for the RAII InFlightGuard count to reach zero, and calls app().quit(), which stops the listeners so run() returns. (3) main() joins the watcher, closes the libpq pool and returns 0, inside the 30-second grace period. std::stop_token and std::jthread extend the same pattern to worker threads such as Kafka consumers: the watcher calls request_stop() after it sees the flag, never inside the handler. Deterministic destruction makes the teardown order predictable.

## [165] APPENDIX H · SHUTDOWN · The Kubernetes side: probes, preStop, grace period (sldId 420)

- readinessProbe — Kubernetes asks 'are you ready to serve traffic?' Periodic. Failing it removes the pod from Service endpoints. Use /readyz with the in-process readiness flag.
- livenessProbe — 'are you alive?' Failing it restarts the pod. Use sparingly; a too-aggressive liveness probe causes its own outages. Use /healthz with simple process-alive checks.
- startupProbe — 'have you finished starting yet?' Disables liveness until this passes. Useful for slow-starting workloads (C++ with large initialisation, model loading).
- preStop hook — runs before SIGTERM. Common pattern: 'sleep 5' to let Endpoint propagation finish before signal arrives. Or call a graceful-shutdown endpoint that flips readiness.
- terminationGracePeriodSeconds — bounds the entire termination. SIGKILL hits at the end. Default 30s; set as needed for your slowest workload's drain time.
- C++ specific: a Drogon binary's cold-start is sub-second, so startupProbe is rarely needed. Set terminationGracePeriodSeconds based on your longest in-flight gRPC/saga step + 5s safety margin.

p. 142

> The pod spec settings that pair with the in-process shutdown discipline. The combination is what makes graceful drain reliable: readiness flip + Service endpoint removal + preStop sleep + bounded grace period + signal handler + std::stop_token + RAII destructors. Every layer matters; missing one creates a failure mode.

## [166] APPENDIX H · SHUTDOWN · Beyond HTTP: messages, sockets, jobs (sldId 421)

- Kafka consumer drain: stop polling, finish processing in-flight messages, commit final offsets, call consumer.unsubscribe() to leave the group cleanly. Skipping unsubscribe forces other consumers to wait for session.timeout.ms.
- Kafka producer drain: producer.flush() before destruction. Otherwise in-memory batches die with the process; no error, just silent loss.
- WebSocket drain: send close frames with reason 1001 (going away) so clients reconnect immediately. The backplane (sw/redis++ pub/sub) keeps fan-out working on remaining pods.
- Long-running gRPC streams: send a status with code OK on the stream, then half-close. Clients should reconnect; the streaming pattern naturally supports this.
- Batch jobs and CronJobs: trap SIGTERM, checkpoint state, exit. The Kubernetes Job controller respects activeDeadlineSeconds; honor it.
- Saga steps in flight: the row-lock + state-machine pattern (App D) handles this automatically. The sweeper picks up the saga on the new pod and continues from the persisted state.

p. 143

> Workload-specific drain notes. Each row is a separate concern; the C++ binary has to orchestrate them in the right order. Order that works for a typical Drogon + Kafka + libpq service: (1) fail readiness, (2) stop Kafka producer (flush), (3) stop Drogon app (drains HTTP), (4) stop Kafka consumer (commits + unsubscribes), (5) close DB pool (RAII), (6) exit. Steps 3-5 can be deterministic via destruction order — main() returns; destructors run; exit code 0.

## [167] APPENDIX H · SHUTDOWN · Graceful shutdown checklist (sldId 422)

- Install an async-signal-safe SIGTERM handler that only flips an atomic readiness flag. No locks, no destructors, no printf; the main thread acts on the flag.
- /readyz endpoint returns 503 when readiness flag is false. Service controller removes the pod from endpoints within seconds.
- preStop hook with 'sleep 5' (or longer) so Endpoint propagation finishes before SIGTERM arrives at your handler.
- Pass std::stop_token to every long-running worker (Kafka consumer thread, batch processor, scheduled work). They check stop_requested() in their loop and exit cleanly.
- Use std::jthread (since C++20) for managed worker threads — automatic join + stop_token propagation. No raw std::thread::detach.
- Set terminationGracePeriodSeconds to longer than your slowest in-flight workload — and test it under load. Default 30s is rarely right for production.
- Connect RAII to teardown: connection pools, Kafka clients, OTel TracerProvider all destroy in reverse order when main() returns. Deterministic, no leaked file descriptors.

p. 144

> Seven rules. Following all of them gives you bounded, predictable, deterministic shutdown.

## [168] L7 Routing & Traffic Mgmt (sldId 423)

Appendix I

Software, not silicon: routing decisions across four layers and both directions.

> Section Appendix I divider: L7 Routing &
>
> Traffic Mgmt. Software, not silicon: routing decisions across four layers and both directions.

## [169] APPENDIX I · L7 ROUTING · L7 routing: software, not silicon (sldId 424)

- The hardware load balancer used to be where routing decisions lived. In cloud-native systems that work has moved into software — programmable, observable, runnable anywhere.
- L7 means application layer: the router sees the HTTP or gRPC envelope (host, path, method, headers, cookies, gRPC service.method) and can route on any of it.
- It lives in four layers — edge / ingress, API gateway, service mesh, and (sometimes) inside the app itself. Each makes a different type of L7 decision.
- It runs both directions: north/south (clients into your system) and east/west (service to service). Most L7 decisions happen on internal traffic.
- The open-source stack is composable: HAProxy, Nginx, Envoy, Istio, Linkerd, Kong, Traefik, Drogon, sol2/Lua, Open Policy Agent — plus a YAML or two.

p. 145

> L7 routing is a discipline, not a product. Routing spans four layers and both traffic directions, with many decisions per request. For C++ services the natural fit is the lowest layer that can express the decision — most external routing belongs in the mesh or gateway; business-rule routing belongs in the service itself.

## [170] APPENDIX I · L7 ROUTING · L4 vs L7: what each layer can decide on (sldId 425)

L4 sees connections; L7 sees the conversation — paths, headers, methods, cookies, gRPC service.method.

p. 146

> The key difference: L4 only sees connection-level information (IP, port, TLS SNI in some cases). L7 terminates the TLS connection and reads the HTTP/2 envelope: path, method, headers, cookies, body if needed. Every routing decision worth making lives at L7.

## [171] APPENDIX I · L7 ROUTING · The L7 capability menu (sldId 426)

- Routing rules: path / host / header / method / cookie / gRPC method → backend.
- TLS termination: decrypt at the edge, re-encrypt (or use mTLS) inward.
- Traffic management: canary, blue/green, A/B, header-based, geo, shadow.
- Payload modification: inject / strip headers, rewrite URLs, transform bodies.
- Resilience: timeouts, retries with backoff + jitter, circuit breakers, outlier ejection — the same toolkit from Appendix E, applied at the network.
- Cross-cutting: authn/authz, rate limiting, WAF, request mirroring, full traces and metrics on every hop.

p. 147

> Six capability categories. A modern L7 layer (Envoy/Istio) can do all of them; configure what you need, leave the rest at defaults. For C++ services downstream, the value is the same as for any language — security and resilience as platform config, no per-service code.

## [172] APPENDIX I · L7 ROUTING · Where L7 lives: the layered stack (sldId 427)

Four layers, north/south at the top, east/west at the bottom, each making a different type of L7 decision.

p. 148

> The four layers, top to bottom: edge / ingress (HAProxy, Nginx, cloud LB), API gateway (Kong, Traefik, custom Drogon binary), service mesh sidecar (Envoy via Istio/Linkerd), in-app router (Drogon + sol2/Lua for business-rule routing). Each layer is there because it makes decisions the layers in front of it can't. The mesh shouldn't route on business rules; the in-app router shouldn't terminate TLS.

## [173] APPENDIX I · L7 ROUTING · A request's L7 path (sldId 428)

One HTTP request is a chain of L7 decisions made by four independent components.

p. 149

> From client to backend, the same request hits 4-6 L7 decision points. Each adds latency (next-slide content), each adds resilience and observability. The job is to make sure each layer is earning its place; collapse the ones that aren't.

## [174] APPENDIX I · L7 ROUTING · Open-source L7 building blocks (sldId 429)

- HAProxy: fast, battle-tested L7 LB; ACL-driven config; classic ingress. Pure C, single binary.
- Nginx: ubiquitous web server / LB; location-block routing; widely used as ingress controller. Also C.
- Envoy: the modern L7 proxy; HTTP/2, gRPC, dynamic config; the sidecar of choice. Written in C++.
- Istio: a control plane built on Envoy; CRDs for routing, security, observability across the mesh.
- Kong, Traefik, Spring Cloud Gateway: opinionated API gateways with plugin ecosystems.
- Drogon + sol2 / Lua: when the routing logic is a business rule, push it into the C++ service — embedded Lua scripts that domain experts can edit, executed safely in a sandboxed VM.

p. 150

> All major L7 building blocks are open-source and well-maintained. For the C++ audience: Envoy is itself a C++ project (CNCF graduated, ~600k LOC modern C++). The C++ ecosystem is the foundation of cloud-native networking. For business-rule routing inside a Drogon service, sol2 (header-only modern C++ Lua wrapper, MIT license) embeds Lua as a sandboxed rule language — domain experts edit .lua files; the service hot-reloads them; the C++ code stays type-safe at its boundaries.

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

> HAProxy's ACL-driven config is the original L7-routing language. It's all C; the config is declarative; the matching is fast. For the C++ audience: HAProxy uses memory-arena allocation per request, the same pattern PMR enables for your own Drogon services. A canonical example of a low-latency C/C++ network stack.

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

> Nginx is the other big C network stack. The 'map' directive is its declarative routing language; location blocks pin behaviour by path; grpc_pass natively understands HTTP/2 + gRPC. For C++ teams who don't run Istio, Nginx + Drogon is a complete, fast, production-grade stack.

## [177] APPENDIX I · L7 ROUTING · Content-based routing in the mesh: Istio VirtualService (sldId 432)

[chip] yaml · Istio

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

> Istio's VirtualService is the K8s-native version of the HAProxy/Nginx routing config. Same L7 inputs (path, header, cookie); same dispatch model (first match wins); declarative GitOps-friendly. For a C++ service in a Kubernetes deployment, this is where your routing lives — not in C++ code.

## [178] APPENDIX I · L7 ROUTING · SSL / TLS termination at L7 (sldId 433)

- Edge terminates TLS so the L7 router can read and route on the request — you cannot inspect headers or paths through an encrypted connection.
- Re-encrypt or mTLS inward: terminate at the edge, then either plaintext within the cluster (rare today) or mTLS via the mesh (the modern default).
- Certificate management: cert-manager + Let's Encrypt for public certs; SPIFFE / SDS for service identity inside the mesh; Istio rotates pod certs automatically.
- TLS passthrough (no termination) when you need end-to-end encryption (gRPC client mTLS, regulated payloads); route by SNI only.
- Cost: TLS handshakes are real CPU. Modern stacks use session resumption, TLS 1.3 and HTTP/2 to amortise the cost across many requests.
- C++ specific: a Drogon service behind Istio never does TLS itself; the sidecar handles it. drogon::HttpAppFramework runs plaintext on the pod's localhost; mTLS is platform.

p. 154

> TLS at L7 is platform work. For C++ services, the win is that you don't link OpenSSL into your binary — Drogon runs plaintext, Istio's Envoy sidecar adds TLS at the network. The binary stays smaller, the certificate lifecycle is automatic, and rotation doesn't require restarting your service.

## [179] APPENDIX I · L7 ROUTING · Sticky sessions: cookie vs IP-hash vs none (sldId 434)

Convenient for legacy state, hostile to elastic scaling — prefer stateless behind a JWT.

p. 155

> Sticky sessions are an anti-pattern in cloud-native systems for the same reason WebSocket pinning is in App C: they tie the client to a specific pod, which breaks scale-down, rolling deployment, and graceful drain. For C++ services that need session state, the right answer is the same: externalize to Redis (sw/redis++) or carry state in JWT claims.

## [180] APPENDIX I · L7 ROUTING · Sticky sessions in practice (sldId 435)

- When you need them: legacy session state, a stateful WebSocket that hasn't been moved off-process yet, certain rate-limit windows tied to a token bucket per pod.
- Cookie-based is almost always the right choice over IP-hash: it survives NAT and lets clients explicitly drop the cookie.
- What stickiness breaks: even load balancing, fast pod restarts, scale-to-zero, blue/green flips, and a clean Appendix H graceful shutdown for any stateful pod.
- The right fix is usually upstream: move session state to Redis (via sw/redis++) or the JWT, use a backplane for WebSocket fan-out (see Appendix C), and treat every pod as disposable.

p. 156

> Stickiness is one of the things to design out of a C++ service, not into it. cpp-statelessness addresses this directly (patterncatalyst.github.io/cpp-statelessness/docs/01-deployment-posture/): the only state in the binary is request-scoped (arenas) or process-scoped (config, connection pools); never user-scoped state that ties a user to a pod.

## [181] APPENDIX I · L7 ROUTING · Intelligent traffic steering (sldId 436)

Six familiar shapes — each is a header or weight rule away.

p. 157

> Six steering patterns: canary, blue/green, A/B test, header-based dark launch, geographic routing, traffic mirroring. Each is a small variation on the same L7 primitive: match on something in the envelope, route to a different backend or split by weight. For a C++ service this is platform configuration — Istio CRDs in Git. The service stays oblivious.

## [182] APPENDIX I · L7 ROUTING · Canary release: weighted Istio routing (sldId 437)

[chip] yaml · Istio

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

> Canary deployment in Istio is two CRDs: VirtualService for the weight split, DestinationRule for the subset definitions. Pods get labelled by version (Deployment controllers handle this); the subset matches on the label; the weight controls the percentage.

## [183] APPENDIX I · L7 ROUTING · Header-based steering: dark launches (sldId 438)

[chip] yaml · Istio

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

> Header-based dark launch is the safest way to expose new code to production traffic. Your auth proxy (or a feature-flag service) sets x-acme-beta on a controlled population; the mesh routes them to v2; everyone else stays on v1. If v2 misbehaves, the blast radius is exactly the population you opted in.

## [184] APPENDIX I · L7 ROUTING · Payload modifications (sldId 439)

- Header injection: X-Request-Id, traceparent, X-Forwarded-For, identity claims — propagate context downstream so the trace stitches together.
- Header stripping: drop Authorization or PII headers before forwarding to a less-trusted backend; strip Server / X-Powered-By outbound.
- URL rewrites: /api/v1/orders → /orders internally; clean public URLs over messy service paths.
- Body transformation: rare but possible — protocol translation, redaction, format conversion (Envoy filters, Drogon middleware).
- Cost: body inspection means reading the full request into memory — the slowest L7 thing you can do. Use it sparingly, never on every request.

p. 160

> Five operations the mesh/gateway can perform on payloads. The headline is the cost note: body inspection breaks streaming and forces buffering. For a C++ service expecting streaming uploads or large request bodies, ensure the mesh policy doesn't accidentally buffer everything for header injection.

## [185] APPENDIX I · L7 ROUTING · Header injection and URL rewrites (sldId 440)

[chip] yaml · Istio

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
      uri: /orders                                  # external -> internal
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

> Header injection lets the mesh add context and identity and strip secrets before they cross a trust boundary. %DOWNSTREAM_PEER_URI_SAN% is the URI SAN of the client's mTLS certificate, the SPIFFE ID inside the mesh; Envoy creates x-request-id itself when a request has none, and traceparent travels with the request.
>
> For a C++ service downstream, these headers arrive in the request and the Drogon middleware reads them as plain values.

## [186] APPENDIX I · L7 ROUTING · Beyond the edge: routing inside the app (sldId 441)

- Sometimes the routing decision is a business rule the platform doesn't know about: route 'high-value-customer claims' here, 'European HL7 messages of type A03' there.
- Pushing those rules into HAProxy ACLs or VirtualService matches does not scale: domain experts own them, they change often, and they depend on the payload, not just the envelope.
- The pattern: an in-app router (Drogon middleware, a custom dispatcher) calls a rule engine and routes on the result. The engine reads the payload and business context.
- It runs inside one service, behind the mesh — not on the network. The mesh still does mTLS, retries and locality; the rule engine just decides where to send the message next.
- C++ specifics: the rules-engine ecosystem is thinner in C++ than in JVM/Python. Three pragmatic options: (1) embed Lua via sol2 (rules as Lua scripts, hot-reloadable); (2) hand-rolled std::function dispatch tables; (3) embed Python via pybind11 for power users.

p. 162

> Business-rule routing in C++. The Python deck uses durable-rules; for C++ services we recommend sol2 + Lua because: (a) sol2 is modern C++ (header-only, MIT licensed); (b) Lua is small, embeddable, and sandboxable; (c) domain experts can edit .lua files without C++ build tooling. The Lua rules and the dispatcher show the pattern in code.

## [187] APPENDIX I · L7 ROUTING · Drogon + sol2 / Lua: routing by business rules (sldId 442)

Drogon is the HTTP front; embedded Lua is the rules engine; rdkafka++ (librdkafka) does the dispatch.

p. 163

> The C++ in-app router. Drogon receives the HTTP request; enrichment gathers business context (database lookups, downstream calls); Lua rules evaluate and return the list of destinations; librdkafka publishes to each. Why sol2/Lua vs alternatives: Lua compiles to small bytecode (~50KB VM), runs in a sandbox (no I/O unless you expose it), and reloads instantly. Rules can be tested independently of the C++ service. sol2 makes the C++ ↔ Lua glue type-safe.

## [188] APPENDIX I · L7 ROUTING · The rules, externalised: Lua (sldId 443)

[chip] lua

```lua
-- orders_rules.lua  —  edited by domain experts, not developers
-- Each rule returns a list of destinations; the dispatcher fans out.

function route(order, ctx)
  local dests = {}

  -- high-value VIP orders
  if order.amount_cents > 50000 and ctx.tier == "VIP" then
    table.insert(dests, "kafka:orders.priority")
    table.insert(dests, "http:notify-vip")
  end

  -- European orders -> EU region
  if order.region == "EU" then
    table.insert(dests, "kafka:orders.eu")
  end

  -- catch-all
  if #dests == 0 then
    table.insert(dests, "kafka:orders.default")
  end
  return dests
end
```

Domain experts read and write the Lua. Reload-on-change, sandboxed, no recompile. The C++ binary is the runtime; the rules are data.

p. 164

> Lua as a rules language. The script lives in a ConfigMap or a Git-versioned file (ROUTING_RULES_FILE in Example 22); the service compiles it once at startup, so a bad script stops the rollout instead of reaching traffic. Sandboxing is a sol2 configuration — only expose the C++ functions you want the rules to call (no os, no io, no debug). Example 22 changes the rule inputs (thresholds, topics) live through PUT /rules; a new script version ships as a rollout. A file watcher that swaps in a freshly compiled Lua state between requests is an extension, not part of the example.

## [189] APPENDIX I · L7 ROUTING · The dispatcher, in Drogon (sldId 444)

[chip] c++ · Drogon + sol2

{% raw %}
```c++
// dispatcher.cpp — Drogon controller + sol2 + librdkafka
#include <sol/sol.hpp>
class Router {                                // process-scoped
  sol::state lua_;
 public:
  Router() {
    lua_.open_libraries(sol::lib::base, sol::lib::table);
    lua_.script_file("/etc/orders/rules.lua");  // load DSL
  }
  std::vector<std::string> evaluate(const Order& o, const Ctx& c) {
    return lua_["route"](o, c);              // call route()
  }
} router;
Task<> Orders::route(HttpRequestPtr req, auto cb) {
  auto order = parse<OrderIn>(req);
  auto ctx   = co_await enrich(order);        // DB / HTTP
  auto dests = router.evaluate(order, ctx);   // rules
  for (const auto& dest : dests) {            // fan-out
    auto [proto, target] = split(dest, ':');
    if (proto == "kafka") produce_to(*producer_, target, order.id, to_json(order));
    else if (proto == "http") co_await http_.post(target, order);
  }
  cb(json_response({{"routed_to", dests}}));
}
```
{% endraw %}

Enrich → evaluate → dispatch. The C++ binary is the type-safe runtime; Lua rules are the editable DSL.

p. 165

> The complete in-app router. Router is process-scoped (one Lua state per binary); evaluate() calls into the Lua route() function with strongly-typed Order and Ctx structs (sol2 handles the marshalling). The handler enriches, evaluates, dispatches. Performance note: Lua evaluation runs at memory-copy speed for table-of-strings results — tens of microseconds per evaluation. Slow compared to native C++ but fast compared to the gRPC and Kafka calls that follow it. The right ratio.

## [190] APPENDIX I · L7 ROUTING · Every L7 hop costs time (sldId 445)

Typical p50/p99 added per stage — the budget you spend before your service even runs.

p. 166

> L7 layers earn their keep but they're not free. Each hop adds 0.1-2ms p50 and 1-10ms p99 depending on what it's doing. Body-inspection layers are the slow ones. For C++ services this budget matters: a Drogon binary handling 5ms p99 of business work behind a stack of 5 L7 layers (edge + gateway + ingress + sidecar in + sidecar out) may see total p99 in the 15-25ms range. That's still fine for most workloads, but if you're sub-ms-critical, collapse layers.

## [191] APPENDIX I · L7 ROUTING · L7 pitfalls and how to avoid them (sldId 446)

- Too many hops: edge → gateway → ingress → mesh sidecar in → mesh sidecar out adds up fast. Collapse layers that aren't earning their place.
- Regex-heavy ACLs / matches: each regex evaluation is real CPU. Prefer exact / prefix matches; use regex only when needed.
- Sticky sessions break elasticity without any error: the auto-scaler can't rebalance, restarts are painful, scale-to-zero is gone.
- Body inspection on every request: blows memory, kills streaming. If you must transform bodies, do it on a small percentage or just at the edge.
- Sync auth lookups on the hot path: cache validated tokens, validate JWT signatures locally, never do a per-request DB lookup for identity.
- Misaligned timeouts and retries between layers — a 30s gateway timeout + 3 mesh retries with 10s each = a retry storm at the bottom (see Appendix E).

p. 167

> Six universal L7 pitfalls. Aligning timeouts is the most common operational mistake: review the full stack's retry × timeout math before going to production. A 'low' timeout at the top of the stack plus retries further down can amplify into a thundering herd.

## [192] APPENDIX I · L7 ROUTING · East / West: L7 between services, inside the mesh (sldId 447)

Every service-to-service call is L7-routable through the sidecars.

p. 168

> East/west traffic, service-to-service inside the cluster, is the majority of traffic in a microservices system. The same L7 routing primitives that handle external traffic (VirtualService, DestinationRule) also handle internal. For a C++ Drogon → gRPC Inventory call, both pods have Envoy sidecars; mTLS happens automatically; outlier detection ejects misbehaving inventory pods; canary weights work between services.

## [193] APPENDIX I · L7 ROUTING · Why east/west L7 matters (sldId 448)

- Internal traffic dominates: in a microservices system the volume of east/west calls dwarfs north/south by 10x or more.
- Security: mTLS everywhere by default — every internal call has an identity, encryption and an audit trail without per-service code.
- Resilience: timeouts, retries, circuit breakers and outlier ejection live in the sidecar, applied uniformly to every internal hop.
- Observability: every internal call gets a span, latency histogram and per-route success rate — the request lifecycle from §11, populated automatically.
- Locality: prefer same-zone or same-region pods so internal RTT stays in single-digit milliseconds, and graceful failover when a zone goes.
- Routing decisions: header-based canaries and weighted releases work east/west too — you can canary a backend service that has no external traffic at all.

p. 169

> Six reasons east/west L7 matters. For a C++ shop, the headline is that all of this happens without modifying your binary — gRPC clients in your Drogon service talk to the localhost Envoy sidecar, which handles mTLS, retries, outlier detection, and observability uniformly.

## [194] APPENDIX I · L7 ROUTING · Istio for east/west: DestinationRule + VirtualService (sldId 449)

[chip] yaml · Istio

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata: { name: payments }
spec:
  host: payments.acme.svc.cluster.local
  trafficPolicy:
    connectionPool: { http: { http2MaxRequests: 1000 } }
    outlierDetection: { consecutive5xxErrors: 5, interval: 30s, baseEjectionTime: 30s }   # eject
    loadBalancer: { localityLbSetting: { enabled: true } }                                # same zone
  subsets:
  - { name: v1, labels: { version: v1 } }
  - { name: v2, labels: { version: v2 } }
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata: { name: payments }
spec:
  hosts: [payments.acme.svc.cluster.local]   # internal DNS — east/west
  http:
  - route:
    - { destination: { host: payments, subset: v1 }, weight: 95 }
    - { destination: { host: payments, subset: v2 }, weight: 5 }
```

Same CRDs as north/south, pointed at an internal host — outlier detection, locality LB, canary weights between services, no app code.

p. 170

> Same Istio CRDs work east/west. The hostname is the internal service DNS (payments.acme.svc.cluster.local). Outlier detection ejects misbehaving pods; locality LB prefers same-zone for latency; canary weights work between services that have no external traffic. For C++ services this is all transparent — your gRPC client just uses the service DNS name and the platform does the rest.

## [195] APPENDIX I · L7 ROUTING · gRPC east/west specifics (sldId 450)

- gRPC is HTTP/2 under the hood, so it works natively in any L7 router that speaks HTTP/2 (Envoy, Istio, modern HAProxy/Nginx).
- Route by gRPC service.method: the URI path is /package.Service/Method — use a uri prefix match in Istio, grpc_pass in Nginx, or path_beg in HAProxy.
- Header-based balancing matters more for gRPC: connections are long-lived and multiplexed, so least-request or per-request load balancing beats round-robin.
- Streaming RPCs (server-streaming, client-streaming, bidi): retries are dangerous if the stream is non-idempotent — cap retries to UNARY calls in the mesh policy.
- Trailers carry status: a 200 + a non-OK trailer is the gRPC equivalent of a 5xx — outlier detection has to be configured to read trailers, not just the status line.
- C++ specifics: grpc::Channel reuse is critical — open one channel per target service, share it across requests. The sidecar load-balances across upstream pods on top of that channel.

p. 171

> Five universal gRPC east/west rules plus one C++-specific one. Channel reuse in gRPC C++ is non-negotiable: creating a new grpc::Channel per request is a 10ms overhead minimum (connection setup + HTTP/2 handshake). One channel per upstream service, shared by reference, lives for the binary's lifetime.

## [196] APPENDIX I · L7 ROUTING · When to use which L7 layer (sldId 451)

- Edge / ingress: TLS termination, host/path routing, WAF, public-facing rate limits. Anything north/south that affects all clients.
- API gateway: cross-cutting product policy — auth, per-consumer rate limits, request transformation, monetisation, key management.
- Service mesh: east/west routing, mTLS, retries, outlier detection, canaries between internal services. The default home for service-to-service L7.
- In-app router (Drogon + sol2 / Lua): when routing depends on business rules, payload content, or decisions that domain experts must own.
- Rule of thumb: prefer the lowest layer that can fully express the decision, and never push business rules into mesh CRDs.

p. 172

> Four layers, one rule: lowest layer that can express the decision. A path-based route belongs in the ingress; a per-customer rate limit belongs in the gateway; an outlier-eject belongs in the mesh; a 'route by claim type' decision belongs in the service with embedded rules.

## [197] APPENDIX I · L7 ROUTING · L7 routing checklist (sldId 452)

- Pick one ingress, one gateway, one mesh — don't run three competing L7 layers because each team had a favourite.
- TLS terminates at the edge; mTLS between services in the mesh; cert rotation is automatic (cert-manager + SDS), not a quarterly outage.
- Routing rules live in Git, reviewed like code; GitOps reconciles them; rollback is a git revert.
- Every L7 layer emits traces and metrics — sample the spans, alert on per-route SLOs, watch for retry budget exhaustion.
- Stickiness is an exception, not a default; business rules belong in a rule engine inside a service, not in network YAML.
- Test under load and under failure: bring a pod down, eject a zone, ramp a canary, verify the mesh does what the YAML says.
- References: HAProxy / Nginx / Envoy docs; Istio traffic management guide; sol2 (header-only modern C++ Lua bindings); Open Policy Agent for declarative policy; Drogon docs for middleware.

p. 173

> Seven rules. The headline: L7 routing is platform discipline, observed through telemetry, tested under failure.

## [198] Monolith to Microservices (sldId 453)

Appendix K

Patterns that survive the migration with the system still running.

> Section Appendix K divider: Monolith to
>
> Microservices. Patterns that survive the migration with the system still running.

## [199] APPENDIX K · MONOLITH · A monolith is a unit of deployment (sldId 454)

One process, one binary, one heartbeat. All modules live or die together. Often the right starting point — don't be ashamed of it.

p. 174

> A monolith is a unit of deployment, not a unit of design. One C++ binary with well-organised internal modules is a monolith; one C++ binary with everything in main.cpp is also a monolith. They're not the same thing. For C++ specifically, a single binary has real advantages: in-process function calls are nanoseconds, no serialisation, no network failure modes, deterministic destruction order, shared memory between modules is free. Don't break apart a healthy C++ monolith just because microservices are fashionable.

## [200] APPENDIX K · MODULAR MONOLITH · The modular monolith — often the right destination (sldId 455)

Still one deployable, but with strict in-process module boundaries enforced by build tooling — not by gentlemen's agreement.

p. 175

> The modular monolith is the destination many systems should aim for, not a stop on the way to microservices. One binary, strict module boundaries, separate teams own separate modules. C++ enforcement mechanisms: separate CMake projects per module, public/private include directories, link visibility settings, namespace discipline. The compiler is your friend here — make boundary violations into build errors, not code review failures.

## [201] APPENDIX K · DECOMPOSED DBS · Modular monolith with decomposed databases (sldId 456)

Data ownership becomes per-module — the hardest part of the split, done while still one process. The next step is mechanical.

p. 176

> Database decomposition is harder than process decomposition. By splitting the data first while you're still one binary, you discover the foreign-key entanglements, the shared utility tables, the read-only joins you didn't know existed — and you fix them in one place, in one binary, with one team's release cycle. When the data is per-module, breaking the binary apart is mechanical: each module already has its own libpq connection pool, its own schema, its own migrations. Convert each module's interface to a network protocol (gRPC, REST), ship them as separate Drogon binaries, point them at their schemas. Done.

## [202] APPENDIX K · STRANGLER FIG · Identify → move → redirect (sldId 457)

Named after the strangler fig vine: grow the new system around the old until the old can be removed.

p. 177

> Martin Fowler's strangler fig pattern is the safest large-migration approach known. Three steps per slice: (1) Identify the seam — what is the boundary between the piece you're extracting and the rest of the monolith. (2) Move — implement that piece as a new C++ service with its own data. (3) REDIRECT — point traffic at the new service. Repeat. The monolith shrinks; the new system grows; at no point is the system down for more than a config change.

## [203] APPENDIX K · STRANGLER FIG · With a proxy — step zero of every migration (sldId 458)

Introduce the routing layer first, before extracting anything. Then redirection becomes a config change, not a release.

p. 178

> The most important step in a strangler migration is putting the proxy in front of the existing monolith before you extract anything. Day 0: 100% of traffic still goes to the monolith; the proxy is just forwarding. Day 1+: you can shift any route to a new service with a config change. For a C++ shop the proxy can be HAProxy, Nginx, Envoy/Istio, or even a Drogon binary with a single forwarding rule. The technology matters less than the operational property: redirection is now a config change, not a release.

## [204] APPENDIX K · STRANGLER FIG · With proxy + redirection (sldId 459)

The proxy splits traffic between the new service and the shrinking monolith. Roll forward by widening the route; roll back by narrowing.

p. 179

> Each new service starts with a tiny slice of traffic (1%, 5%) and widens as confidence grows. The proxy controls the split — same primitive as the canary release pattern from App I, applied to migration. Critical observability: at the proxy, per-route success rates and latencies for both the old and the new side. If the new service's error rate spikes during a widening, the proxy narrows automatically (circuit breaker) or you narrow manually with a config push. Either way, no release required.

## [205] APPENDIX K · STRANGLER FIG · With a shared database — a deliberate intermediate state (sldId 460)

Process boundary first, data boundary later. Useful intermediate state, not a destination. Schema coupling will bite eventually.

p. 180

> Sometimes you'll extract a service before extracting its data — both old and new code read/write the same tables. This is a useful intermediate state, not a destination. It lets you ship the new service early and prove the contract before the data migration. But schema coupling is real coupling (Appendix G). Two binaries owning the same tables means schema changes coordinate across teams; ALTER TABLE has a blast radius beyond your binary. Plan the data extraction before you start; budget time for it; don't let the intermediate state become permanent.

## [206] APPENDIX K · ROUTING · Content-based routing during migration (sldId 461)

[chip] c++ · Drogon

```c++
// router/src/main.cpp (excerpt): route POST /orders by tenant during cutover
g_service_urls["monolith"]    = env_m ? env_m : "http://monolith:8080";
g_service_urls["new-service"] = env_n ? env_n : "http://new-service:8080";
g_tenant_routes["acme"] = "new-service";            // cut Acme over first
g_default_service = "monolith";                     // everyone else: legacy

app().registerHandler("/orders",
    [](const HttpRequestPtr& req, std::function<void(const HttpResponsePtr&)>&& cb) {
      auto body = req->getJsonObject();             // decide by content
      std::string tenant;
      if (body && body->isMember("tenant")) tenant = (*body)["tenant"].asString();
      forward_request(resolve_upstream(tenant), Post, "/orders",
                      std::string(req->body()), std::move(cb));
    },
    {Post});

// forward_request(): drogon::HttpClient to the chosen upstream, 502 on failure
auto client = HttpClient::newHttpClient(upstream);
auto fwd = HttpRequest::newHttpRequest();
fwd->setMethod(method); fwd->setPath(path); fwd->setBody(body);
client->sendRequest(fwd, [cb](ReqResult result, const HttpResponsePtr& resp) {
  cb(result == ReqResult::Ok ? copy_of(resp) : bad_gateway());   // simplified
});
```

Read the body, decide by content (tenant here; region or a feature flag work the same way), forward to the right backend. Cutover by attribute, not by URL.

p. 181

> Content-based routing during migration is the L7 + business-logic split from App I, applied to cutover. The Drogon handler reads the request body, decides by tenant, and forwards with Drogon's HttpClient. Most teams put this in a sidecar (Envoy with Lua filter, or a dedicated Drogon proxy) so the migration logic doesn't pollute every service. Performance note: reading the body means the middleware is no longer streaming — acceptable during migration, but not a production pattern long-term.

## [207] APPENDIX K · DECORATOR · The decorating collaborator (sldId 462)

The new service wraps the legacy one, adds capability, then becomes the API. Useful when you can't modify the legacy code.

p. 182

> The decorating collaborator wraps a system you can't change (vendor product, mainframe, legacy COBOL service) and adds capabilities — caching, eventing, transformation, auditing. Over time, the decorator becomes the API consumers know; the underlying legacy can be replaced without consumers noticing. For C++ this is a natural Drogon pattern: your service exposes the public API, calls the legacy via cpp-httplib or gRPC, layers sw/redis++ caching and librdkafka events around it. The legacy stays untouched; the new behaviour lives in your code.

## [208] APPENDIX K · DECORATOR · A decorating collaborator in Drogon (sldId 463)

[chip] c++ · Drogon

```c++
// Drogon decorator wrapping a legacy /orders API: Redis caching of GET
// responses and Kafka event emission on writes. The legacy service is unchanged.
class OrdersDecorator : public drogon::HttpController<OrdersDecorator> {
 public:
  METHOD_LIST_BEGIN
    METHOD_ADD(OrdersDecorator::getOrder,   "/orders/{oid}", Get);
    METHOD_ADD(OrdersDecorator::placeOrder, "/orders",       Post);
  METHOD_LIST_END
  Task<> getOrder(HttpRequestPtr req, auto cb, std::string oid) {
    auto key = "order:" + oid;
    if (auto hit = cache_.get(key)) {                    // 1. hit (sw/redis++)
      cb(json_response(*hit)); co_return;
    }
    auto body = co_await legacy_.get("/orders/" + oid);  // 2. miss → legacy
    cache_.setex(key, 60, body);                         // 3. populate
    cb(json_response(body));
  }
  Task<> placeOrder(HttpRequestPtr req, auto cb) {
    auto body = co_await legacy_.post("/orders", req->body());  // 1. legacy first
    auto id   = json::parse(body)["id"].get<std::string>();
    produce_to(*producer_, "order.placed", id, body);          // 2. emit (rdkafka++)
    cache_.del("order:" + id);                                 // 3. invalidate
    cb(json_response(body));
  }
```

Drogon wraps the legacy: caching with sw/redis++, events with librdkafka, no legacy code changes.

p. 183

> Idiomatic C++ decorator. legacy_ wraps Drogon's HttpClient; cache_ is sw/redis++; producer_ is a librdkafka producer. The pattern: try cache, call legacy on miss, populate cache. For writes, call legacy first, emit event after, invalidate cache. What you gained without touching the legacy: ~100x faster reads on cache hits, event-stream integration with downstream consumers, an OTel-instrumented hop you can observe.

## [209] APPENDIX K · DECISIONS · Choosing the right migration pattern (sldId 464)

- Modular monolith first, microservices later — the cheapest decomposition is often inside one process. Many systems never need to leave this state.
- Decompose the database before decomposing the deployment. The data split is the hard part; doing it in one process is much cheaper than coordinating across services.
- Always introduce the proxy first — the routing layer is what makes incremental cutover possible. No proxy = no incremental migration.
- Strangler with shared database is a transition state. Plan its end before you start it. Schema coupling is debt that accrues.
- Content-based routing when you need to cut over by tenant / region / segment instead of by URL. Costs CPU at the proxy; buys precise risk control.
- Decorating collaborator when you need to add behaviour to a system you can't modify. Most useful for vendor / 3rd-party / legacy-mainframe wrappers.
- C++ specific: a well-modularised C++ monolith is often faster and more reliable than the microservices system that replaces it. The migration is worth doing when team scaling or independent deploy cadence demands it — not because microservices are fashionable.

p. 184

> Seven heuristics. The headline: C++ monoliths can be excellent. The migration is a business / team decision, not a technical one. When you do migrate, do it in this order: modularise inside the binary → split the database → extract one service at a time behind a proxy → repeat. Reversibility at every step.

## [210] Caching Patterns (sldId 465)

Appendix L

Six patterns for keeping a cache useful and your data correct.

> Section Appendix L divider: Caching
>
> Patterns. Six patterns for keeping a cache useful and your data correct.

## [211] APPENDIX L · WHY CACHE · Five things a cache earns you (sldId 466)

- Application performance — a cache hit is microseconds; a database round trip is milliseconds. The hot path becomes ~100x faster on hits.
- Backend load — caching shields the database from repeated reads of unchanged data. Read-heavy workloads can offload 80-95% of queries with a sensible TTL.
- Throughput — the same Pod fleet serves dramatically more requests because it spends less time waiting on the DB. Vertical scaling without buying anything.
- Predictable performance — p99 latency stops being a function of DB load. Tail latencies flatten because the hot path doesn't contend on the same lock-bound resource as everyone else.
- Database cost — fewer queries means smaller (or fewer) DB instances, smaller IOPS budgets, less replication bandwidth. Cache is almost always cheaper than the DB tier it offloads.
- Trade-off: every cache adds a consistency story, an invalidation story, and a failure-mode story. Pick the pattern that matches the consistency you need from the six patterns in this appendix.

p. 185

> Five reasons to cache, one warning. For a C++ service the cache is usually sw/redis++ talking to a Redis instance in the same cluster. Latency to Redis is ~0.5ms p50; to Postgres ~5-50ms p50 depending on query — so the hit is real.

## [212] APPENDIX L · CACHE-ASIDE · Cache-aside (look-aside) — the default (sldId 467)

The application reads cache, falls back to DB, populates cache. Explicit and simple; the most common pattern.

p. 186

> Cache-aside is the pattern you start with. The application owns the cache lookup, the DB fetch, and the cache populate. Invalidation on write is explicit. The simplest model, but every caller has to remember the discipline. For C++, the Drogon handler does: try sw/redis++ get, on miss query libpq, populate the cache, return.

## [213] APPENDIX L · CACHE-ASIDE · Cache-aside with sw/redis++ + libpq (sldId 468)

[chip] c++ · Drogon

{% raw %}
```c++
// Cache-aside with sw/redis++ + libpq.
#include <sw/redis++/redis++.h>
constexpr int TTL = 60;                       // seconds
Task<> Products::get(HttpRequestPtr req, auto cb, std::string pid) {
  auto key = "product:" + pid;
  if (auto cached = cache_.get(key)) {        // 1. lookup
    cb(json_response(*cached)); co_return;    // hit
  }
  PgConn conn = co_await pg_.acquire();
  auto row = conn.exec_params(                // 2. miss → DB
    "SELECT id, name, price_cents FROM products WHERE id = $1", pid);
  if (row.empty()) throw HttpException{404};
  auto body = to_json(row).dump();
  cache_.setex(key, TTL, body);               // 3. populate
  cb(json_response(body));
}
Task<> Products::update(HttpRequestPtr req, auto cb, std::string pid) {
  auto body = req->bodyJson();
  PgConn conn = co_await pg_.acquire();
  conn.exec_params("UPDATE products SET name=$1, price_cents=$2 WHERE id=$3",
                    body["name"], body["price_cents"], pid);
  cache_.del("product:" + pid);               // 4. invalidate
  cb(json_response({{"ok", true}}));
}
```
{% endraw %}

Try cache; on miss, hit DB and populate. Invalidate on write. Three operations — the rest is conventions about TTL and naming.

p. 187

> The canonical C++ cache-aside. sw/redis++ Redis class is process-scoped (one connection pool); the get() returns std::optional<std::string>. libpq through a PgConn checked out from a process-scoped pool (ScopedConn in cpp-statelessness Doc 07, patterncatalyst.github.io/cpp-statelessness/docs/07-state-externalization/). JSON via nlohmann::json. The discipline is in three lines: try cache, on miss query DB and populate, invalidate on write.

## [214] APPENDIX L · READ-THROUGH · Read-through — the cache fetches on miss (sldId 469)

Application sees one interface; the cache library handles DB fallback transparently.

p. 188

> Read-through hides the cache-vs-DB decision behind a single get() interface. Same semantics as cache-aside but the discipline is in one place. In C++ this is naturally a template — the loader is parametrised.

## [215] APPENDIX L · READ-THROUGH · Read-through: a typed loader wrapper (sldId 470)

[chip] c++ · template

```c++
// Read-through wrapper. Caller just calls get(); the template handles the rest.
template <typename T>
class ReadThrough {
  using Loader = std::function<Task<std::optional<T>>(const std::string&)>;
  // ... members: redis_, loader_, ttl_, prefix_
 public:
  ReadThrough(sw::redis::Redis& r, Loader l, int ttl, std::string p)
    : redis_(r), loader_(std::move(l)), ttl_(ttl), prefix_(std::move(p)) {}
  Task<std::optional<T>> get(const std::string& id) {
    auto key = prefix_ + id;
    if (auto hit = redis_.get(key))           // cache hit
      co_return T::from_json(json::parse(*hit));
    auto value = co_await loader_(id);        // miss → loader
    if (value)
      redis_.setex(key, ttl_, value->to_json().dump());
    co_return value;
  }
};
// Wire it up once at startup — callers don't see Redis directly:
ReadThrough<Product> products{ redis_, &load_product_from_db, 60, "product:" };
Task<> Products::get(HttpRequestPtr req, auto cb, std::string pid) {
  auto p = co_await products.get(pid);
  cb(p ? json_response(*p) : not_found());
}
```

One template, one prefix, one TTL, one loader: wire it up once and every caller gets the cache-aside discipline by default.

p. 189

> Templated read-through. Type-safe at compile time (the cache returns T, not bytes); the loader is a std::function returning Task<std::optional<T>>. Compared to Python's dynamic version, the C++ version forces you to declare the type but rewards you with a zero-cost interface — the compiler inlines through it. One ReadThrough<T> per cached type lives at process scope.

## [216] APPENDIX L · WRITE-THROUGH · Write-through — cache and DB written synchronously (sldId 471)

Every write hits both the cache and the DB. Cache is never stale; writes pay both latencies.

p. 190

> Write-through trades write latency for read freshness. After a successful write, the cache reflects the new value immediately — no stale-read window. Cost: write latency is DB + cache, not DB alone. For read-heavy workloads with infrequent writes, the trade is excellent.

## [217] APPENDIX L · WRITE-THROUGH · Write-through with sw/redis++ + libpq (sldId 472)

[chip] c++ · Drogon

{% raw %}
```c++
Task<> Products::update(HttpRequestPtr req, auto cb, std::string pid) {
  auto body = req->bodyJson();
  auto key  = "product:" + pid;
  PgTxn txn = co_await pg_.begin();
  // 1. write the DB first — it's the source of truth
  txn.exec_params("UPDATE products SET name=$1, price_cents=$2 WHERE id=$3",
                   body["name"], body["price_cents"], pid);
  auto updated = txn.fetch_one(
    "SELECT id, name, price_cents FROM products WHERE id=$1", pid);
  co_await txn.commit();
  // 2. write the cache second — set, don't invalidate
  cache_.setex(key, TTL, to_json(updated).dump());
  cb(json_response({{"ok", true}}));
}
// Alt: trust the request body (faster, but server-side defaults may diverge)
Task<> Products::updateFast(HttpRequestPtr req, auto cb, std::string pid) {
  auto body = req->bodyJson();
  PgTxn txn = co_await pg_.begin();
  txn.exec_params("UPDATE products SET name=$1, price_cents=$2 WHERE id=$3",
                   body["name"], body["price_cents"], pid);
  co_await txn.commit();
  body["id"] = pid;
  cache_.setex("product:" + pid, TTL, body.dump());   // trust body
  cb(json_response({{"ok", true}}));
}
```
{% endraw %}

DB first (source of truth), cache second (read-back the canonical row, or trust the body for speed).

p. 191

> Two variants. The safe version (top) reads back the canonical row after the write to capture server-side defaults, triggers, computed columns. The fast version (bottom) trusts the request body for the cache value — works if your domain has no server-side modifications. Pick the one that matches your data model.

## [218] APPENDIX L · WRITE-AROUND · Write-around — writes skip the cache (sldId 473)

Writes go to the DB only. The next read populates the cache lazily. Good for write-heavy, low-re-read workloads.

p. 192

> Write-around suits append-heavy data: events, logs, telemetry, audit records. Writes go straight to the DB and never touch the cache (which would just thrash). Reads use cache-aside; the rare re-read populates lazily.

## [219] APPENDIX L · WRITE-AROUND · Write-around with selective read-side caching (sldId 474)

[chip] c++ · Drogon

{% raw %}
```c++
// Common with append-heavy data: events, logs, telemetry.
// Writes go straight to DB. Cache is irrelevant on writes.
Task<> Events::record(HttpRequestPtr req, auto cb) {
  auto body = req->bodyJson();
  PgTxn txn = co_await pg_.begin();
  txn.exec_params(
    "INSERT INTO events (id, type, payload, ts) VALUES ($1, $2, $3, NOW())",
    body["id"], body["type"], body["payload"].dump());
  co_await txn.commit();
  // no cache write here — most events are never read again
  cb(json_response({{"ok", true}}));
}
// ... optional variant: after the same INSERT, cache_.del("event:" + id)
// Read side is standard cache-aside
Task<> Events::get(HttpRequestPtr req, auto cb, std::string eid) {
  auto key = "event:" + eid;
  if (auto hit = cache_.get(key)) { cb(json_response(*hit)); co_return; }
  auto row = co_await pg_.fetch_one("SELECT * FROM events WHERE id=$1", eid);
  if (row.empty()) throw HttpException{404};
  auto body = to_json(row).dump();
  cache_.setex(key, 60, body);
  cb(json_response(body));
}
```
{% endraw %}

Writes hit DB only; reads use cache-aside. Skip the cache on writes; populate lazily on the rare re-read.

p. 193

> Write-around in idiomatic C++. The key discipline: don't touch the cache on writes for events/logs/telemetry data — you'd just be polluting the cache with values that will never be re-read. The optional defensive variant invalidates any stale entry, useful if siblings might have read the data before this write.

## [220] APPENDIX L · WRITE-BACK · Write-back (write-behind) — fast writes, eventual durability (sldId 475)

Writes return immediately after touching the cache; a background flusher persists to the DB asynchronously.

p. 194

> Write-back is the high-throughput pattern: write to cache, return immediately, flush to DB asynchronously in batches. Used for write-heavy workloads where some delay before DB durability is acceptable (metrics, counters, session state). Critical risks: cache outage = data loss. Configure Redis persistence (AOF) and monitor flush success rates. Graceful shutdown (Appendix H) matters more here than anywhere: pod restart must drain the dirty set before exit.

## [221] APPENDIX L · WRITE-BACK · Write-back with a background flusher (sldId 476)

[chip] c++ · sw/redis++ + libpq

```c++
// cache-service main.cpp (excerpt), examples/25-caching/cpp: write-back
app().registerHandler("/write-back/metrics/{id}",   // cache_val {id, payload}; body {ok, ...}
    [](const HttpRequestPtr& req, Callback&& callback, const std::string& id) {
      redis_set("metric:" + id, writer.write(cache_val), std::chrono::hours(1));  // 1. cache
      redis_sadd("writeback:dirty", "metric:" + id);  // 2. mark dirty
      auto resp = HttpResponse::newHttpJsonResponse(body);  resp->setStatusCode(k202Accepted);
      callback(resp);                                 // 3. 202: queued, not yet durable
    }, {Put});
void writeback_flusher() {                          // std::thread, joined at shutdown
  std::map<std::string, int> attempts;  int failures = 0;   // per-key failure count
  while (!g_shutdown) {   // ... each cycle first sleeps std::min(2 << failures, 8) s
    for (const auto& key : redis_smembers("writeback:dirty")) {  // key -> id, cached payload
      auto res = g_flush_db->exec("INSERT INTO metrics (id, payload) VALUES ($1, $2) "
          "ON CONFLICT (id) DO UPDATE SET payload = EXCLUDED.payload, ts = NOW()",
          {id, payload});
      if (res && PQresultStatus(res.get()) == PGRES_COMMAND_OK) {
        redis_srem("writeback:dirty", key);  attempts.erase(key);  continue;  // DB has it
      }                                             // failed: stays dirty, retried next cycle
      if (++attempts[key] >= kMaxFlushAttempts)     // bounded: park after 5 attempts
        { redis_sadd("writeback:failed", key);  redis_srem("writeback:dirty", key); }
    }   // ... failures + 1 (at most 2) after a cycle with a failure, 0 after a clean one
  }
```

PUT answers 202; the flusher upserts every 2 s, clears a mark once the DB has the row, and parks a key after 5 failures.

p. 195

> Write-back from Example 25: PUT /write-back/metrics/{id} stores the payload in Redis under metric:<id> with a one-hour TTL (a queued write has to outlive a database outage), adds the key to the writeback:dirty set and answers 202 Accepted: the write is queued, not yet durable. A background std::thread wakes every two seconds, reads the dirty set, upserts each metric into Postgres with INSERT ... ON CONFLICT DO UPDATE, and removes the key from the set only after the upsert succeeds, so a failed write stays dirty and is retried on the next cycle.
>
> Retries are bounded: a per-key counter parks a key on writeback:failed after five failed attempts, with its value still in the cache and an error in the log, and the cycle time backs off to four and then eight seconds while flushes fail. The upsert makes a repeated flush harmless. The flusher has its own libpq connection, separate from the request handlers', and main() joins it after the shutdown flag is set (Appendix H). The risk is the one every write-back carries: a write that was acknowledged but not yet flushed is lost if Redis loses it, so keep write-back for data that tolerates that window, such as metrics.

## [222] APPENDIX L · REFRESH-AHEAD · Refresh-ahead — keep hot keys warm (sldId 477)

A background task refreshes hot keys before their TTL expires. Users never see a cold miss on popular items.

p. 196

> Refresh-ahead targets the small set of hot keys that serve most traffic. A background task watches their TTLs and refreshes them before expiry, so users never see a miss on the hot path. Cost: extra DB load for the hot set; eliminates user-visible misses on it.

## [223] APPENDIX L · REFRESH-AHEAD · Refresh-ahead with a Redis sorted set (sldId 478)

[chip] c++ · jthread

```c++
// Refresh-ahead: a jthread refreshes hot keys before TTL expiry.
constexpr int TTL_S = 60;
constexpr int REFRESH_BEFORE_S = 10;     // refresh window
Task<> Products::get(HttpRequestPtr req, auto cb, std::string pid) {
  auto key = "product:" + pid;
  cache_.zadd("product:hot", pid, now_seconds());  // touch
  // ... then cache-aside on key with TTL_S
}
void refresher(std::stop_token st) {
  while (!st.stop_requested()) {
    std::this_thread::sleep_for(5s);
    cache_.zremrangebyscore("product:hot", 0, now_seconds() - 300);
    std::vector<std::string> hot;
    cache_.zrange("product:hot", 0, -1, std::back_inserter(hot));
    for (auto& pid : hot) {
      auto ttl = cache_.ttl("product:" + pid);
      if (ttl > 0 && ttl < REFRESH_BEFORE_S) {     // danger zone
        auto row = pg_.fetch_one("SELECT * FROM products WHERE id=$1", pid);
        if (!row.empty())
          cache_.setex("product:" + pid, TTL_S, to_json(row).dump());
      }
    }
  }
}
```

ZADD marks keys hot at read time; the jthread refreshes hot keys whose TTL is in the danger zone. Cold misses disappear on popular items.

p. 197

> Refresh-ahead in C++ uses sw/redis++ sorted sets (ZADD with timestamp as score). The refresher jthread filters by recency (drop cold keys older than 5 minutes), checks TTL of remaining hot keys, and refreshes any in the danger zone. Effect: the hot key set stays warm; cold misses on popular items disappear. Cost: 1-N extra DB queries per refresh cycle for hot keys near expiry.

## [224] APPENDIX L · ANTI-PATTERNS · When not to cache, and what to watch for (sldId 479)

- Don't cache by default. Caching adds a consistency story, an invalidation story, and a failure-mode story. If reads are already fast, just don't add a cache.
- Don't cache rarely-read data. Caching write-once-read-never data thrashes your cache and gains nothing. Profile your read patterns first.
- Don't cache without a TTL. Unbounded caches grow until they evict at random, which is the worst way to fail. Always set an explicit TTL or maxmemory-policy on Redis (allkeys-lru typical).
- Avoid cache stampedes (thundering herd): when a hot key expires and many concurrent readers all miss at once, they all hit the DB simultaneously. Mitigate with per-key locks in the loader, refresh-ahead, or jittered TTLs.
- Watch for cache-aside + write-around without invalidation — the write goes to the DB, but a stale cached value can persist for the full TTL. Invalidate on every write, or use a shorter TTL.
- Treat the cache as a performance optimisation, never as the source of truth. A cache outage must mean slower reads, not data loss — always have a DB fallback path. Test this by stopping Redis in staging.

p. 198

> Six caching anti-patterns. The headline rule: the cache is a performance optimisation, never the source of truth. Every cache-dependent code path must work correctly when the cache is empty or unavailable — slower, but correct.

## [225] APPENDIX L · DECISIONS · Choosing the right caching pattern (sldId 480)

- Cache-aside — the default. Use when you want explicit control and reads dominate writes. The pattern everyone should know first.
- Read-through — use when the read path is repetitive across the codebase and you want to factor out the if/else. Same semantics as cache-aside; cleaner code.
- Write-through — use when zero stale-read risk after a write matters more than write latency. Read-heavy with infrequent writes is the sweet spot.
- Write-around — use when writes far outnumber re-reads. Avoids cache pollution by write-once data.
- Write-back — use only when extreme write throughput is the constraint, eventual durability is acceptable and your cache is configured for persistence.
- Refresh-ahead — use when a small set of hot keys serves most traffic and miss latency is unacceptable. Adds DB load for the hot set; eliminates user-visible misses on it.
- Most production systems use cache-aside for 95% of cases, with refresh-ahead on a small set of identified hot keys and write-through where stale-read is forbidden. Mix patterns; don't pick one as the rule.

p. 199

> Six patterns, one rule: mix them.

## [226] Failure Modes (sldId 481)

Appendix M

Six modes, the defensive toolkit, and how to layer the patterns.

> Section Appendix M divider: Failure
>
> Modes. Six modes, the defensive toolkit, and how to layer the patterns.

## [227] APPENDIX M · Distributed systems fail differently (sldId 482)

- In a single process, an operation succeeds or it throws. Across a network, a call can succeed, fail, hang forever, succeed-but-the-response-is-lost, or succeed-slowly — and you often cannot tell which.
- Partial failure is the defining trait: some dependencies are up, some down, some degraded, all at the same time. There is no global 'the system is up'.
- Failures are not independent: one slow component can exhaust a caller's resources and take down healthy services around it. Failure spreads.
- Some failures lie: a node passes its own health check while failing real traffic (gray failure). What the system believes about itself and what users experience diverge.
- The goal is not zero failures; that is impossible. The goal is to bound the blast radius and recover automatically. All management is risk management.
- This appendix: six failure modes, the defensive patterns that address them (with C++ code), Istio's mesh-level role, graceful shutdown, how to observe failures, and a mapping matrix.

p. 200

> The defining property of distributed systems: failure is not boolean. For C++ services the implications are the same as any language — bound the blast radius, recover automatically. RAII unwinding and cooperative cancellation with std::stop_token make recovery clean (cpp-statelessness Docs 02 and 05, patterncatalyst.github.io/cpp-statelessness/).

## [228] APPENDIX M · A taxonomy of failure modes (sldId 483)

Network failures, component failures, load failures — and the defensive toolkit that addresses them.

p. 201

> Six failure modes across three categories. NETWORK: partition, split-brain. COMPONENT: partial failure, gray failure. LOAD: amplification (retry storms), cascading. Each has a different shape and a different defence. The defensive toolkit (timeout, retry+backoff, circuit breaker, bulkhead, load shedding, quorum, fallback) addresses them with varying effectiveness — the failure-mode matrix maps which pattern defends which mode.

## [229] APPENDIX M · NETWORK · Network partition (sldId 484)

Nodes are alive and healthy; they cannot reach each other. CAP forces a choice: consistency or availability.

p. 202

> Partition tolerance is the P in CAP. When the network splits, each side must choose: stay available (and risk inconsistency) or stay consistent (and refuse writes). For C++ services this means: connection failures, gRPC UNAVAILABLE, Kafka rebalance, Postgres replica lag — all symptoms of the same underlying cause.

## [230] APPENDIX M · NETWORK · Split-brain (sldId 485)

A partition where both sides think they are the leader and both accept writes. State diverges; the worst partition outcome.

p. 203

> Split-brain is the worst partition outcome: two sides both believe they are authoritative and both accept writes. Reconciliation after the partition heals is impossible — there's no canonical history. The only defence is quorum (Raft, Paxos): a majority must agree before any side declares itself leader. For C++ services this is usually delegated — etcd, Zookeeper, or your datastore (CockroachDB, FoundationDB) handles consensus. Don't invent your own.

## [231] APPENDIX M · COMPONENT · Partial failure (sldId 486)

The defining trait of distributed systems: some dependencies fail while others keep working. Handle each leg.

p. 204

> Partial failure is the everyday case. Your C++ service depends on Postgres, Kafka, Redis, two downstream gRPC services. At any moment, any subset of them may be unhealthy while the rest work. Your handlers must reason about each leg independently (fail open, fail closed, degrade, retry) per dependency, not service-wide.

## [232] APPENDIX M · COMPONENT · Gray failure (sldId 487)

The insidious one: a component is degraded and is perceived differently by different observers. Liveness is green; users suffer.

p. 205

> Gray failure is the failure that lies. The /healthz endpoint returns 200; real traffic is timing out. The node passes its own check; clients are seeing 504s. Detection requires comparing self-reported health to observed traffic outcomes — Istio's outlierDetection (consecutive5xxErrors) is exactly this: eject a pod from the load balancer pool when its real responses look bad, regardless of what it says about itself.

## [233] APPENDIX M · LOAD · Amplification loops & retry storms (sldId 488)

A failure triggers retries, which add load, which cause more failures. Backoff, jitter and retry budgets break the loop.

p. 206

> Retry storm: A fails, B retries, A is now more loaded, A fails more, B retries more. The classic positive-feedback loop in distributed systems. Three controls break it: exponential backoff (each retry waits longer), jitter (spread retries randomly so they don't synchronize), retry budget (system-wide cap on retries-per-second). All three are needed; one alone isn't enough.

## [234] APPENDIX M · LOAD · Cascading failure (sldId 489)

One component's failure overloads its neighbours, which fail in turn — the domino effect up the call graph.

p. 207

> Cascading failure: A slows down, B's connection pool to A fills up, B can't serve anyone (not even non-A traffic), C calls B and times out, C's pool fills, the cascade climbs the call graph. Bulkheads (App G) prevent this: separate connection pools per dependency mean A's problems are contained to A-related calls; B keeps serving everyone else.

## [235] APPENDIX M · The defensive toolkit — patterns and what they buy (sldId 490)

- Timeout + deadline propagation — never wait forever; pass the remaining budget downstream so nobody does doomed work. Defends: partial, cascading.
- Retry with backoff + jitter — ride out transient failures without building a storm; only for idempotent calls; use a retry budget. Defends: partial, amplification (if done right).
- Circuit breaker — stop calling a failing dependency; fail fast; test for recovery. Defends: cascading, amplification, gray.
- Bulkhead (§12) — isolate resources by tenant/call/priority so one failure can't starve the rest. Defends: partial, cascading.
- Load shedding — when overloaded, reject excess early (503) rather than collapsing. Defends: amplification, cascading.
- Quorum / consensus — majority-required action; the only real answer to split-brain. Defends: partition, split-brain.
- Fallback / graceful degradation — return a useful degraded response (cache, default, queue-for-later) instead of an error. Defends: partial, gray.
- Istio mesh policies + graceful shutdown + observability: the platform layer underneath all of these patterns. C++ services lean hard on Istio for uniform timeout/retry/outlier-detection policy.

p. 208

> Eight defensive patterns. For C++, most uniform concerns (timeouts at the network, retries between services, outlier ejection, mesh bulkheads) belong in Istio. Business-aware concerns (fallback to a cached default, idempotency keys, queue-for-later) belong in the C++ service. The split keeps the binary simple.

## [236] APPENDIX M · TIMEOUTS · Timeouts + deadline propagation (sldId 491)

Every remote call needs a timeout; the remaining budget should travel downstream so nobody does doomed work.

p. 209

> Timeouts are the most fundamental resilience primitive: bound how long you'll wait. The deadline propagation discipline adds the second half: if you have 5s left in your budget, pass that as the downstream's timeout — they shouldn't spend 10s doing work you've already abandoned. For gRPC C++ this is built in: ClientContext::set_deadline propagates through the HTTP/2 header. For REST you set the header explicitly (X-Deadline-Ms) and read it downstream.

## [237] APPENDIX M · TIMEOUTS · Timeouts + deadlines in C++ (sldId 492)

[chip] c++ · Drogon

```c++
// examples/26-failure-modes/cpp/edge-service/src/main.cpp (condensed excerpts)
// Drogon's async HttpClient: the coroutine suspends while it waits; the timeout is per call.
Task<Reply> get_backend(double timeout_s, std::string deadline_ms = {}) {
    auto client = HttpClient::newHttpClient(g_backend);
    auto req = HttpRequest::newHttpRequest();
    req->setPath("/process");
    if (!deadline_ms.empty()) req->addHeader("X-Deadline-Ms", deadline_ms);  // the budget
    try {
        auto resp = co_await client->sendRequestCoro(req, timeout_s);
        Reply reply;
        reply.status = static_cast<int>(resp->getStatusCode());
        if (auto json = resp->getJsonObject()) reply.body = *json;
        co_return reply;
    } catch (const HttpException&) {
        co_return Reply{};   // status 0: timed out or unreachable
    }
}

// /with-timeout:  co_await get_backend(2.0)
// /with-deadline: int remaining = budget_ms - 50;   // edge overhead
//                 if (remaining < 50) -> "insufficient budget at edge"
//                 co_await get_backend(remaining / 1000.0, std::to_string(remaining))
```

gRPC propagates deadlines natively; for REST set the header. Always check remaining budget before starting a hop.

p. 210

> Two layers, from examples/26. Drogon's HttpClient takes a timeout on every request, and sendRequestCoro suspends the coroutine handler while it waits, so a slow backend never holds an event-loop thread. A timeout or a refused connection arrives as HttpException and is reported as no answer. The deadline endpoint passes the remaining budget both as the request timeout and in the X-Deadline-Ms header, so the backend can refuse work it cannot finish.

## [238] APPENDIX M · RETRY · Retry with exponential backoff + jitter (sldId 493)

Retry transient failures — but spread retries with exponential backoff + jitter, cap them, and only for idempotent calls.

p. 211

> Retry math: exponential backoff (100ms, 200ms, 400ms, ...) plus random jitter (each client adds 0-100ms random delay) prevents synchronized retry waves. Cap attempts (3 is typical). Only retry idempotent calls (GET, PUT with idempotency key, gRPC unary with explicit idempotency declaration). For C++ the typical recommendation is: do retries at the mesh (Istio retry policy), not in the binary. Keeps the C++ code simple; uniform policy across the fleet.

## [239] APPENDIX M · RETRY · Retry with backoff + jitter in C++ (sldId 494)

[chip] c++

```c++
// examples/26-failure-modes/cpp/edge-service/src/main.cpp (condensed excerpt)
// 3 attempts, waits from 100 ms doubling to 2 s with up to 50% jitter; a 5xx or no answer
// is retried. sleepCoro suspends the handler, so the thread serves other requests meanwhile.
app().registerHandler("/with-retry", [](HttpRequestPtr) -> Task<HttpResponsePtr> {
    thread_local std::mt19937 rng{std::random_device{}()};
    auto wait = 0.1;
    Reply reply;
    int attempt = 1;
    for (;; ++attempt) {
        reply = co_await get_backend(2.0);
        if ((reply.status != 0 && reply.status < 500) || attempt == 3) break;
        co_await sleepCoro(trantor::EventLoop::getEventLoopOfCurrentThread(),
                           wait + std::uniform_real_distribution<>(0.0, wait * 0.5)(rng));
        wait = std::min(wait * 2, 2.0);
    }
    Json::Value v;
    v["attempts"] = attempt;
    co_return json(v);
}, {Get});
```

Retry in a coroutine: exponential backoff + jitter, waits that suspend instead of block. Cap attempts; only idempotent calls; pair with a circuit breaker.

p. 212

> No maintained C++ resilience library is on ConanCenter, so the retry is a short loop in a Drogon coroutine handler. Three attempts at most; between them the wait starts at 100 ms, doubles up to 2 seconds and gets up to half again as jitter. The wait is co_await sleepCoro, which suspends the handler instead of blocking the event-loop thread. Retry only idempotent calls, and pair the retry with a circuit breaker.

## [240] APPENDIX M · CIRCUIT BREAKER · Circuit breaker — the state machine (sldId 495)

Closed → Open (fail fast) → Half-Open (test) → Closed. Stops doomed calls; gives the dependency room to recover.

p. 213

> Three-state machine: CLOSED (normal, calls flow), OPEN (failing fast, no calls), HALF-OPEN (testing recovery with a few trial calls). Transitions on failure threshold (e.g. 5 consecutive failures) and reset timeout (e.g. 30s). C++ has no widely adopted circuit-breaker library; Example 26 hand-rolls one (CircuitBreaker in edge-service). The typical production answer for C++ services is to let Istio handle circuit breaking via outlierDetection — uniform, mesh-level, no in-process code.

## [241] APPENDIX M · CIRCUIT BREAKER · Circuit breaker + fallback (sldId 496)

[chip] c++ · mutex

```c++
// examples/26-failure-modes/cpp/edge-service/src/main.cpp (excerpt)
class CircuitBreaker {   // kThreshold = 5, kTrialSuccesses = 2, kResetTimeout = 10s
public:
    bool allow() {
        std::lock_guard lock(mtx_);
        if (state_ == "open" && Clock::now() - opened_at_ >= kResetTimeout) {
            state_ = "half-open";
            successes_ = 0;
        }
        return state_ != "open";
    }
    // record_success(): resets the failure count; 2 successes in half-open close it
    void record_failure() {
        std::lock_guard lock(mtx_);
        if (state_ == "half-open" || ++failures_ >= kThreshold) {   // or a failed trial
            state_ = "open";
            opened_at_ = Clock::now();
            failures_ = 0;
        }
    }
};
```

Mutex-guarded state machine; per-dependency, never one global breaker; falls back to a useful response when open.

p. 214

> The breaker from examples/26, written in the service because no maintained C++ resilience library is on ConanCenter. One mutex guards three states: five consecutive failures open it, the first call after ten seconds moves it to half-open, two successful trials close it and one failed trial opens it again. The handler asks allow() before calling the backend and records the outcome afterwards; when allow() refuses, it answers from the fallback with circuit_open.

## [242] APPENDIX M · BULKHEAD · Bulkhead — isolate so one failure can't sink the rest (sldId 497)

- Covered in depth in section 12 (Security) as a blast-radius pattern; it is equally a resilience pattern, so it appears here in the failure-mode context.
- Isolate resources (connection pools, thread pools, std::counting_semaphore, queues) by tenant, by call type, or by priority. A storm in one pool exhausts only that pool.
- Against cascading failure: if database calls have their own bounded pool, a slow database exhausts that pool and returns errors for DB-backed calls — but the service's other endpoints keep serving from their own pools.
- Against partial failure: a single misbehaving tenant or dependency is contained to its own compartment instead of consuming the shared resource.
- C++ implementation: std::counting_semaphore<MAX> for in-process concurrency limits, separate cpp-httplib Client instances or gRPC channels per dependency for connection pools. At the mesh: Istio DestinationRule connectionPool gives the same isolation at the network layer.
- Pair with timeouts: a bulkhead bounds how many calls run concurrently, but without a timeout those calls can still block forever and keep the bulkhead full. The two patterns need each other.

p. 215

> Bulkhead = isolation. The C++ specifics: std::counting_semaphore (since C++20) is the in-process primitive for bounded concurrency; per-dependency gRPC channels and cpp-httplib Clients give per-dependency connection pools. The mesh-level version (Istio DestinationRule connectionPool) gives network-layer isolation.

## [243] APPENDIX M · SHEDDING & FALLBACK · Load shedding and graceful degradation (sldId 498)

- Load shedding — when you are over capacity, reject excess work immediately (HTTP 503 + Retry-After) at the edge, before it consumes resources. A system that sheds 20% of load stays up for the other 80%; a system that accepts everything collapses for 100%.
- Shed by priority: drop health-check-style or low-value traffic first, protect revenue-critical paths. Adaptive concurrency limits (e.g. Netflix's, or Envoy's) shed automatically based on observed latency.
- Graceful degradation — when a dependency is unavailable, return a useful reduced response instead of an error: serve stale cache, omit the personalised section, queue the write for later, show a default recommendation.
- Degradation turns a hard failure into a soft one the user may barely notice. A product page that can't reach the reviews service should still show the product — just without reviews.
- Both are the application-level complement to the circuit breaker: the breaker decides to stop calling; the fallback decides what to return instead; load shedding decides what not to accept in the first place.
- Reference §11: you cannot shed or degrade intelligently without observability — you shed based on measured saturation, and you alert when degradation rates climb.

p. 216

> Load shedding + graceful degradation: the application-level pair. For C++ services, Drogon middleware can implement adaptive concurrency limits (count in-flight requests, shed when the count passes a threshold). Envoy's adaptive_concurrency filter at the sidecar does the same uniformly across the fleet.

## [244] APPENDIX M · ISTIO · Istio — resilience at the mesh layer (sldId 499)

Timeouts, retries, outlier detection (gray-failure ejection) and circuit breaking — uniform, config-driven, no app code.

p. 217

> Istio's traffic-management CRDs cover most of the toolkit declaratively: timeouts on VirtualService routes, retries with backoff and budget, outlierDetection (per-pod ejection on consecutive 5xx — addresses gray failure), connectionPool limits (bulkhead at the network layer). For a C++ shop the win is: write the binary to handle its own business logic; let Istio handle the uniform resilience concerns. The C++ code stays clean of retry loops, circuit-breaker state machines, and connection-pool tuning.

## [245] APPENDIX M · SHUTDOWN · Graceful shutdown (see App. H) (sldId 500)

[chip] c++23 · Drogon

```c++23
// Recap of Appendix H in the failure-mode context: shutdown is a failure mode.
// A pod that dies mid-request causes 5xx; a pod that drains cleanly does not.
std::atomic<bool> g_shutting_down{false};         // /readyz answers 503 once it is set
std::atomic<int>  g_in_flight{0};                 // InFlightGuard per request
extern "C" void sigterm_handler(int) {            // async-signal-safe: one atomic store
  g_shutting_down.store(true, std::memory_order_release);
}
void shutdown_watcher() {                         // one SIGTERM drives the rest
  // ... wait for the flag, sleep DRAIN_DELAY_SECONDS (5), wait for g_in_flight == 0 (20 s)
  app().quit();                                   // stop the listeners: run() returns
}
int main() {
  app().registerBeginningAdvice([] { std::signal(SIGTERM, sigterm_handler); });
  std::thread watcher(shutdown_watcher);
  app().addListener("0.0.0.0", 8080).run();
  watcher.join();
  g_pool.reset();                                 // close the pool, then exit 0
}
// K8s pod spec: terminationGracePeriodSeconds: 30 (>= 5 s delay + 20 s drain + buffer)
```

Shutdown is a failure mode: readiness flip, drain delay, bounded in-flight drain, then cleanup.

p. 218

> Recap of App H in the failure-mode context: pod shutdown is itself a failure mode that graceful drain converts into a non-failure. The C++ disposability discipline of Example 21 (one SIGTERM, an async-signal-safe flag, /readyz answering 503, the drain delay, a bounded in-flight wait, app().quit(), the pool closed and exit 0) is what makes rolling deploys clean.

## [246] APPENDIX M · OBSERVE · Observing failure modes (see §11) (sldId 501)

- Network partition — watch peer-connectivity and cross-zone error metrics; alert on quorum-loss events from etcd / your datastore.
- Split-brain — alert on more-than-one-leader conditions, divergent-replica metrics, and fencing-token rejections in logs.
- Partial failure — RED metrics per dependency (rate, errors, duration), not just per service. A spike in errors to one downstream is the early signal.
- Gray failure — the hard one: compare health-check status against real-traffic SLOs. Latency percentiles (p99) diverging from the average, and Istio outlier-ejection counts, are your tells.
- Amplification — watch request-rate against user-action-rate (if requests >> actions, retries are multiplying), retry-count metrics, and goodput falling while load rises.
- Cascading — a distributed trace shows the error spreading service-to-service; saturation metrics (thread pools, queue depth, connection pools) climb together across services.
- The unifying tool is the trace_id from §11: when an alert fires, pivot from the metric to an exemplar trace to its logs to find which leg failed first and how it spread.

p. 219

> How to see the failure modes — observation discipline per category. The C++ specifics are the OpenTelemetry C++ SDK plus spdlog with trace_id MDC; pivoting from metric to trace to log requires consistent trace_id propagation across hops, which Istio handles via the traceparent header.

## [247] APPENDIX M · Which pattern addresses which failure mode (sldId 502)

Read a row to defend a failure mode; read a column to see what a pattern buys you. Production layers several.

p. 220

> The matrix. No single pattern defends against every failure mode; production systems layer several. The combination most C++ shops settle on: Istio for timeouts / retries / outlier detection / mesh bulkheads + in-process std::counting_semaphore for in-app concurrency caps + application-level fallbacks (cached defaults, queue-for-later) + etcd/Raft for consensus. The C++ binary stays focused on business logic; the platform carries the uniform resilience concerns.

## [248] APPENDIX M · Take-aways and references (sldId 503)

- Design for partial failure from the start: every remote call can succeed, fail, hang, or lie. Timeout everything; the default is often infinite.
- Retry only idempotent calls, with backoff + jitter + a budget, at one layer, always paired with a circuit breaker. Naive retries cause the outages they were meant to prevent.
- Bound the blast radius: bulkheads isolate, circuit breakers stop the bleeding, load shedding protects capacity, fallbacks keep the user served.
- Quorum is the only cure for split-brain. Let etcd / Raft / your datastore handle consensus; don't invent your own.
- Push uniform concerns (timeouts, outlier detection, mesh bulkheads) to Istio; keep business-aware concerns (fallbacks, idempotency) in the app. Don't double-retry.
- Observe from the client's vantage point (RED per dependency, SLOs, outlier ejections) — gray failures are invisible to naive health checks. Drain on shutdown (App. H).
- References: Google SRE Book (chapters on Addressing Cascading Failures, Handling Overload); 'Release It!' (Nygard — circuit breaker, bulkhead origin); the gRPC retry design, gRFC A6 (retry policy, backoff with jitter, retry throttling); Istio traffic-management docs; the metastable-failures research (Bronson et al., 2021).

p. 221

> Final take-aways for App M and for the deck overall. The headline: failure is the default; resilience is what you design for. For C++ services in a cloud-native system, the discipline is: cooperate with the platform (Istio for uniform concerns, RAII for resource lifetime, std::stop_token for cooperative shutdown), keep business logic clean (typed exceptions, idempotency keys, fallbacks), observe from the client's vantage (RED per dependency, exemplar traces). The language gives you the tools; the discipline puts them to work.

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

[chip] c++ · flagd gRPC

```c++
// flag-service (excerpt): flagd's gRPC ResolveBoolean, called with grpc++
bool FlagdClient::evaluateBoolean(const std::string& flagKey, bool defaultValue,
                                  const std::string& targetingKey,
                                  const std::string& plan) {
  flagd::evaluation::v1::ResolveBooleanRequest request;
  request.set_flag_key(flagKey);
  auto* fields = request.mutable_context()->mutable_fields();
  (*fields)["targetingKey"].set_string_value(targetingKey);   // sticky bucketing
  if (!plan.empty()) (*fields)["plan"].set_string_value(plan);
  flagd::evaluation::v1::ResolveBooleanResponse response;
  grpc::ClientContext ctx;
  ctx.set_deadline(std::chrono::system_clock::now() + std::chrono::milliseconds(800));
  auto status = grpc::internal::BlockingUnaryCall(
      channel_.get(), method_, &ctx, request, &response);
  return status.ok() ? response.value() : defaultValue;      // flagd down: default
}
// POST /checkout
bool useNew = flagdClient->evaluateBoolean("new-checkout", false, user, plan);
```

The same one line of code serves an on/off, a per-plan entitlement, or a 25% rollout.

> The C++ example evaluates flags through flagd's gRPC evaluation API, ResolveBoolean, with a small hand-written grpc++ stub: flagd's proto service is named Service, which collides with grpc::Service in generated C++. The request carries the flag key and an evaluation context: the targeting key, which makes a percentage rollout sticky, and attributes such as plan. A deadline bounds the call, and any failure returns the default, so a flagd outage leaves the new path dark instead of failing the request.
>
> In the other languages the shape is the same through the OpenFeature SDK: register a flagd provider, build an evaluation context with a targeting key and attributes, and ask for a boolean with a safe default. The targeting rules live in flagd's configuration, not in the code, so the one call serves an on/off flag, a per-plan entitlement or a 25 percent rollout.

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

[chip] c++ · flagd

```c++
// ops kill switch: default true (fail open), on unless an operator turns it off
bool enabled = flagdClient->evaluateBoolean("recommendations-enabled", true, user);
if (!enabled) {
  response["recommendations"] = Json::Value(Json::arrayValue);  // page still renders
  response["reason"] = "killed";
} else {
  response["recommendations"] = live_recommendations(user);  // with a circuit breaker
  response["reason"] = "live";
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

> Close on the imperatives. Decouple deploy from release: ship dark, release gradually, roll back by narrowing a flag. Distinguish the four flag types, because they want different owners, defaults, and lifecycles. Evaluate through a vendor-neutral SDK against an open-source backend, always with a safe default so a flag outage cannot take the app down. Keep targeting and rollout rules in configuration, not code, and make percentage rollouts sticky. Treat release flags as debt with a removal ticket attached, and put the resolved variant on your telemetry so you can attribute a regression to a cohort. The canonical references are the OpenFeature specification and the flagd documentation, Pete Hodgson's Feature Toggles article for the taxonomy of flag types, and the Accelerate and DORA research for the deploy-versus-release distinction; Unleash (AGPL-3.0) is an open-source alternative backend; OpenFeature's C++ contrib ships only a flagd provider, so a C++ service would call Unleash through its own API.

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

[chip] bash · C++

```bash
# C++ / Drogon — build and run, then the same collection
cmake --build build && ./build/order-service &   # http://localhost:8080
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
# k8s/overlays/cpp/kustomization.yaml (excerpt)
images:
  - name: order-service
    newName: localhost/cndp-05/cpp-order-service
    newTag: v1
  # shipping-consumer and notification-consumer map the same way
# appended to each Deployment's environment by a JSON patch
- name: PG_CONNINFO
  value: "postgresql://$(PG_USER):$(PG_PASSWORD)@cndp-postgres-rw:5432/appdb"
- name: KAFKA_BOOTSTRAP
  value: "cndp-kafka-bootstrap:9092"
# memory: requests 128Mi, limits 256Mi
```

base/ is language-neutral; each overlay maps the images and appends the variables its language reads.

> The C++ overlay. The base Deployments are language-neutral: they run with a restricted security context (non-root, no privilege escalation, all capabilities dropped, RuntimeDefault seccomp, no fixed user ID), read PG_USER and PG_PASSWORD from the Secret, and point OTEL_EXPORTER_OTLP_ENDPOINT at the LGTM Service.
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
k8s/build-images.sh cpp     # docker build, then minikube image load
k8s/deploy.sh cpp           # Strimzi, Kafka, Postgres, LGTM, then the overlay
RUNTIME=kubernetes BASE=http://127.0.0.1:30080 ./verify.sh

# all six languages, a fresh namespace for each
OUT=/tmp/cndp-k8s-matrix k8s/verify-matrix.sh

# clean up: the namespace, the Strimzi release and its CRDs; then stop the profile
k8s/teardown.sh --operator
minikube stop -p cndp-k8s
```

With RUNTIME=kubernetes, verify.sh runs its container checks through kubectl exec; the ten checks are unchanged.

> The run, from the example directory. setup-profile.sh creates the profile and refuses to start while another profile or a container is running. build-images.sh builds and loads the three C++ images, and deploy.sh installs Strimzi, then Kafka, Postgres and LGTM, then the overlay.
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
