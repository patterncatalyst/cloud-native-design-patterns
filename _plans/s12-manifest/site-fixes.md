# Site fixes found during the S12 deck review

User decision 3 (2026-10-12): where a site codetab is stale against `examples/`, the site is fixed in this PR
as a separate `docs(site)` commit; `examples/` is the authority. Each row names the doc, the codetab (or block)
and the exact fix. Where a deck slide already carries the corrected code, the row names it, so the site block
can reuse the slide's lines. Apply one doc at a time, then run `python3 scripts/validate_site.py` and
`scripts/voice-scan.sh`; C++ and Go blocks with `{{` need `{% raw %}` guards.


### `_docs/28-appendix-o-newman.md` (planner, Appendix O)

| Section | Block | Fix |
|---|---|---|
| Newman in CI | `yaml` (`.github/workflows/api-tests.yml`) | `actions/checkout@v4` → `actions/checkout@v7` and `actions/upload-artifact@v4` → `actions/upload-artifact@v7` (the repo's workflows use `checkout@v7`; `upload-artifact` v7.0.2 is the newest release, 2026-10-07). |
| Running Newman | `bash` | `--bail \                         # stop on first failure (fail fast in CI)` is not a line continuation (the backslash is followed by spaces and a comment), so `--timeout-request 5000` runs as a separate command. Replace the last two option lines with `  --timeout-request 5000 \` and `  --bail`, and put the explanation on its own comment line: `# --timeout-request: per-request ceiling (ms); --bail: stop at the first failure`. |

## Site fixes found by the shared-code review (examples/ wins)

| Doc | Block | Fix |
|---|---|---|
| `_docs/21-appendix-h-shutdown.md` | "The Kubernetes side" YAML (line ~282) and the paragraph after it (line ~293) | `livenessProbe` path `/livez` → `/healthz`; prose "a *separate* `/livez`" → "`/healthz`". Every `examples/21-graceful-shutdown/*` service exposes `/healthz` and `/readyz`; none exposes `/livez`. |
| `_docs/21-appendix-h-shutdown.md` | .NET codetab comment (line ~166) `// /healthz/ready → 503` | `// /readyz → 503` (`examples/21-graceful-shutdown/dotnet/OrderService/Program.cs` maps `/readyz`). Owned by the .NET deck review if it touches the same codetab. |
| `_docs/09-api-registry.md` | bash block "register a new version" (lines ~48-52) | `--data-binary @order-placed.avsc` sends the raw schema; the v3 create-version endpoint takes a JSON body. Use the shape from `examples/09-api-registry/verify.sh`: `-d "{\"content\": {\"content\": $(jq -Rs '.' < order-placed.avsc), \"contentType\": \"application/json\"}}"`. |
| `_docs/06-stream-processing.md` | KEDA YAML (lines ~294-307) | Same as the deck slide: `metadata: { name: payment-consumer }`, `bootstrapServers` in the kafka trigger metadata, and for the HTTPScaledObject `apiVersion: http.keda.sh/v1alpha1`, `metadata: { name: order-service }`, `hosts: [...]`, `scaleTargetRef: { name: order-service, service: order-service, port: 8080 }`. No example covers KEDA; this is an API-correctness fix (KEDA v2.21.0, http-add-on). |
| `_docs/27-appendix-n-feature-flags.md` | flagd JSON (line ~225) | Optional: add `"$schema": "https://flagd.dev/schema/v0/flags.json"` as in `examples/27-feature-flags/flags/flags.json`. |

Checked and left as they are: `_docs/02-communications.md` Istio retries (deck now uses its comment), `_docs/22-appendix-i-l7-routing.md` VirtualService, canary and east/west blocks (identical to the slides), `_docs/15-appendix-b-versioning.md` proto, `_docs/12-security.md` Gatekeeper template (the `rego:` field of a ConstraintTemplate is parsed as Rego v0 by Gatekeeper, so `violation[{"msg": msg}] { ... }` is correct there; the Rego v1 syntax in `examples/12-security/policy/signed_images.rego` is for conftest 0.71.1, a different tool).

## Site fixes found by the Python deck review (examples/ wins)

1. `_docs/01-cloud-native-principles.md`, codetab "A twelve-factor service, ready for the platform", Python block
   (first line `# pyproject.toml (Poetry) pins everything; config comes from the environment`). The Python
   examples use pip with a full `==` freeze in `requirements.txt`, not Poetry, and the readiness probe checks the
   database pool. Replace the block with (from `examples/01-cloud-native-principles/python/main.py`):

   ```python
   # main.py (excerpt); requirements.txt pins every package with ==
   from fastapi import FastAPI
   from pydantic_settings import BaseSettings

   class Settings(BaseSettings):           # config from env — factor III
       database_url: str
       kafka_bootstrap: str = ""
       service_version: str = "0.0.0"

   settings = Settings()
   app = FastAPI(title="order-service", version=settings.service_version, lifespan=lifespan)

   @app.get("/healthz")                     # liveness — the process is up
   def healthz(): return {"status": "ok"}

   @app.get("/readyz")                      # readiness — dependencies are reachable
   async def readyz():
       try:
           async with pool.acquire() as conn:
               await conn.fetchval("SELECT 1")
       except Exception:
           return {"status": "down", "checks": {"database": "unreachable"}}
       return {"status": "ready", "checks": {"database": "ok"}}
   ```

2. `_docs/01-cloud-native-principles.md` figure `01-factors-mapped` (alt text, line 88) and
   `assets/diagrams/01-factors-mapped.svg` + `.excalidraw` (`text` and `originalText`): label
   `one repo · Poetry · one image per release` → `one repo · pinned requirements · one image per release`;
   alt text `(one repo, Poetry, one image per release)` → `(one repo, pinned requirements, one image per release)`.
   (The deck image `42-twelve-factor-map-py.png`, slide 13, likely carries the same label: image-audit fork.)

Not stale (recorded for the record): the Python tabs of `_docs/26` (tenacity, purgatory) and `_docs/22`
(durable-rules) teach libraries the examples replace with hand-written code (`examples/26-failure-modes/python`,
`examples/22-l7-routing/python`); the concept is the same and the site states the library choice, so no fix.
`_docs/06` prose says "Faust" (lines 43, 193, 240, 272) and `_docs/05` line 835 "Python's Faust": optional wording
fix to "faust-streaming" for consistency with the locked stack; the code tabs already use faust-streaming.

## Site codetab fixes found by the Quarkus deck pass (examples/ win)

| Doc | Codetab | Fix |
|---|---|---|
| `_docs/01-cloud-native-principles.md` (line 107) | Quarkus | `@Inject PgPool db;` → `@Inject Pool db;` (PgPool is deprecated in the reactive SQL client), and the readiness body `return db.query("SELECT 1") != null ? up("ready") : down("ready");` (a Query object is never null) → `try { db.query("SELECT 1").executeAndAwait(); return up("ready"); } catch (Exception e) { return down("ready"); }` |
| `_docs/05-event-driven.md` (line 69, also 485, 685, 1081) | Quarkus | Every Quarkus example uses the channel `order-placed` bound to the topic `order.placed` (`mp.messaging.*.order-placed.topic=order.placed`). Change `@Channel("order.placed")` / `@Incoming("order.placed")` to `"order-placed"` and add `// channel order-placed → topic order.placed` to the first block |
| `_docs/09-api-registry.md` (line 231, "Validate before you publish") | Quarkus (and the same call in the other five tabs) | `X-Registry-DryRun: true` is the Apicurio v2 header. The v3 API (`/apis/registry/v3`, Apicurio 3.3.3) takes `dryRun=true` as a query parameter on `POST /groups/{g}/artifacts/{a}/versions` (`VersionsRequestBuilder.PostQueryParameters.dryRun` in apicurio-registry-java-sdk 3.x). Quarkus: replace `@ClientHeaderParam(name = "X-Registry-DryRun", value = "true")` with a `@QueryParam("dryRun") boolean dryRun` parameter called with `true`. Spring, .NET, Python, C++, Go: append `?dryRun=true` to the URL and drop the header. Verify against a running 3.3.3 registry before committing |
| `_docs/11-observability.md` (line 69) | Quarkus | `public ReserveReply reserve(String sku, int qty)` returns the result of the Mutiny client `Inventory.reserveStock`, which is a `Uni<ReserveReply>` → `public Uni<ReserveReply> reserve(String sku, int qty)` |
| `_docs/27-appendix-n-feature-flags.md` (line 76) | Quarkus | The example (`examples/27-feature-flags/quarkus`) uses the OpenFeature SDK 1.23.0 and the flagd provider 0.14.2 directly: `OpenFeatureSetup` registers `new FlagdProvider(FlagdOptions.builder().host(flagdHost).port(flagdPort).build())` on `StartupEvent`, config keys `flagd.host` / `flagd.port`, and the resource calls `OpenFeatureAPI.getInstance().getClient()`. Replace the `quarkus-openfeature` / `quarkus.openfeature.flagd.*` comment lines and `@Inject Client flags` with that shape (the deck slide 253 text is the reference) |

## Site codetabs stale against examples/ (Spring Boot tabs)

| Doc | Codetab | Fix |
|---|---|---|
| `_docs/02-communications.md` | "gRPC for internal calls", Spring Boot (line ~250) | Replace the `@GrpcService` / grpc-spring-boot-starter server with the example's plain grpc-java server (`examples/02-communications/spring-boot/inventory-service/.../InventoryServiceApplication.java`): `@SpringBootApplication public class InventoryServiceApplication extends InventoryGrpc.InventoryImplBase implements CommandLineRunner`, `run()` starts `ServerBuilder.forPort(grpcPort).addService(this).build().start()` and awaits termination; `reserveStock` unchanged in shape. Use the deck lines of slide 18 (sldId 273) from the second comment line down. |
| `_docs/14-appendix-a-protocols.md` | "How an RPC travels", Spring Boot (line ~80) | `// grpc-spring-boot-starter injects a generated blocking stub` + `@GrpcClient("inventory") private InventoryGrpc.InventoryBlockingStub inventory;` → the example's bean: `@Bean InventoryGrpc.InventoryBlockingStub inventoryStub()` returning `InventoryGrpc.newBlockingStub(ManagedChannelBuilder.forAddress(host, port).usePlaintext().build())` (`examples/02-communications/spring-boot/order-service/.../OrderServiceApplication.java`), injected by constructor. |
| `_docs/14-appendix-a-protocols.md` | "Streaming and bidirectional communication", Spring Boot (line ~180) | Drop `@GrpcService` (grpc-spring-boot-starter); the class extends `OrderEventsGrpc.OrderEventsImplBase` and is registered with `ServerBuilder.forPort(...).addService(...)` as in the 02 example. |
| `_docs/04-data.md` | "The code, in your language", Spring Boot (line ~136) | Spring Data JPA (`OrderRepository`/`OutboxRepository`) → `JdbcClient` and Jackson 3 `JsonMapper` as in `examples/04-data/spring-boot/order-service/.../OrderController.java`; use the deck lines of slide 32 (sldId 287). |
| `_docs/06-stream-processing.md` | "A windowed aggregation", Spring Boot (line ~46) | `KStream<String, Order>`, `Duration.ofMinutes(5)`, `Double` totals → the example topology (`examples/06-stream-processing/spring-boot/stream-processor/.../RevenueTopology.java`): String serdes, `map(parse)` re-key by merchant_id, `groupByKey(Grouped.with(...))`, `TimeWindows.ofSizeWithNoGrace(Duration.ofSeconds(windowSeconds))`, `Acc(count, BigDecimal)` with `JacksonJsonSerde<Acc>` (Spring Kafka 4, Jackson 3), sink `revenue.by-merchant`. Use the deck lines of slide 43 (sldId 298). |
| `_docs/27-appendix-n-feature-flags.md` | "Evaluating a flag", Spring Boot (line ~77) | `// build.gradle: dev.openfeature:sdk, ...` → `// pom.xml: dev.openfeature:sdk, dev.openfeature.contrib.providers:flagd` (the example builds with Maven). |

## Site codetab fixes found by the .NET deck pass (examples/ wins)

| Doc | Codetab (.NET block, section) | Stale against | Fix |
|---|---|---|---|
| `_docs/02-communications.md` | "REST at the edge" | ASP.NET Core 10 / C# rules | Drop `.WithOpenApi()` (obsolete in ASP.NET Core 10, ASPDEPR002; Microsoft.AspNetCore.OpenApi documents endpoints without it). Move `public record OrderIn(...)` after the top-level statements (a type declared between top-level statements is error CS8803). |
| `_docs/05-event-driven.md` | "Producing and consuming" | `examples/05-event-driven/dotnet/OrderService/Program.cs` | The comment on `await producer.ProduceAsync(...)` says "fire-and-forget ack"; `ProduceAsync` awaits the delivery report. Change to `// awaits the broker ack`. |
| `_docs/06-stream-processing.md` | "A windowed aggregation" | `examples/06-stream-processing/dotnet/StreamProcessor/Program.cs` | The example uses `ApplicationId = "stream-processor"` (verify.sh checks that consumer group), `Stream<string, string>` + `Map(Rekey)` + `GroupByKey()`, a `WINDOW_SECONDS` window (10 s), a decimal `Acc` aggregate in `RocksDbWindows.As<string, Acc>("revenue-store")` with `JsonSerDes<Acc>`, and JSON output with half-up revenue to `revenue.by-merchant`. The codetab has `revenue-aggregator`, a typed `Order` stream grouped by `MerchantId`, a 5-minute window and a double sum. Align the ApplicationId, window and aggregate type with the example (the deck slide is now an excerpt of the example). |
| `_docs/11-observability.md` | "Auto-instrument your service" | `examples/11-observability/dotnet/OrderService/Program.cs`, `compose.yaml` | The example calls `.AddOtlpExporter()` with no endpoint (compose sets `OTEL_EXPORTER_OTLP_ENDPOINT=http://lgtm:4318`, `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`), registers `AddSource("order-service")`, and names the span `reserve-stock`. The codetab exports to `http://otel-collector:4317` and adds HttpClient, gRPC client and EF Core instrumentation packages the example does not reference. Use the example's exporter configuration and source name; keep the extra instrumentations as a comment if wanted. |
| `_docs/16-appendix-c-websockets.md` | "A WebSocket endpoint — and the problem hiding in it" | `examples/16-websockets/dotnet/WsServer/Program.cs` | The example maps `/ws/{clientId}`; the codetab uses `{userId}`. `clients.Remove(userId, out _)` on a `ConcurrentDictionary` should be `TryRemove`. |
| `_docs/18-appendix-e-errors.md` | "REST — status is the category, the body is the specifics" | ASP.NET Core behaviour | `WriteAsJsonAsync(problem, ct)` sets `Content-Type: application/json` and overwrites the `application/problem+json` set on the line before. Pass the media type: `await ctx.Response.WriteAsJsonAsync(problem, (JsonSerializerOptions?)null, "application/problem+json", ct);` (or write through `IProblemDetailsService`). |
| `_docs/22-appendix-i-l7-routing.md` | "Routing inside the app by business rules" (both .NET blocks) | `examples/22-l7-routing/dotnet/RouterService/Program.cs` | Note only: the example keeps its rules in a runtime-editable dictionary (`GET/PUT /rules`, VIP threshold, priority and default topics) and uses no NRules. The NRules codetabs are a valid illustration; add one sentence saying the runnable example uses a rule table, or leave as is. |

## Site codetab fixes found by the Go deck pass (examples/ wins)

| Doc | Codetab (Go block) | Stale against | Fix |
|---|---|---|---|
| `_docs/05-event-driven.md` | "Producing and consuming" | `examples/05-event-driven/go/notification-consumer/cmd/consumer/main.go` | `kgo.ConsumerGroup("notification")` → `kgo.ConsumerGroup("notification-group")` |
| `_docs/11-observability.md` | "Auto-instrument your service" | `examples/11-observability/go/order-service/cmd/server/main.go` (`tracer.Start(ctx, "reserve-stock")`) | span name `"reserve_stock"` → `"reserve-stock"` |
| `_docs/19-appendix-f-ddd-hexagonal.md` | "Hexagonal architecture — protocols are adapters" | `examples/19-ddd-hexagonal/go/order-service/domain/{ports.go,service.go}` | ports: `Save(ctx context.Context, order *Order) error` (plus `FindByID`, `FindAll`), `EventPublisher` is `Publish(event OrderPlaced)` (no ctx, no error); use case is `type PlaceOrder struct { repo OrderRepository; pub EventPublisher }` with `func (s *PlaceOrder) Execute(ctx, cmd PlaceOrderCmd) (*Order, error)` that validates, saves, then `s.pub.Publish(OrderPlaced{OrderID: ..., SKU: ..., Quantity: ...})`; the REST adapter calls `Execute`, not `Do` |
| `_docs/26-appendix-m-failure-modes.md` | "Circuit breaker" | `examples/26-failure-modes/go/edge-service/cmd/server/main.go` (gobreaker v2.4.0) | v1 API does not compile against v2: import `github.com/sony/gobreaker/v2`; `gobreaker.NewCircuitBreaker[Result](gobreaker.Settings{...})`; `paymentBreaker.Execute(func() (Result, error) {...})` returns `(Result, error)` (drop `v.(Result)`); treat `gobreaker.ErrOpenState` and `gobreaker.ErrTooManyRequests` as the fallback triggers |
| `_docs/27-appendix-n-feature-flags.md` | "Evaluating a flag: OpenFeature and flagd" | `examples/27-feature-flags/go/flag-service/cmd/server/main.go` (flagd provider 0.7.1) | `openfeature.SetProviderAndWait(flagd.NewProvider(...))` does not compile: `flagd.NewProvider` returns `(provider, error)`. Write `provider, err := flagd.NewProvider(flagd.WithHost("flagd"), flagd.WithPort(8013))`, check `err`, then `openfeature.SetProviderAndWait(provider)` (the example uses `SetProvider`) |
| `_docs/01-cloud-native-principles.md` | "A twelve-factor service, ready for the platform" | `examples/01-cloud-native-principles/go/cmd/server/main.go` (`os.Getenv("SERVICE_VERSION")`) | the hard-coded `"1.4.0"` in the `slog.Info` line → `os.Getenv("SERVICE_VERSION")` (config from the environment, factor III) |

Valet key (user decision 6, 2026-10-12): `_docs/12-security.md`, codetab "The valet key hands out direct access",
Go block (line ~274, first line `// valet_key.go — mint a scoped, time-bound upload ticket`). The block uses
`aws-sdk-go-v2` (`s3.PresignClient`), a managed-cloud SDK that no Go example uses; `examples/12-security/go/cmd/server/main.go`
mints the valet key as an HS256 JWT with golang-jwt v5.3.1. Replace the whole Go block with (Go deck slide 78,
sldId 333, carries a condensed version of the same code; tabs as in the example; no `{{`, so no raw guard):

```go
// main.go (excerpt), examples/12-security/go — the valet key is an HS256 JWT (golang-jwt v5)
type valetClaims struct {
	Resource  string `json:"res"`
	Operation string `json:"op"`
	jwt.RegisteredClaims
}

func mintValet(resource, operation string) map[string]any {
	expires := time.Now().Add(5 * time.Minute) // time-bound
	token, err := jwt.NewWithClaims(jwt.SigningMethodHS256, valetClaims{
		Resource:  resource,  // scoped: this one object
		Operation: operation, // operation-restricted: GET or PUT, not both
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(expires),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			Issuer:    "order-service",
		},
	}).SignedString([]byte(valetSecret))
	if err != nil {
		slog.Error("sign valet key", "err", err)
	}
	return map[string]any{"resource": resource, "operation": operation,
		"expires": expires.Unix(), "token": token}
}
// the verifier accepts HS256 only, requires exp, checks the issuer, then matches res, op and exp
```

The claim-check Go block and the sentence after the valet-key codetabs are superseded by the decision-7
section (end of this file).

## Site fixes found by the C++ deck pass

C++ codetabs (`langs="Spring Boot|Quarkus|.NET|Python|C++|Go"`, fifth block) that disagree with
`examples/*/cpp/`. The deck slide named in each row already carries the corrected code (see
`lgtm-presentation/edits/Designing-Cloud-Native-APIs-Cpp.json`); the site fix can reuse it.

| Doc (line of the C++ block) | Codetab | Stale | Fix (examples win) |
|---|---|---|---|
| `_docs/04-data.md` (~221) | The code, in your language | `PgTxn` coroutine wrapper, `insert_outbox_sql` | `examples/04-data/cpp/order-service/src/main.cpp` uses libpq directly: `PQexec(conn, "BEGIN")`, `PQexecParams` into `orders (id, sku, quantity, status)` and `outbox (aggregate_id, event_type, payload)` with `$3::jsonb`, `COMMIT`, `ROLLBACK` + 500 on any error. Use the deck slide 32 (sldId 287) excerpt. |
| `_docs/06-stream-processing.md` (~143) | A windowed aggregation | `consumer.poll(100ms)`, `msg.value()` (modern-cpp-kafka API), `emit_window` to `revenue.by-merchant`, 5-minute window | `examples/06-stream-processing/cpp/stream-processor/src/main.cpp`: rdkafka++ `consume(200)`, `cndp::MerchantWindows::apply()`, `send("revenue.by-merchant", ..., cndp::revenue_json(...))`, `commit_batch()` flushes the producer before `commitSync()`; window length is `WINDOW_SECONDS` (default 10 s). Use the deck slide 43 (sldId 298) excerpt. |
| `_docs/11-observability.md` (~149) | Auto-instrument your service | `OtlpGrpcExporterFactory`, `otlp_grpc_exporter_factory.h` | The examples export OTLP/HTTP (`examples/11-observability/cpp/*/src/telemetry.hpp`: `OtlpHttpExporterFactory`, `otlp_http_exporter_factory.h`, endpoint `http://lgtm:4318`). Replace both tokens. |
| `_docs/12-security.md` (~569) | Claim-check: send a reference, not the payload | `producer.produce("order.documents", claim.dump())`, `consumer.poll(100ms)`, `msg.value()` | Locked stack is librdkafka's C++ API: `producer->produce(topic, RdKafka::Topic::PARTITION_UA, RdKafka::Producer::RK_MSG_COPY, claim.data(), claim.size(), key.data(), key.size(), 0, nullptr)` and `std::unique_ptr<RdKafka::Message> msg(consumer->consume(100))` with `payload_of(*msg)`, `commitSync(msg.get())` after the fetch (deck slide 87, sldId 342). No claim-check example exists.  Superseded by the decision-7 claim-check block (rdkafka++ plus the jwt-cpp ticket). |
| `_docs/12-security.md` (~255) | The valet key hands out direct access | AWS SDK presigned URL | **Required** (decision 7): replace the block with the jwt-cpp excerpt of `examples/12-security/cpp/order-service/src/valet.hpp` given in the decision-7 section. |
| `_docs/17-appendix-d-sagas.md` (~232) | Compensation unwinds a failed saga | `"comp_stock"_s + event<StockReleased>` table, `reversed(s.completed_steps())`, `inverse_of(step)` | `examples/17-sagas/cpp/saga-orchestrator/src/{saga_machine.hpp,main.cpp}`: a `Lifecycle` machine (RUNNING → COMPENSATING → COMPENSATED on `StepFailed` / `Compensated`) and `for (int i : cndp::saga::compensation_order(progress.step_index))` calling `step.compensate(context)` with `logStep(..., step.compensationName, "compensate", ...)`. Use the deck slide 124 (sldId 379) excerpt. |
| `_docs/19-appendix-f-ddd-hexagonal.md` (~230) | Hexagonal architecture — protocols are adapters | `virtual Task<> save(...)`, `Task<> publish(const DomainEvent&)`, `class PlaceOrder` with `co_await` | `examples/19-ddd-hexagonal/cpp/order-service/src/domain/{ports.hpp,service.hpp}`: synchronous ports (`void save(const Order&)`, `std::optional<Order> find_by_id`, `void publish(const OrderPlaced&)`), use case `PlaceOrderUseCase::execute(const PlaceOrderCmd&)`. Use the deck slide 146 (sldId 401) code. |
| `_docs/21-appendix-h-shutdown.md` (~196) | The application side | `std::stop_source` / `std::jthread kafka_worker` / `request_stop()` inside the signal handler, "(C++20)" | `examples/21-graceful-shutdown/cpp/src/main.cpp`: `std::atomic<bool> g_shutting_down`, `InFlightGuard` + `g_in_flight`, `registerBeginningAdvice` re-installs the SIGTERM handler after Drogon's, `/readyz` → 503, drain loop after `run()`. Use the deck slide 164 (sldId 419) code. Also: `request_stop()` is not specified as async-signal-safe; the site prose claiming it is should be dropped. |
| `_docs/24-appendix-k-monolith-to-microservices.md` (~276) | Content-based routing during migration | `cpp_httplib::Client` (the library's namespace is `httplib`; the example does not use it) | `examples/24-monolith-to-microservices/cpp/router/src/main.cpp`: tenant route table (`g_tenant_routes["acme"] = "new-service"`), `forward_request()` with `drogon::HttpClient::newHttpClient(upstream)`, 502 on failure. Use the deck slide 206 (sldId 461) code. |
| `_docs/24-appendix-k-monolith-to-microservices.md` (~513) | The decorating collaborator | `producer_.send("order.placed", body)`; `co_await cache_.get/setex/del` | `examples/24-.../cpp/decorator/src/main.cpp` produces with an `RdKafka::Producer` and calls sw/redis++ synchronously. Use the deck slide 208 (sldId 463) code (`produce_to(*producer_, "order.placed", id, body)`, no `co_await` on `cache_`). |
| `_docs/27-appendix-n-feature-flags.md` (~168, ~313) | Evaluating a flag; The kill switch | OpenFeature C++ SDK (`getApi().setProvider(FlagdProvider{...})`, `flags->getBooleanValue`) | `examples/27-feature-flags/cpp/flag-service/src/main.cpp` calls flagd's gRPC `ResolveBoolean` with a hand-written grpc++ stub (`FlagdClient::evaluateBoolean(flagKey, default, targetingKey, plan)`, 800 ms deadline, default on failure); kill switch `evaluateBoolean("recommendations-enabled", true, user)`. Use the deck slides 253 and 256 (sldIds 508, 511). |
| `_docs/22-appendix-i-l7-routing.md` (~310, ~475) | Routing inside the app by business rules (Lua + dispatcher) | `route(order, ctx)` returning a list of `kafka:`/`http:` destinations | `examples/22-l7-routing/cpp/router-service/routing.lua` defines `route(order, rules)` returning `(topic, vip)`, evaluated in a sandboxed per-call `lua_State` with an instruction and time budget (`routing_engine.hpp`). The deck keeps the site's fan-out version (slides 188, 189); align both if the site changes. |

## Figures (from the image and policy reviews)

| File | Fix |
|---|---|
| `assets/diagrams/01-factors-mapped.svg` + `.excalidraw` (`text` and `originalText`) and its alt text in `_docs/01-cloud-native-principles.md` | Label "one repo · Poetry · one image per release" → "one repo · pinned requirements · one image per release" (the Python examples use pip with a full `==` freeze). |
| `assets/diagrams/policy-ci-pipeline.svg`, `policy-gitops-flow.svg` + their `.excalidraw` | kubeval → kubeconform (v0.8.0). Only the K8s policy deck uses these figures; the deck gets fixed PNGs from `lgtm-presentation/edits/png/src/`. |
| `_docs/23-appendix-j-dotnet-toolkit.md` | The platform table lists Redis (or Valkey) as "BSD-3 / BSD"; Redis 8 is RSALv2 / SSPLv1 / AGPLv3 (the AGPLv3 option is the one used). |
| `assets/diagrams/02-pick-protocol.svg`, `02-mesh-handles-wire.svg`, `22-business-rule-routing.svg`, `22-hop-cost.svg` | Optional: they carry Python labels (FastAPI, durable-rules) while the site is six-language; the decks now use per-language copies (`lgtm-presentation/edits/png/src/`). |
| `assets/diagrams/29-container-layers.svg` | Optional: the "COPY --from=build" label overlaps. |

## Decision 7: vendor-neutral site (no AWS, Azure, Google Cloud, ACS or OpenShift reliance)

User decision 7 (plan, 2026-10-12). Apply as part of the `docs(site)` commit. The code blocks are the same lines
as the deck slides (`tools/amend_vendor.py` holds them; Go: `tools/amend_decisions.py`), so the site and the decks
agree. Run `python3 scripts/validate_site.py` (raw guards, codetab counts) and the voice scan after applying.

### `_docs/12-security.md`, "The valet key hands out direct access"

1. Figure alt text (line ~174): `directly against the resource (S3, blob, file) using the token` →
   `directly against the resource (object store, file) using the token`.
2. Replace the six codetab blocks (Spring Boot, Quarkus, .NET, Python, C++, Go, in that order) with the blocks
   below. The Go block is the `main.go (excerpt)` block already given in the Go section of this file (golang-jwt;
   deck slide 78). None of the blocks has `{{`, so no raw guards.

```java
// ValetKeyService.java (excerpt), examples/12-security/spring-boot: HMAC-SHA256 valet key
@Service
public class ValetKeyService {
    private static final int TTL_SECONDS = 300;                       // time-bound
    private final byte[] secret;          // VALET_SECRET, injected through @Value
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
// OrderController maps POST /valet-key to mint() and GET /verify-valet to verify()
```

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

```csharp
// Program.cs (excerpt), examples/12-security/dotnet: an HMAC-SHA256 valet key
var valetSecret = Environment.GetEnvironmentVariable("VALET_SECRET")
    ?? "demo-secret-do-not-use-in-prod";
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

```python
# main.py (excerpt), examples/12-security/python: an HMAC-SHA256 valet key
VALET_SECRET = os.environ.get("VALET_SECRET", "demo-secret-do-not-use-in-prod")

def _mint_valet(resource: str, operation: str, ttl: int = 300) -> dict:
    expires = int(time.time()) + ttl                        # time-bound
    payload = f"{resource}:{operation}:{expires}"           # one object, one operation
    sig = hmac.new(VALET_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return {"resource": resource, "operation": operation, "expires": expires, "token": sig}

def _verify_valet(resource: str, operation: str, expires: int, token: str) -> bool:
    if time.time() > expires:
        return False                                        # expired: worthless
    payload = f"{resource}:{operation}:{expires}"
    expected = hmac.new(
        VALET_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(token, expected)             # constant-time compare

@app.post("/valet-key")
async def mint_key(resource: str, operation: str = "GET"):
    return _mint_valet(resource, operation)
# GET /verify-valet answers 403 for an expired or tampered key
```

```cpp
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

3. Line ~290: `The same shape covers Azure SAS tokens, GCS signed URLs, and AWS STS scoped roles.` →
   `Example 12 mints and verifies the ticket in the service itself. Most object stores, open-source ones included,`
   `accept signed URLs of the same shape: the method, the object key and the expiry signed into the URL.`

### `_docs/12-security.md`, "Claim-check: send a reference, not the payload"

Replace the six codetab blocks with the blocks below (the producer stores the body in any encrypted object store and
publishes a claim whose ticket is Example 12's valet key; no `s3://` URI). The C++ block contains `{{` and keeps a
`{% raw %}` guard. Prose and figure are vendor-neutral already.

```java
// claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key
@Service
public class ClaimPublisher {
    private final ObjectStore store;                           // any encrypted object store
    private final KafkaTemplate<String, Map<String, Object>> kafka;
    private final ValetKeyService valet;                       // examples/12-security
    // constructor injection omitted
    public void publish(String orderId, byte[] body) {
        String key = "payloads/" + orderId;
        store.put(key, body, true);                            // encrypted at rest, ACL'd
        Map<String, Object> claim = new LinkedHashMap<>(valet.mint(key, "GET"));
        claim.put("order_id", orderId);
        claim.put("uri", "https://objects.internal/" + key);
        kafka.send("order.documents", orderId, claim);         // only the claim on the topic
    }
}
// consumer: read the claim, fetch the body out of band
@KafkaListener(topics = "order.documents", groupId = "documents")
public void onClaim(Map<String, Object> claim) {
    byte[] body = store.get((String) claim.get("uri"), (String) claim.get("token"));
    handle(body);                                              // PII never touched the topic
}
```

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

```python
# claim-check sketch: store is any encrypted object store; the ticket: Example 12's valet key
async def publish_with_claim(producer: AIOKafkaProducer, order_id: str, body: bytes):
    key = f"payloads/{order_id}"
    await store.put(key, body, encrypt=True)                # encrypted at rest, ACL'd
    claim = {
        "order_id": order_id,
        "uri": f"https://objects.internal/{key}",
        **_mint_valet(key, "GET", ttl=900),                  # resource, op, expires, token
    }
    await producer.send_and_wait(                           # only the claim goes on the topic
        "order.documents", json.dumps(claim).encode(), key=order_id.encode())

# consumer: read the claim, fetch the body out of band
async for msg in consumer:
    claim = json.loads(msg.value)
    body = await store.get(claim["uri"], token=claim["token"])   # the store checks the ticket
    await handle(body)                                      # PII never touched the topic
    await consumer.commit()                                 # after the side effect
```

```cpp
{% raw %}
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
{% endraw %}
```

```go
// claim-check sketch: store is any encrypted object store; the token is the valet-key JWT
func publishWithClaim(ctx context.Context, cl *kgo.Client, orderID string, body []byte) error {
	key := "payloads/" + orderID
	if err := store.Put(ctx, key, body, true); err != nil { return err } // encrypted, ACL'd
	claim, _ := json.Marshal(map[string]any{
		"order_id": orderID,
		"uri":      "https://objects.internal/" + key,
		"token":    mintValet(key, "GET")["token"],          // GET only, five minutes
	})
	return cl.ProduceSync(ctx,                               // only the claim goes on the topic
		&kgo.Record{Topic: "order.documents", Key: []byte(orderID), Value: claim}).FirstErr()
}
func onClaim(ctx context.Context, r *kgo.Record) error {
	var c Claim
	if err := json.Unmarshal(r.Value, &c); err != nil { return err }
	body, err := store.Get(ctx, c.URI, c.Token)              // the store verifies the ticket
	if err != nil { return err }
	return handle(ctx, body)                                 // PII never touched the topic
}
```

### Other vendor mentions on the site

| Doc (line) | Find | Replace with |
|---|---|---|
| `_docs/29-glossary.md` (~90) | the row `\| S3 \| Simple Storage Service \| Object storage, e.g. the target of a valet-key upload \|` | delete the row (no chapter uses the acronym after the valet-key fix) |
| `_docs/26-appendix-m-failure-modes.md` (~730) | `the AWS Builders' Library (timeouts, retries, backoff with` / `jitter)` | `the gRPC retry design, gRFC A6 (retry policy, backoff with jitter, retry` / `throttling)` (github.com/grpc/proposal/blob/master/A6-client-retries.md: "Jitter of plus or minus 0.2 is applied to the backoff delay"; `retryThrottling`) |
| `_docs/22-appendix-i-l7-routing.md` (~47) | `The **API gateway** (Kong, Apigee, an Istio gateway,` | `The **API gateway** (Kong, an Istio gateway,` |
| `_docs/30-appendix-q-blazor-signalr.md` (~99-102) | the paragraph `For teams that want fully managed infrastructure, **Azure SignalR Service** offloads ... scaling equation.` | delete the paragraph (a vendor-hosted service is not a recommended option; the Redis backplane before it is the answer) |
| `_docs/16-appendix-c-websockets.md` (~519-521) | `scale-out, or **Azure SignalR Service** offloads the persistent connections entirely` / `  to a managed endpoint.` | `scale-out.` |
| `_docs/23-appendix-j-dotnet-toolkit.md` (~27) | `commercial-only dependencies, and nothing that requires Azure or any other specific` / `cloud.` | `commercial-only dependencies, and nothing that requires a specific cloud.` |
| `_docs/23-appendix-j-dotnet-toolkit.md` (~50) | `Open-source Redis backplane (not Azure SignalR Service)` | `Open-source Redis backplane (no managed SignalR service)` |
| `_docs/23-appendix-j-dotnet-toolkit.md` (~137) | `no Azure required` | `no managed cloud service required` |
| `_docs/29-appendix-p-dotnet-on-linux.md` (~207) | `when running on OpenShift or RHEL, UBI images get full` | optional: `when running on RHEL, UBI images get full` (nothing depends on it) |

Checked and left as they are: `_docs/31-appendix-r-minikube.md` (~22) and `_docs/05-event-driven.md` (~1294) only
point to Appendix S, which stays on the site; no recommendation outside Appendix S depends on an OpenShift-only feature
(Routes, SCCs, OLM, EgressFirewall, ACS). `_docs/32-appendix-s-openshift-local.md` is unchanged.

### Figures

Change the SVG `<text>`, the `.excalidraw` `text` and `originalText` of the same element, and any alt text that repeats
the label. The deck copies are rendered by `tools/vendor_figures.py` (corrected SVG text in `lgtm-presentation/edits/png/src/`).

| File | Old label | New label |
|---|---|---|
| `assets/diagrams/12-valet-key.svg` + `.excalidraw` | Resource (S3, blob, file) | Resource (object store, file) |
| `assets/diagrams/12-valet-key.svg` + `.excalidraw` | the app never proxies the bytes — no long-lived credentials at the client (S3 pre-signed URLs, Azure SAS tokens, GCS signed URLs, STS AssumeRole) | the app never proxies the bytes — no long-lived credentials at the client (Example 12: a ticket the service signs and verifies itself) |
| `assets/diagrams/advisory-tier-evaluation.svg` + `.excalidraw` | Tier 1 — AdminNetworkPolicy | Tier 1 — CNP Admin tier |
| `assets/diagrams/advisory-tier-evaluation.svg` + `.excalidraw` | Tier 3 — BANP | Tier 3 — CNP Baseline tier |
| `assets/diagrams/advisory-tier-evaluation.svg` + `.excalidraw` | ANP evaluates | Admin tier evaluates |
| `assets/diagrams/advisory-tier-evaluation.svg` + `.excalidraw` | cluster-scoped, priority 0-99 | cluster-scoped, priority 0-1000 |
| `assets/diagrams/advisory-tier-evaluation.svg` + `.excalidraw` | Allow | Accept | (2 elements)
| `assets/diagrams/advisory-tier-evaluation.svg` + `.excalidraw` | BANP evaluates | Baseline tier evaluates |
| `assets/diagrams/advisory-tier-evaluation.svg` + `.excalidraw` | cluster singleton, safety net | cluster-scoped, safety net |
| `assets/diagrams/advisory-tier-evaluation.svg` + `.excalidraw` | OVN-Kubernetes three-tier policy evaluation | ClusterNetworkPolicy three-tier evaluation |
| `assets/diagrams/advisory-tier-evaluation.svg` + `.excalidraw` | BANP catches unmatched traffic. | The Baseline tier catches unmatched traffic. |
| `assets/diagrams/advisory-tier-evaluation.svg` + `.excalidraw` | ANP Allow/Deny are final — NP and BANP are skipped. | Admin Accept/Deny skip NP and Baseline. |
| `assets/diagrams/advisory-tier-evaluation.svg` + `.excalidraw` | BANP is overridable by NetworkPolicy. | Baseline is overridable by NetworkPolicy. |
| `assets/diagrams/advisory-ci-pipeline.svg` + `.excalidraw` | oc apply --dry-run | kubeconform |
| `assets/diagrams/advisory-ci-pipeline.svg` + `.excalidraw` | ACS Build-time | Baseline Diff |
| `assets/diagrams/advisory-ci-pipeline.svg` + `.excalidraw` | baseline validation | vs observed flows |
| `assets/diagrams/advisory-ci-pipeline.svg` + `.excalidraw` | ACS + OVN-K verify | flow logs + Falco |
| `assets/diagrams/advisory-team-ownership.svg` + `.excalidraw` | EgressFirewall | Egress rules |
| `assets/diagrams/advisory-team-ownership.svg` + `.excalidraw` | ANP / BANP review | Admin / Baseline review |
| `assets/diagrams/advisory-team-ownership.svg` + `.excalidraw` | Perimeter (Palo Alto) | Perimeter firewall |
| `assets/diagrams/advisory-team-ownership.svg` + `.excalidraw` | AdminNetworkPolicy | CNP Admin tier |
| `assets/diagrams/advisory-team-ownership.svg` + `.excalidraw` | cluster guardrails, Allow/Deny/Pass | cluster guardrails, Accept/Deny/Pass |
| `assets/diagrams/advisory-team-ownership.svg` + `.excalidraw` | BANP | CNP Baseline tier |
| `assets/diagrams/advisory-team-ownership.svg` + `.excalidraw` | ACS baselines | Observed baselines |

The three `advisory-*` figures are used by the network advisory companion (`lgtm-presentation/network-policy-process-advisory.md`)
and deck only; `12-valet-key` is Figure 12.3 of `_docs/12-security.md`.

## Site fixes found by S12 fix round A (examples/ wins)

Found while fixing the decks after the Quarkus validation (colours, caps, accuracy, cross-deck). Apply in the
same `docs(site)` commit as the rows above.

| Doc | Block | Fix |
|---|---|---|
| `_docs/12-security.md` | Bulkhead codetabs, all six languages (lines ~385-472) | The per-tenant capacity is 5 in every `examples/12-security/<lang>` service (`CAPACITY = 5` in Spring Boot, Quarkus and C++, `bulkheadLimit = 5` in .NET, `BULKHEAD_LIMIT = 5` in Python, `bulkheadCapacity = 5` in Go); the site shows 20. Spring Boot: `.maxConcurrentCalls(20)              // 20 concurrent per tenant` → `.maxConcurrentCalls(5)               // 5 concurrent per tenant`; Quarkus: `new Semaphore(20));  // 20 / tenant` → `new Semaphore(5));   // 5 / tenant`; .NET: `new SemaphoreSlim(20));  // 20 / tenant` → `new SemaphoreSlim(5));   // 5 / tenant`; Python: `asyncio.Semaphore(20))   # 20 concurrent / tenant` → `asyncio.Semaphore(5))    # 5 concurrent / tenant`; C++: `try_emplace(tenant, 20);   // 20 concurrent / tenant` → `try_emplace(tenant, 5);    // 5 concurrent / tenant`; Go: `make(chan struct{}, 20)) // 20 / tenant` → `make(chan struct{}, 5))  // 5 / tenant`. Prose that repeats "20" follows. |
| `_docs/25-appendix-l-caching.md` | Write-back, Quarkus codetab (line ~875) | `@Scheduled(every = "1s") @Transactional` with `Metric.persistAll(...)` inside `try`: the insert is flushed at commit, after the method returns, so a database error never reaches the `catch` and the ids are not re-marked dirty. Flush inside the `try`: `Metric.persistAll(loadFromCache(ids)); Metric.flush();  // batch insert` (the deck's fix, Quarkus slide "Write-back with @Scheduled in Quarkus"). The other five write-back codetabs already run the write (and the commit) inside the `try` (Spring `repo.saveAll` commits in its own transaction; .NET `SaveChangesAsync`, Python `execute_many`, Go `CopyFrom`/`Exec`, C++ `txn.commit()`), as `examples/25-caching/<lang>` does. |
| `_docs/26-appendix-m-failure-modes.md` | Retry + breaker, Quarkus codetab (line ~362) | `// MicroProfile applies the breaker first, then retry within the closed state.` is wrong: SmallRye Fault Tolerance applies `@Retry` outside `@CircuitBreaker`, so every attempt goes through the breaker and an open breaker fails each retry fast. → `// Retry wraps the breaker; an open breaker fails each retry fast.` Same file: `// ALWAYS pair with a breaker` → `// always pair with a breaker`, and the .NET `// Polly v8: exponential backoff WITH jitter is built in` → `with` (ALL-CAPS emphasis, voice rule). |
| `_docs/06-stream-processing.md` | Kafka Streams, Spring Boot and Quarkus codetabs (lines ~63, ~83) | `.to("revenue.by-merchant")` writes a `Windowed<String>` key and a `Double` value with the default serdes, which fails at runtime (the default key serde is a plain String serde). Declare `var windowSerde = WindowedSerdes.timeWindowedSerdeFrom(String.class, Duration.ofMinutes(5).toMillis());` and write `.to("revenue.by-merchant", Produced.with(windowSerde, Serdes.Double()))`, as the Quarkus deck slide now does (`examples/06-stream-processing/<jvm>` maps the window to a JSON string first and uses `Produced.with(Serdes.String(), Serdes.String())`; either shape is correct). The .NET Streamiz block unwraps the window key before `.To<StringSerDes, DoubleSerDes>` and is correct. |
| `_docs/12-security.md` | Zero-trust prose | Checked: the site describes the generic zero-trust model (an IAP evaluates user, device, MFA, posture) and names neither Pomerium nor OAuth2 Proxy, so the decks' "check device posture" claim about those proxies (fixed in the decks) is not on the site. No change. |
