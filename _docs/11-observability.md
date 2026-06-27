---
title: "Observability"
order: 11
part: "The operational platform"
description: "Traces, metrics, and logs from OpenTelemetry, correlated by one trace id across the LGTM stack — auto-instrumentation, W3C context propagation, and head- vs. tail-based sampling."
duration: 28 minutes
---

The signal plane. Once you have services, events, and a platform, the question is
what is *actually* happening in production — and the answer is three signals,
emitted by **OpenTelemetry** (vendor-neutral) and stored in an LGTM-style stack
(Loki, Grafana, Tempo, Mimir).

## Three signals, one correlated story

Each signal answers a different question:

- **Traces** — where did the time go, and which service failed, in *this one*
  request?
- **Metrics** — what are the aggregate rates, errors, and latencies over time?
- **Logs** — what exactly happened inside this component?

The power isn't any one signal; it's that they share a **trace id**, so you can
pivot from a latency spike on a metric, to the slow trace behind it, to the logs of
the exact span that stalled. One correlated story instead of three disconnected
tools.

{% include excalidraw.html
   file="11-three-signals"
   alt="One OpenTelemetry SDK and Collector instrumentation layer fans out to three stores: Traces (request across services, Tempo, viewed in Grafana), Metrics (RED/USE histograms, Prometheus to Mimir, alerts and SLOs), and Logs (structured, trace-linked, Loki, filtered by trace_id). A band notes Grafana as the single pane and Kiali as the service-mesh topology view."
   caption="Figure 11.1 — Instrument once with OpenTelemetry; three signals land in the LGTM stack, correlated by trace_id" %}

It is worth widening the lens slightly: the classic three signals now travel with two
more that matter increasingly — **baggage**, the key-value context propagated along
the whole trace, and **profiles**, continuous CPU and memory sampling per service.
OpenTelemetry is the one vendor-neutral SDK and wire format for all of them.

{% include excalidraw.html
   file="11-signals-in-depth"
   alt="Five signal columns. Traces: request flow across services, latency per span, where did time go, Tempo/Jaeger. Metrics: aggregate rates, errors, latencies (RED/USE), what's the trend, Prometheus/Mimir. Logs: discrete timestamped events, what exactly happened, Loki/ELK. Baggage: key-value context carried along the trace, tenant_id downstream, W3C Baggage. Profiles: continuous CPU/memory sampling, which function burns CPU, Pyroscope/Parca. All correlated by trace_id, span_id, and resource attributes."
   caption="Figure 11.2 — The signals in depth: each answers a different question, all correlated by trace_id" %}

What each answers differs — traces locate *where*, metrics show the *trend*, logs say
*what exactly*, baggage carries *who or which* downstream, profiles reveal *which
function* — but the power is the `trace_id` that lets you pivot from one to the next.

## Three kinds of instrumentation

Keep three things distinct, because people conflate them:

- **Manual instrumentation** — you write the spans (`start_span`,
  `set_attribute`). Needed for *business* operations the libraries can't know
  about — `reserve_stock`, `score_fraud`. Most signal per line, most effort.
- **Auto-instrumentation** — a library or agent wraps known frameworks (HTTP, gRPC,
  database drivers, Kafka) into spans with zero code change. Covers the plumbing,
  misses your domain.
- **Auto-injection** — the platform (the OpenTelemetry Operator) injects the
  auto-instrumentation agent into the pod at admission, so you don't even add the
  dependency.

In practice you let auto-instrumentation cover the plumbing and add a few manual
spans for the business operations that matter.

## Auto-instrument your service

Here is auto-instrumentation plus one custom business span, per stack. Point it at
the Collector; the framework integrations do the rest.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
# application.yml — Micrometer Tracing + OTLP exporter
management:
  tracing:
    sampling.probability: 1.0                 # 100% in dev; sample lower in prod
  otlp:
    tracing.endpoint: http://otel-collector:4317

// Spring Web, RestTemplate/WebClient, gRPC, and Spring Kafka are instrumented
// automatically. Custom business spans use the Micrometer Observation API:
@Service
public class OrderService {
    private final InventoryGrpcClient inventory;
    public OrderService(InventoryGrpcClient i) { this.inventory = i; }

    @Observed(name = "reserve_stock")          // custom span
    public ReserveReply reserve(String sku, int qty) {
        return inventory.reserveStock(sku, qty);
    }
    // trace_id flows: REST -> gRPC -> Kafka -> consumer
}
```

```java
# application.properties — add quarkus-opentelemetry; REST, gRPC and
# Reactive Messaging are instrumented automatically. Point it at the Collector:
quarkus.otel.exporter.otlp.endpoint=http://otel-collector:4317

