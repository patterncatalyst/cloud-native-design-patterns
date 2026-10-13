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
(a native Kafka Streams port); Python uses faust-streaming; C++ keeps bounded state
in-process and reaches for Flink only when the state outgrows a single worker.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// stream-processor RevenueTopology.java (excerpt): order.placed -> revenue.by-merchant
@Configuration
@EnableKafkaStreams
public class RevenueTopology {
    @Bean
    public KStream<String, MerchantRevenue> revenueStream(StreamsBuilder builder) {
        var orderSerde = new JacksonJsonSerde<>(OrderPlaced.class).ignoreTypeHeaders().noTypeInfo();
        var accSerde = new JacksonJsonSerde<>(Acc.class).noTypeInfo();
        var revenueSerde = new JacksonJsonSerde<>(MerchantRevenue.class).noTypeInfo();
        var revenue = builder.stream(ORDERS, Consumed.with(Serdes.String(), orderSerde))
            .filter((key, order) -> order != null && order.merchantId() != null)
            .selectKey((key, order) -> order.merchantId())     // re-key by merchant_id
            .groupByKey(Grouped.with(Serdes.String(), orderSerde))
            .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofSeconds(windowSeconds)))
            .aggregate(() -> new Acc(0, BigDecimal.ZERO),      // local, changelog-backed
                (merchant, order, acc) -> acc.add(order.total()),
                Materialized.with(Serdes.String(), accSerde))
            .toStream()
            .map((window, acc) -> KeyValue.pair(window.key(), toRevenue(window, acc)));
        revenue.to(REVENUE, Produced.with(Serdes.String(), revenueSerde));
        return revenue;                 // typed records in and out: no JSON strings built by hand
    }
}
```

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

```csharp
// StreamProcessor/Program.cs (excerpt) — Streamiz.Kafka.Net 1.8.2
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
await new KafkaStream(builder.Build(), config).StartAsync(cts.Token);
```

```python
import faust
from datetime import timedelta

app = faust.App("stream-processor", broker="kafka://my-cluster-kafka-bootstrap",
                store="memory://")      # state is rebuilt from the changelog topic
orders_topic = app.topic("order.placed", value_type=Order)
revenue_topic = app.topic("revenue.by-merchant", value_type=Revenue)

# table = local, changelog-backed state (a materialised view): tumbling windows,
# no grace (expires after one window), placed by the record's own timestamp
revenue = app.Table("revenue", default=float) \
             .tumbling(300, expires=timedelta(seconds=300)) \
             .relative_to_stream()

@app.agent(orders_topic)
async def aggregate(stream):
    async for order in stream.group_by(Order.merchant_id):   # repartition by merchant
        revenue[order.merchant_id] += order.total            # stateful, per key and window
        start = int(faust.current_event().message.timestamp // 300) * 300
        await revenue_topic.send(key=order.merchant_id, value=Revenue(
            window_start=start, window_end=start + 300, merchant_id=order.merchant_id,
            revenue=revenue[order.merchant_id].value()))     # derived stream out
```

```cpp
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

```go
// goka: a group (the Kafka consumer group) with a changelog-backed table. Stage one re-keys
// each order by merchant; stage two folds it into the merchant's tumbling windows and emits
// every update to revenue.by-merchant. Window state lives in the group table, so a restart
// replays the changelog topic and picks up where it stopped.
graph := goka.DefineGroup("stream-processor",
	goka.Input("order.placed", new(codec.Bytes), rekey),
	goka.Output("stream-processor-by-merchant", rekeyedCodec{}),
	goka.Input("stream-processor-by-merchant", rekeyedCodec{}, aggregate),
	goka.Output("revenue.by-merchant", new(codec.Bytes)),
	goka.Persist(stateCodec{}), // the group table
)

func aggregate(ctx goka.Context, msg any) {
	in := msg.(*rekeyed)                          // {ts, total} for one order
	state := loadState(ctx)                       // this merchant's windows, from the table
	start := (in.TS / 1000 / windowSeconds) * windowSeconds // 5-minute floor in the book, WINDOW_SECONDS in the example
	cur := state.add(start, in.Total)             // count + running total for the window
	ctx.SetValue(state)                           // goka writes the changelog
	ctx.Emit(revenue, ctx.Key(), revenueJSON(ctx.Key(), start, cur)) // revenue.by-merchant
}
```

### How the code works

Every tab is the same topology: read `order.placed`, group by merchant, bucket into
five-minute windows, fold each window into a running total, and write the result to
a derived `revenue.by-merchant` stream. The JVM, .NET, Python and Go versions (Kafka Streams, Streamiz, faust-streaming, goka) get a
changelog-backed store built in — kill the pod and the window state rebuilds by
replaying the changelog topic. The C++ version keeps the window map in process,
which is fine while the state is bounded; once you need joins or state larger than a
worker, that is the signal to move to a dedicated engine like Flink rather than
hand-roll it.

## Delivery guarantees in stream processing

The windowed aggregation has a silent assumption: what happens when the worker
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
Kafka Streams, faust-streaming, and Streamiz support three other window types, each suited to
a different access pattern:

{% include excalidraw.html
   file="06-window-types"
   alt="Three rows of window types. Tumbling: fixed 5-minute buckets with no overlap, so an event lands in exactly one window. Hopping (sliding): 5-minute windows that advance every 1 minute, overlapping, so an event lands in multiple windows, giving a smoothed view. Session: variable-length windows defined by an inactivity gap; no events for 10 minutes closes the window, suited to user-activity sessions."
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

**When to reach for Flink** — in-process stream processing (Kafka Streams, faust-streaming,
Streamiz, goka, the C++ loop in this chapter's example) works well for single-topic,
bounded-state computations. Once you need **stream-to-stream joins** (correlate
orders with payments by key and time), **state larger than a single worker's
memory**, or **exactly-once across multiple Kafka clusters**, a dedicated engine
like Apache Flink is the right tool. Flink manages state snapshots, checkpointing,
and watermarks at a scale that in-process libraries don't attempt.

## Scale on the signal that matters

A stream processor's load is *backlog*, not CPU. The right scaling signal is
**consumer lag** — how far behind the log the workers are. KEDA reads that lag and
scales workers up, and **down to zero** when there is no lag. For
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
metadata: { name: payment-consumer }
spec:
  scaleTargetRef: { name: payment-consumer }
  minReplicaCount: 0                     # scale to zero when there is no lag
  maxReplicaCount: 20
  triggers:
    - type: kafka
      metadata: { bootstrapServers: "cndp-kafka-bootstrap:9092", topic: order.placed,
                  consumerGroup: payment, lagThreshold: "100" }
---
# synchronous: scale the HTTP service on concurrent requests (KEDA http-add-on)
apiVersion: http.keda.sh/v1alpha1
kind: HTTPScaledObject
metadata: { name: order-service }
spec:
  hosts: [orders.example.com]
  scaleTargetRef: { name: order-service, service: order-service, port: 8080 }
  replicas: { min: 0, max: 30 }
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
*Verification status: verified — [`examples/06-stream-processing/`](https://github.com/patterncatalyst/cloud-native-design-patterns/tree/main/examples/06-stream-processing/) passes 11/11 checks in each of the six languages on Docker Engine (2026-10-12)
(per-merchant revenue aggregation onto a derived Kafka topic, the stream-processor consumer group, consumer lag that builds while the processor is paused and drains on resume, and the burst appearing in the revenue stream).*
