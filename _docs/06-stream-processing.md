---
title: "Stream Processing"
order: 6
part: "Foundations & the system"
description: "Deriving new streams from streams — stateful, changelog-backed windowed aggregation, and KEDA scaling workers on consumer lag rather than CPU, down to zero when the topic is quiet."
duration: 18 minutes
---

A consumer reacts to one event at a time. A *stream processor* does something more:
it treats the stream as input to a standing computation and emits a new stream.
The previous chapter established that the log is a replayable source of truth; this
chapter builds standing computations on top of it.

## Derive new streams from streams

A stream-processing app is a **topology**: sources (input topics), stateful
processors (filter, join, window, aggregate), and sinks (output topics or stores).
The output of one topology is just another stream that other services consume.

{% include excalidraw.html
   file="06-derive-streams"
   alt="A streaming topology: the orders and payments topics feed a join-and-window operator (keyed by orderId, 5-minute tumbling, with a local state store); its output feeds an aggregate operator (count, sum, rate per merchant); that emits a derived revenue topic, which a Grafana dashboard reads."
   caption="Figure 6.1 — A streaming app is a topology of sources, processors, and sinks; each output is just another stream" %}

Reading the topology left to right makes the pattern concrete: two input topics
(`orders` and `payments`) are joined and bucketed into five-minute tumbling windows
keyed by order id; the windowed result is aggregated into per-merchant counts, sums,
and rates; and that aggregate is published as a brand-new `revenue` topic that a
dashboard — or any other service — can consume. Nothing here calls another service
synchronously; each stage only reads a stream and writes a stream.

The word that matters is **stateful**. Unlike a simple consumer, these processors
keep local state — running totals, window buffers — and that state must survive
restarts. The fault-tolerance trick is a **changelog**: the local state store is
backed by a compacted Kafka topic, so if the pod dies, the state rebuilds by
replaying the changelog. That is fault-tolerant local state with no external
database in the hot path.

## A windowed aggregation

Here is the canonical example — revenue per merchant, in tumbling five-minute
windows — in each ecosystem. The JVM stacks use Kafka Streams; .NET uses Streamiz
(a native Kafka Streams port); Python uses Faust; C++ keeps bounded state
in-process and reaches for Flink only when the state outgrows a single worker.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// spring-kafka: the topology is built via a StreamsBuilder bean
@Configuration
@EnableKafkaStreams
public class RevenueTopology {
    @Bean
    public KStream<String, Order> revenueStream(StreamsBuilder b) {
        KStream<String, Order> s = b.stream("order.placed",
            Consumed.with(Serdes.String(), orderSerde));
        s.groupBy((k, o) -> o.merchantId())
         .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(5)))
         .aggregate(() -> 0.0,                        // local, changelog-backed
                    (mId, o, total) -> total + o.total(),
                    Materialized.with(Serdes.String(), Serdes.Double()))
         .toStream()
         .to("revenue.by-merchant");                  // derived stream out
        return s;
    }
}
```

```java
// quarkus-kafka-streams: the topology is a CDI-produced bean
@ApplicationScoped
public class RevenueTopology {
  @Produces
  public Topology build() {
    StreamsBuilder b = new StreamsBuilder();
    b.stream("order.placed", Consumed.with(Serdes.String(), orderSerde))
     .groupBy((k, o) -> o.merchantId())
     .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(5)))
     .aggregate(() -> 0.0,                            // local, changelog-backed
                (mId, o, total) -> total + o.total(),
                Materialized.as("revenue-by-merchant"))
     .toStream()
     .to("revenue.by-merchant");
    return b.build();
  }
}
```

```csharp
// Streamiz.Kafka.Net (MIT) — a .NET port of Kafka Streams: same
// topology / state-store / changelog model, native C#, no JVM in the container.

var config = new StreamConfig<StringSerDes, OrderSerDes>
{
    ApplicationId    = "revenue-aggregator",
    BootstrapServers = "kafka:9092",
    StateDir         = "/var/streamiz/state",   // local RocksDB, changelog-backed
};

var builder = new StreamBuilder();

builder.Stream<string, Order>("order.placed")
    .GroupBy((k, o) => o.MerchantId)
    .WindowedBy(TumblingWindowOptions.Of(TimeSpan.FromMinutes(5)))
    .Aggregate(() => 0.0,                        // local, changelog-backed
               (mId, o, total) => total + o.Total)
    .ToStream()
    .To("revenue.by-merchant");                  // derived stream out

var stream = new KafkaStream(builder.Build(), config);
await stream.StartAsync();
```

```python
import faust

app = faust.App("revenue", broker="kafka://my-cluster-kafka-bootstrap")
orders_topic = app.topic("order.placed", value_type=Order)