// Only custom business spans need code — @WithSpan does it declaratively
@ApplicationScoped
public class OrderService {
    @Inject @GrpcClient("inventory") Inventory inventory;

    @WithSpan("reserve_stock")               // custom span on this method
    public ReserveReply reserve(String sku, int qty) {
        return inventory.reserveStock(req(sku, qty));
    }
    // trace_id flows: REST -> gRPC -> Kafka -> consumer
}
```

```csharp
// Program.cs — OpenTelemetry .NET replaces Windows performance counters +
// ETW + Event Log, unified in one model.
builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("order-service"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()          // every HTTP request → span
        .AddHttpClientInstrumentation()          // outbound HttpClient → span
        .AddGrpcClientInstrumentation()          // gRPC stub calls → span
        .AddEntityFrameworkCoreInstrumentation() // EF Core queries → span
        .AddSource("OrderService")               // your custom spans
        .AddOtlpExporter(o => o.Endpoint = new Uri("http://otel-collector:4317")));

// custom business span
private static readonly ActivitySource Activity = new("OrderService");
using var span = Activity.StartActivity("reserve_stock");
await inventory.ReserveStockAsync(sku, qty);
// trace_id flows: REST -> gRPC -> Kafka -> consumer
```

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.aiokafka import AIOKafkaInstrumentor
from opentelemetry import trace

FastAPIInstrumentor.instrument_app(app)      # every request becomes a span
AIOKafkaInstrumentor().instrument()          # context propagates onto the event

tracer = trace.get_tracer("order-service")

@app.post("/orders")
async def place_order(body: OrderIn):
    with tracer.start_as_current_span("reserve_stock"):   # custom span
        await inventory.ReserveStock(body.sku, body.quantity)
    # trace_id flows: REST -> gRPC -> Kafka -> consumer
```

```cpp
// otel_init.cc — initialise once in main(), before serving traffic
#include <opentelemetry/exporters/otlp/otlp_grpc_exporter_factory.h>
#include <opentelemetry/sdk/trace/batch_span_processor_factory.h>
#include <opentelemetry/sdk/trace/tracer_provider_factory.h>
namespace otel = opentelemetry;

void init_tracing() {
  auto exporter  = otel::exporter::otlp::OtlpGrpcExporterFactory::Create({});
  auto processor = otel::sdk::trace::BatchSpanProcessorFactory::Create(  // BATCH, not Simple
      std::move(exporter), {});
  otel::trace::Provider::SetTracerProvider(
      otel::sdk::trace::TracerProviderFactory::Create(std::move(processor)));
}
// No auto-instrumentation for Drogon + modern-cpp-kafka: add a request
// middleware that starts a span, and a custom span per business op.
auto tracer = otel::trace::Provider::GetTracerProvider()->GetTracer("order-service");
auto span   = tracer->StartSpan("reserve_stock");          // custom span
auto scope  = tracer->WithActiveSpan(span);
co_await inventory.ReserveStock(sku, qty);
span->End();
// trace_id flows: REST -> gRPC -> Kafka -> consumer
```

```go
// otel.go — init once in main(); otelhttp auto-instruments, add a custom span
func main() {
	shutdown := initTracer(context.Background()) // OTLP exporter + batch processor
	defer shutdown()

	mux := http.NewServeMux()
	mux.HandleFunc("POST /orders", placeOrder)
	// NewHandler turns every request into a span; context propagates onto Kafka
	_ = http.ListenAndServe(":8080", otelhttp.NewHandler(mux, "order-service"))
}

var tracer = otel.Tracer("order-service")

func placeOrder(w http.ResponseWriter, r *http.Request) {
	ctx, span := tracer.Start(r.Context(), "reserve_stock") // custom span
	defer span.End()
	inventory.ReserveStock(ctx, body.SKU, body.Quantity)
	// trace_id flows: REST -> gRPC -> Kafka -> consumer
}
```

### How the code works

Every tab does two things: turn on auto-instrumentation for the frameworks (one
line of config, or a builder chain in .NET), and add **one** manual span around the
business operation — `reserve_stock`. The plumbing spans (HTTP in, gRPC out, Kafka
publish) come for free; the domain span is the bit only you can write. The honest
exception is C++: there is no auto-instrumentation for Drogon or
`modern-cpp-kafka`, so you add a request-scoped middleware span by hand — the
chapter says so rather than pretending the agent exists.

## The other two signals, in code

Auto-instrumentation gives you trace spans for free, but the **metric** and the
**trace-correlated log** are a line you write at the business moment. Emit a counter
(or histogram) for the operation, and log through the OTel-aware logger so the active
`trace_id` is stamped onto the line — that stamp is what lets you jump from a log
straight to its trace:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// Micrometer meter + SLF4J; the OTel logback appender puts trace_id in the MDC
private final Counter ordersPlaced = Counter.builder("orders.placed")
    .tag("service", "order-service")
    .register(registry);

