---
title: "Observability"
order: 11
part: "The operational platform"
description: "Traces, metrics, and logs from OpenTelemetry, correlated by one trace id across the LGTM stack — auto-instrumentation, W3C context propagation, and head- vs. tail-based sampling."
duration: 20 minutes
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

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

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

### How the code works

Every tab does two things: turn on auto-instrumentation for the frameworks (one
line of config, or a builder chain in .NET), and add **one** manual span around the
business operation — `reserve_stock`. The plumbing spans (HTTP in, gRPC out, Kafka
publish) come for free; the domain span is the bit only you can write. The honest
exception is C++: there is no auto-instrumentation for Drogon or
`modern-cpp-kafka`, so you add a request-scoped middleware span by hand — the
chapter says so rather than pretending the agent exists.

## How correlation actually works

"Correlation" sounds like backend magic; it isn't. The trace context travels
**with the request, in band, at every hop** — the W3C `traceparent` header,
formatted `version-traceid-parentspanid-flags`. The `trace_id` (16 bytes) is
*constant* across every hop, and that constancy is literally what stitches the
spans into one trace.

{% include excalidraw.html
   file="11-trace-propagation"
   alt="One trace id propagates via the W3C traceparent header from the order-service REST span, through the inventory gRPC span, onto the published order.placed Kafka event, and into the notification consumer span"
   caption="Figure 11.1 — One trace id, carried in band across REST, gRPC, and Kafka" %}

So a single `order.placed` request becomes one readable waterfall across five
services — edge REST, the gRPC `ReserveStock`, the published event, the consumer —
and you can point at the time axis and see exactly which span dominated the
latency.

## Sampling — head vs. tail

At scale you can't store every trace, so you sample, and the only real question is
*when* the keep/drop decision is made.

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