# table = local, changelog-backed state (a materialised view), 5-min windows
revenue = app.Table("revenue_by_merchant", default=float) \
             .tumbling(300.0, expires=3600.0)

@app.agent(orders_topic)
async def aggregate(stream):
    async for order in stream.group_by(Order.merchant_id):
        revenue[order.merchant_id] += order.total   # stateful, per key
```

```cpp
// In-process windowed aggregation: revenue-per-merchant, 5-minute tumbling.
// Stateful but bounded — fits in-process. For joins or large state: use Flink.
struct Window {
  std::chrono::sys_seconds start;
  std::unordered_map<std::string, double> revenue;   // per-merchant
};
Window current{floor_to_5min(now()), {}};

consumer.subscribe({"order.placed"});
while (!stop_token.stop_requested()) {
  for (auto& msg : consumer.poll(100ms)) {
    Order o       = deserialize(msg.value());
    auto win_start = floor_to_5min(o.placed_at);
    if (win_start != current.start) {                // window rolled over
      emit_window(current);                           // flush to revenue.by-merchant
      current = Window{win_start, {}};
    }
    current.revenue[o.merchant_id] += o.total;        // stateful, in-process
  }
}
```

```go
// In-process windowed aggregation: revenue-per-merchant, 5-minute tumbling.
// Stateful but bounded — fits in-process. Go has no Faust/Flink-class framework;
// for joins or large state, use Flink and treat Go as the producer/consumer.
type window struct {
	start   time.Time
	revenue map[string]float64 // per merchant
}