void recordOrder(Order o) {
    ordersPlaced.increment();                              // metric
    // trace_id is already in the MDC, so it lands on every log line
    log.info("order placed sku={} id={}", o.sku(), o.id());   // correlated log
}
```

```java
// Quarkus: Micrometer registry + the unified Log API
@Inject MeterRegistry registry;

void recordOrder(Order o) {
    registry.counter("orders.placed", "service", "order-service").increment();  // metric
    Log.infof("order placed sku=%s id=%s", o.sku(), o.id());  // trace_id auto-added
}
```

```csharp
// System.Diagnostics.Metrics meter + ILogger
private static readonly Meter Meter = new("OrderService");
private static readonly Counter<long> OrdersPlaced =
    Meter.CreateCounter<long>("orders.placed");

void RecordOrder(Order o, ILogger log)
{
    OrdersPlaced.Add(1, new KeyValuePair<string, object?>("sku", o.Sku));  // metric
    // OTel logging enriches each record with the active TraceId
    log.LogInformation("order placed {Sku} {Id}", o.Sku, o.Id);           // correlated log
}
```

```python
from opentelemetry import trace, metrics
import logging

meter = metrics.get_meter("order-service")
orders_placed = meter.create_counter("orders.placed")

def record_order(order):
    orders_placed.add(1, {"sku": order.sku})              # metric
    ctx = trace.get_current_span().get_span_context()
    logging.info("order placed", extra={                  # trace-correlated log
        "trace_id": format(ctx.trace_id, "032x"),
        "order_id": order.id,
    })
```

```cpp
{% raw %}// metric via the OTel C++ SDK; log via spdlog with the trace_id stamped on
namespace otel = opentelemetry;
auto meter   = otel::metrics::Provider::GetMeterProvider()->GetMeter("order-service");
auto counter = meter->CreateUInt64Counter("orders.placed");

void record_order(const Order& o) {
    counter->Add(1, {{"sku", o.sku}});                    // metric
    auto ctx = otel::trace::Tracer::GetCurrentSpan()->GetContext();
    char tid[32];
    ctx.trace_id().ToLowerBase16(tid);                    // 32 hex chars
    spdlog::info("order placed sku={} id={} trace_id={}", o.sku, o.id,
                 std::string_view(tid, 32));              // correlated log
}{% endraw %}
```

```go
// metric via the OTel SDK; log via log/slog with the trace_id stamped on
var (
	meter        = otel.Meter("order-service")
	ordersPlaced metric.Int64Counter
)

func init() { ordersPlaced, _ = meter.Int64Counter("orders.placed") }

func recordOrder(ctx context.Context, o Order) {
	ordersPlaced.Add(ctx, 1, metric.WithAttributes(attribute.String("sku", o.SKU))) // metric
	sc := trace.SpanContextFromContext(ctx)
	slog.InfoContext(ctx, "order placed", // trace-correlated log
		"trace_id", sc.TraceID().String(),
		"order_id", o.ID)
}
```

The metric feeds the RED/USE dashboards and SLO alerts; the log carries the
`trace_id` so Loki can filter to exactly the request you are chasing. Same operation,
three correlated signals from one place in the code.

## How correlation actually works

"Correlation" sounds like backend magic; it isn't. The trace context travels
**with the request, in band, at every hop** — the W3C `traceparent` header,
formatted `version-traceid-parentspanid-flags`. The `trace_id` (16 bytes) is
*constant* across every hop, and that constancy is literally what stitches the
spans into one trace.

{% include excalidraw.html
   file="11-trace-propagation"
   alt="One trace id propagates via the W3C traceparent header from the order-service REST span, through the inventory gRPC span, onto the published order.placed Kafka event, and into the notification consumer span"
   caption="Figure 11.3 — One trace id, carried in band across REST, gRPC, and Kafka" %}

So a single `order.placed` request becomes one readable waterfall across five
services — edge REST, the gRPC `ReserveStock`, the published event, the consumer —
and you can point at the time axis and see exactly which span dominated the
latency.

{% include excalidraw.html
   file="11-trace-stitch"
   alt="A trace waterfall over a time axis: a long REST POST /orders span contains a nested gRPC ReserveStock span, then a publish order.placed span, then a consume and notify span. All share one trace_id, shown as 4af9c, carried onto every span, metric exemplar, and log line."
   caption="Figure 11.4 — One trace_id stitches REST, gRPC, the published event, and the consumer into a single waterfall" %}

Context propagation also carries application context you choose, not just the trace
ids — that is **baggage**. Set a key once at the edge and it rides every downstream
hop in the W3C `baggage` header, so a value like `tenant.id` is available to every
service and can be attached to their spans and logs without threading it through each
call signature:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// OpenTelemetry Baggage rides the same context propagation as the trace
Baggage.current().toBuilder()
    .put("tenant.id", request.tenantId())
    .build()
    .makeCurrent();
// downstream REST / gRPC / Kafka calls now carry tenant.id automatically
```

