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

The code is in `examples/06-stream-processing/`. The run script there builds and
runs it; its `README.md` covers what it does and how to drive it.

---
*Verification status: unverified — code transcribed and normalised from the source
decks, not yet run. The `examples/06-stream-processing/` runner moves it to
verified.*