func aggregate(ctx context.Context, cl *kgo.Client) {
	cur := window{floorTo5Min(time.Now()), map[string]float64{}}
	for {
		cl.PollFetches(ctx).EachRecord(func(r *kgo.Record) {
			o := deserialize(r.Value)
			start := floorTo5Min(o.PlacedAt)
			if start != cur.start { // window rolled over
				emitWindow(cur)                            // flush to revenue.by-merchant
				cur = window{start, map[string]float64{}}
			}
			cur.revenue[o.MerchantID] += o.Total // stateful, in-process
		})
	}
}
```

### How the code works

Every tab is the same topology: read `order.placed`, group by merchant, bucket into
five-minute windows, fold each window into a running total, and write the result to
a derived `revenue.by-merchant` stream. The JVM and .NET versions get the
changelog-backed store for free — kill the pod and the window state rebuilds by
replaying the changelog topic. The C++ version keeps the window map in process,
which is fine while the state is bounded; once you need joins or state larger than a
worker, that is the signal to move to a dedicated engine like Flink rather than
hand-roll it.

## Delivery guarantees in stream processing

The windowed aggregation above has a silent assumption: what happens when the worker
crashes mid-window, or when a message is delivered twice? Stream processing has three
delivery guarantee levels, and picking the right one is a design decision:

**At-most-once** — process each message zero or one times. Commit the offset *before*
processing. If the worker crashes after committing but before processing, the message
is lost. Fast but lossy; acceptable for metrics that tolerate sampling.

**At-least-once** — process each message one or more times. Commit the offset *after*
processing. If the worker crashes after processing but before committing, the message
is redelivered and processed again. This is the default in most Kafka consumers and
the approach this book prefers — paired with **idempotent handlers** (the same
discipline from the event-driven and workflows chapters), reprocessing is a no-op
and the combination is effectively once.

**Exactly-once** — process each message exactly once, even across crashes. Kafka's
`processing.guarantee=exactly_once_v2` wraps the consume-transform-produce cycle in
a transaction: the offset commit and the output record are written atomically, so a
crash either rolls back both or commits both. The cost is higher latency (transaction
coordination) and the requirement that both input and output live on the same Kafka
cluster.

```yaml
# Kafka Streams config for exactly-once (JVM stacks)
processing.guarantee: exactly_once_v2    # atomic consume-transform-produce
# Requires: Kafka broker ≥ 2.5, transactional.id auto-assigned per task
```

For most services in this stack, **at-least-once plus idempotency** is the right
default: it is simpler, works across cluster boundaries, and the idempotency
discipline is already required by Jobs, CronJobs, and queue workers anyway.
Exactly-once is worth the cost when the output of the stream processor is a *derived
fact* (like the revenue aggregation) that other services treat as authoritative and
where double-counting would be incorrect rather than merely redundant.

## Beyond tumbling windows

The revenue example uses a tumbling window — fixed-size, non-overlapping buckets.
Kafka Streams, Faust, and Streamiz support three other window types, each suited to
a different access pattern:

{% include excalidraw.html
   file="06-window-types"
   alt="Three rows of window types. Tumbling: fixed 5-minute buckets with no overlap — event lands in exactly one window. Hopping (sliding): 5-minute windows that advance every 1 minute, overlapping — event lands in multiple windows, giving a smoothed view. Session: variable-length windows defined by an inactivity gap — no events for 10 minutes closes the window, suited to user-activity sessions."
   caption="Figure 6.3 — Three window types: tumbling (fixed, no overlap), hopping (fixed, overlapping), and session (variable, gap-based)" %}

**Tumbling windows** — fixed-size, non-overlapping. Every event lands in exactly one
window. The revenue-per-merchant aggregation uses this: a clean five-minute bucket,
no overlap.

**Hopping (sliding) windows** — fixed-size, but the window advances by a smaller
interval. A five-minute window that advances every one minute produces overlapping
windows, giving a **smoothed** view: each output reflects the last five minutes of
data, updated every minute. Good for dashboards where a hard bucket boundary would
cause a visible cliff.

**Session windows** — variable-length, defined by an **inactivity gap**. No events
for the gap duration (say, 10 minutes) closes the window. This fits user-activity
patterns: a user's browsing session is a cluster of events with quiet gaps between
them, and the session window captures that shape without you picking an arbitrary
bucket size.

**Late-arriving data** — an event whose timestamp falls inside an already-closed
window. Kafka Streams handles this with a **grace period**: windows stay open for
an additional duration after their nominal close, accepting late events. Events
that arrive after the grace period are dropped (or routed to a dead-letter topic).
Flink extends this with **watermarks** — a system-wide notion of "how far behind
event-time we expect to be" — which is essential for multi-source joins where
sources have different latencies.

**When to reach for Flink** — in-process stream processing (Kafka Streams, Faust,
Streamiz, the C++/Go loops in the example above) works well for single-topic,
bounded-state computations. Once you need **stream-to-stream joins** (correlate
orders with payments by key and time), **state larger than a single worker's
memory**, or **exactly-once across multiple Kafka clusters**, a dedicated engine
like Apache Flink is the right tool. Flink manages state snapshots, checkpointing,
and watermarks at a scale that in-process libraries don't attempt.

## Scale on the signal that matters

A stream processor's load is *backlog*, not CPU. The right scaling signal is
**consumer lag** — how far behind the log the workers are. KEDA reads that lag and
scales workers up, and crucially **down to zero** when there is no lag. For
synchronous HTTP services the same KEDA closes the loop on request rate instead.
One mechanism, two signals.

{% include excalidraw.html
   file="06-scale-on-lag"
   alt="KEDA reads the consumer lag on the order.placed topic and scales the payment-consumer pods up when lag grows and down to zero when the topic is idle"
   caption="Figure 6.2 — Scale on lag, not CPU — and to zero when the topic is quiet" %}

```yaml
# event-driven: scale consumers on Kafka lag
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
spec:
  scaleTargetRef: { name: payment-consumer }
  minReplicaCount: 0                     # scale to zero when there is no lag
  maxReplicaCount: 20
  triggers:
    - type: kafka
      metadata: { topic: order.placed, consumerGroup: payment, lagThreshold: "100" }
---
# synchronous: scale the HTTP service on concurrent requests (KEDA http-add-on)
kind: HTTPScaledObject
spec: { scaleTargetRef: { service: order-service }, replicas: { min: 0, max: 30 } }
```

The `lagThreshold: "100"` is the tuning knob — how many messages of backlog a
single worker is allowed before KEDA adds another. `minReplicaCount: 0` is the cost
lever: true scale-to-zero when the topic is quiet, springing back the moment lag
builds. Picking the signal — lag for events, request rate for HTTP — is the whole
point; scaling a backlog-bound consumer on CPU would miss the load entirely.

### Cross-check it yourself

Make lag visible, then make it move. Pause the `payment-consumer`, publish a burst
of `order.placed` with `hey` driving `order-service`, and watch the consumer-group
lag climb. Resume it and watch KEDA add replicas until the lag drains, then settle
back toward zero. The replica count tracking the lag curve — not CPU — is the
behaviour to confirm.

The code is in [`examples/06-stream-processing/`](https://github.com/patterncatalyst/cloud-native-design-patterns/tree/main/examples/06-stream-processing/). The run script there builds and
runs it; its `README.md` covers what it does and how to drive it.

---
*Verification status: verified — [`examples/06-stream-processing/`](https://github.com/patterncatalyst/cloud-native-design-patterns/tree/main/examples/06-stream-processing/) passes 7/7 checks
(windowed aggregation, changelog-backed state, consumer lag monitoring, rebalance recovery).*