```java
// Quarkus uses the same OpenTelemetry Baggage API
Baggage.current().toBuilder()
    .put("tenant.id", request.tenantId())
    .build()
    .makeCurrent();
// propagates onto every outbound REST, gRPC, and Reactive Messaging call
```

```csharp
// Baggage propagates with the Activity context across services
Baggage.SetBaggage("tenant.id", request.TenantId);
// outbound HttpClient, gRPC, and Kafka calls carry tenant.id in the baggage header
```

```python
from opentelemetry import baggage, context

# set once at the edge; it rides every downstream hop
ctx = baggage.set_baggage("tenant.id", request.tenant_id)
context.attach(ctx)
# any gRPC / Kafka call made under this context carries tenant.id
```

```cpp
// OTel C++: set baggage on the current context and attach it
namespace otel = opentelemetry;
auto ctx      = otel::context::RuntimeContext::GetCurrent();
auto with_bag = otel::baggage::SetBaggage(ctx, "tenant.id", request.tenant_id);
auto token    = otel::context::RuntimeContext::Attach(with_bag);
// downstream gRPC / Kafka calls carry tenant.id until token goes out of scope
```

```go
// set baggage once at the edge; it rides every downstream hop on the context
func withTenant(ctx context.Context, tenantID string) context.Context {
	m, _ := baggage.NewMember("tenant.id", tenantID)
	b, _ := baggage.New(m)
	return baggage.ContextWithBaggage(ctx, b)
}
// any gRPC / Kafka call made with this ctx carries tenant.id downstream
```

Use baggage sparingly — it is copied onto every span and every downstream request, so
a handful of small, high-value keys (tenant, request priority) is the right dose, not
a grab-bag.

## Sampling — head vs. tail

At scale you can't store every trace, so you sample, and the only real question is
*when* the keep/drop decision is made.

{% include excalidraw.html
   file="11-sampling"
   alt="Two rows. Head sampling: a request enters, the SDK decides now (keep 1 in N probabilistically) before the trace completes, and the Collector forwards only sampled traces to the backend — cheap and low overhead but blind to errors and latency at decision time. Tail sampling: a request enters, the SDK sends all spans with no decision, the Collector buffers the whole trace and then keeps errors, slow, and rare-route traces, forwarding a kept subset to the backend — keeps all errors and slow traces but costs buffering and CPU."
   caption="Figure 11.5 — Head sampling decides early in the SDK; tail sampling decides late in the Collector, after the whole trace is seen" %}

**Head sampling** decides at the start, in the SDK, before the trace completes —
"keep 1 in N" (probabilistic) or "keep N/second" (rate-limiting). Cheap, but
blind: it can't keep a trace *because* it errored, since it doesn't know yet. One
head policy is non-negotiable in a distributed system — **parent-based**: honour
the upstream's decision carried in the `traceparent` flags, so you don't sample at
service A and drop at B and get broken half-traces.

**Tail sampling** buffers the whole trace in the Collector and decides after it
finishes — so it can keep every error and every slow trace and sample the boring
rest. More memory and latency at the Collector, far better signal.

```yaml
# otel-collector — tail sampling: buffer the whole trace, then decide
processors:
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: keep-errors                 # always keep traces that errored
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: keep-slow                    # always keep slow traces
        type: latency
        latency: { threshold_ms: 500 }
      - name: sample-the-rest              # 10% of everything else
        type: probabilistic
        probabilistic: { sampling_percentage: 10 }
```

The shape — keep errors, keep slow, sample the rest — is the one most teams want:
you never drop the traces you'd actually investigate, and you pay full storage only
for the boring majority you sample down.

### Cross-check it yourself

Prove the correlation with the house tools — no heavy framework needed. Drive a
request through `order-service` with `curl`, grab the `trace_id`, and find that
same id on the gRPC span, the Kafka event, and the consumer span in Tempo: one id,
five services. Then push load with `hey` (HTTP) and `ghz` (gRPC) and watch the
metrics move and the tail sampler keep the slow and errored traces while dropping
the rest. Seeing one request as one waterfall is the moment observability stops
being three disconnected tools.

---
*Verification status: unverified — code transcribed and normalised from the source
decks, not yet run against a live OpenTelemetry + LGTM stack. The
`examples/11-observability/` runner moves it to verified.*
