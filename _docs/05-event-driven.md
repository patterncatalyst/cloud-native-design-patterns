---
title: "Event-Driven"
order: 5
part: "Foundations & the system"
description: "Decoupled facts that fan out — the event backbone, producing and consuming with commit-after-side-effect, schemas as the enforced contract, and the difference between event sourcing and event streaming."
duration: 30 minutes
---

The Data chapter ended with `order.placed` leaving the database through the
outbox. This chapter is about what that fact does once it's on the wire. An event
is a statement that something happened, published to whoever cares — and the
producer cares about *none* of them.

## One fact, many reactions

`order.placed` fans out to `payment`, `shipping`, and `notification`, and the
producer names none of them. That is the power move: you can add a new consumer —
a fraud-check service — **without touching or redeploying the producer.** Contrast
the synchronous world, where adding a dependency means changing the caller. This
is the open/closed principle at the architecture level, with Kafka (run by Strimzi
on Kubernetes) as the backbone.

{% include excalidraw.html
   file="05-event-backbone"
   alt="order-service emits order.placed to a Kafka topic; payment, shipping, and notification each consume it independently, and a later fraud-check service is added as a new consumer without changing the producer"
   caption="Figure 5.1 — One published fact; consumers added without touching the producer" %}

## Core benefits — and the costs they carry

Event-driven design buys three things, and the honest version of the story is that
each one comes paired with a cost you then have to design for. The benefits are why
you reach for it; the costs are what separates a system that works from one that pages
you at 3 a.m.

| Benefit | What it gives you | The cost that shadows it |
|---|---|---|
| **Loose coupling** | producers don't know their consumers — add a consumer without touching the producer | **eventual consistency**: readers see the effect *after* the event propagates, not in the producer's transaction |
| **Real-time responsiveness** | reactions fire as facts happen, not on a poll interval | **debugging complexity**: one request's story is now spread across services and a log |
| **High scalability** | partitioned consumers scale out horizontally; a slow consumer can't back-pressure the producer | **ordering & duplicates**: order holds only *within* a partition, and delivery is at-least-once |

Each cost has a standard answer, and all three already appeared in this book:

- **Eventual consistency** — the write side commits, the event ships, consumers catch
  up a moment later. Design reads to tolerate that lag, or read from the write model
  when you genuinely need read-your-writes; never assume a consumer is up to date the
  instant the producer commits. This is the same trade the outbox and CQRS sections
  make deliberately.
- **Debugging complexity** — a single user action becomes a chain of events across
  several services, so "what happened to order A-1001?" is no longer one log to grep.
  The fix is to thread a correlation / trace id through every event envelope and lean
  on distributed tracing (**Observability**); without it, you are reconstructing the
  story from five terminals.
- **Ordering & duplicates** — Kafka orders events only within a partition, so key by
  the entity (the order id) to keep one entity's events in order; there is no global
  order across partitions. And at-least-once delivery means the same event can arrive
  twice — a producer retry, a consumer rebalance — so every handler must be
  **idempotent**, deduplicating by event id or folding the work into an upsert.

The throughline: the benefits are real, but each one *moves* a hard problem rather than
removing it. Design for the cost on the same day you reach for the benefit.

## Producing and consuming

Two things matter more than the framework. First, **commit after the side-effect,
not before** — do the work, then acknowledge. Second, because you commit after, a
crash mid-handler means redelivery, so delivery is **at-least-once** and your
handlers **must be idempotent** (dedupe by message key or an idempotency key).

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// producer — order-service (or the Debezium relay) emits the fact
@Service
public class OrderEvents {
    private final KafkaTemplate<String, Order> kafka;
    public OrderEvents(KafkaTemplate<String, Order> k) { this.kafka = k; }

    public void publish(Order o) {
        kafka.send("order.placed", o.id(), o);     // keyed; schema-aware serde
    }
}

// consumer — notification-service, Kafka-only by design
@Service
public class Notifier {
    @KafkaListener(topics = "order.placed", containerFactory = "manualAckFactory")
    public void onOrder(ConsumerRecord<String, Order> rec, Acknowledgment ack) {
        sendEmail(rec.value());                    // do the work first
        ack.acknowledge();                         // ack after — at-least-once
    }
}
```

```java
// producer — order-service (or the Debezium relay) emits the fact
@ApplicationScoped
public class OrderEvents {
    @Inject @Channel("order.placed") Emitter<Order> emitter;   // Reactive Messaging
    public void publish(Order o) {
        emitter.send(KafkaRecord.of(o.id(), o));   // keyed; schema-aware serde
    }
}

// consumer — notification-service, Kafka-only by design
@ApplicationScoped
public class Notifier {
    @Incoming("order.placed")                      // offset tracked per group
    public Uni<Void> onOrder(Message<Order> msg) {
        return sendEmail(msg.getPayload())
            .chain(msg::ack);          // ack after the side-effect — at-least-once
    }
}
```

```csharp
// MassTransit (Apache 2.0) — one programming model over Kafka, RabbitMQ, or
// Azure Service Bus; sagas, retries, and a transactional outbox built in.

public record OrderPlaced(string OrderId, string Sku, int Quantity);

// producer — order-service emits the fact
public class OrderEvents(IBus bus)                  // primary constructor
{
    public Task PublishAsync(Order o) =>
        bus.Publish(new OrderPlaced(o.Id, o.Sku, o.Quantity));  // keyed by type
}

// consumer — notification-service, Kafka-only by design
public class Notifier(IEmailSender mail) : IConsumer<OrderPlaced>
{
    public async Task Consume(ConsumeContext<OrderPlaced> ctx)
    {
        await mail.Send(ctx.Message);   // do the work; acked on return
    }                                   // throw to redeliver — at-least-once
}
```

```python
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

# producer — order-service (called by the CDC relay or directly)
async def publish(topic: str, order: Order):
    await producer.send_and_wait(topic, key=order.id.encode(),
                                 value=serialize(order))   # schema-aware serde

# consumer — notification-service, Kafka-only by design
consumer = AIOKafkaConsumer("order.placed",
    bootstrap_servers=settings.kafka_bootstrap,
    group_id="notification",                 # offset tracked per group
    enable_auto_commit=False)                # commit AFTER the side-effect

async for msg in consumer:
    await send_email(deserialize(msg.value))
    await consumer.commit()                  # at-least-once; handler is idempotent
```

```cpp
// producer — process-scoped, constructed once in main()
kafka::clients::producer::KafkaProducer producer({
    {"bootstrap.servers", cfg.kafka_bootstrap},
    {"acks", "all"},                  // wait for ISR ack — durable
    {"enable.idempotence", "true"},   // no dupes on producer retry
});

void publish_order_placed(const Order& o) {
  auto rec = kafka::clients::producer::ProducerRecord(
      "order.placed", kafka::Key{o.id}, kafka::Value{serialize(o)});  // serde
  producer.send(rec, [](const auto& md, const auto& err) {
    if (err) LOG_ERROR("publish failed: {}", err.message());
  });
}

// consumer — notification-service, Kafka-only by design
kafka::clients::consumer::KafkaConsumer consumer({
    {"bootstrap.servers", cfg.kafka_bootstrap},
    {"group.id", "notification"},     // offset tracked per group
    {"enable.auto.commit", "false"},  // commit AFTER the side-effect
});
for (;;) {
  for (auto& rec : consumer.poll(std::chrono::milliseconds(500))) {
    send_email(deserialize(rec.value()));   // do the work first
    consumer.commitSync();                  // at-least-once; handler idempotent
  }
}
```

```go
// franz-go — pure-Go client; producer made once, consumer commits AFTER the work
func newProducer(cfg Settings) (*kgo.Client, error) {
	return kgo.NewClient(
		kgo.SeedBrokers(cfg.Brokers...),
		kgo.RequiredAcks(kgo.AllISRAcks()), // durable — wait for the ISR ack
		kgo.ProducerLinger(0),
	)
}

// producer — order-service (CDC relay or direct)
func publish(ctx context.Context, cl *kgo.Client, topic string, o Order) error {
	rec := &kgo.Record{Topic: topic, Key: []byte(o.ID), Value: serialize(o)} // serde
	return cl.ProduceSync(ctx, rec).FirstErr()
}

// consumer — notification-service, Kafka-only by design
func consume(ctx context.Context, cfg Settings) error {
	cl, err := kgo.NewClient(
		kgo.SeedBrokers(cfg.Brokers...),
		kgo.ConsumerGroup("notification"), // offset tracked per group
		kgo.ConsumeTopics("order.placed"),
		kgo.DisableAutoCommit(), // commit AFTER the side-effect
	)
	if err != nil {
		return err
	}
	defer cl.Close()
	for {
		fs := cl.PollFetches(ctx)
		fs.EachRecord(func(r *kgo.Record) { sendEmail(deserialize(r.Value)) }) // work first
		if err := cl.CommitUncommittedOffsets(ctx); err != nil { // at-least-once; idempotent
			slog.Error("commit failed", "err", err)
		}
	}
}
```

### How the code works

The producer is trivial and that's the point: send a **keyed** record to a topic
and walk away — it names no consumer. The key (the order id) decides the partition,
which preserves per-order ordering.

The consumer is where the care lives. Every tab disables auto-commit and
acknowledges *after* `send_email` returns. Commit before the side-effect and a
crash loses the work silently; commit after and a crash merely *redelivers* — which
is why every handler must be idempotent. "Exactly-once" is a marketing term for
"at-least-once plus a dedupe you wrote." The frameworks differ in surface —
`Acknowledgment`, `msg.ack()`, consumer-return, `commitSync()` — but the rule is
identical.

## Schemas are the contract

Events need contracts as much as REST and gRPC do — arguably more, because consumers
are anonymous and you can't call them to coordinate a change. The schema (Avro,
Protobuf, or JSON Schema) lives in a registry; in our stack that is **Apicurio**, run
in-cluster.

{% include excalidraw.html
   file="05-schemas-registry"
   alt="An Apicurio Registry at top holds versioned schemas with FORWARD/BACKWARD compatibility. The order-service producer serialises with a schema-id and sends id+bytes through Kafka to a consumer that resolves the id and deserialises; both resolve the schema by id from the registry. A CI publish gate rejects incompatible schemas before merge."
   caption="Figure 5.2 — Apicurio holds versioned schemas; producer and consumer resolve by schema-id on the hot path, and a CI gate rejects incompatible changes before merge" %}

The mechanics matter. The producer serialises a record and prefixes it with a small
**schema-id**; only the id plus the encoded bytes travel on the wire, never the schema
itself. The consumer reads the id, fetches the matching schema from the registry
(cached after the first lookup), and deserialises. Because the registry enforces a
compatibility policy — **FORWARD** so old consumers tolerate new producers, or
**BACKWARD** so new consumers tolerate old data — a change that would break the other
side is refused. Best of all, that check runs in CI at publish time: a breaking schema
is **rejected before it merges**, not discovered in production when an anonymous
consumer falls over. That enforcement is what makes "add a consumer safely" actually
safe.

## Event sourcing vs. event streaming

A vocabulary fix most teams need before going further. **Event sourcing** means
events *are* the database — there is no current-state row anywhere; current state
is computed by folding the entire event history. Crediting an account isn't
`UPDATE balance SET balance = balance + 100`; it's `INSERT INTO events ('credit',
100)`, and reading the balance means summing every event for that account.
**Event streaming** is the broader, looser idea: events flow through the system as
the integration mechanism, while current state still lives in ordinary tables.
Most systems do streaming; reserve sourcing for domains where the full history is
itself the valuable asset (ledgers, audit).

{% include excalidraw.html
   file="05-sourcing-vs-streaming"
   alt="Two columns. Event sourcing: events are the state — aggregate state is a fold of events from t0, the event log is the database, current state is rebuilt by replaying; fit is audit-heavy, financial, temporal; tools Marten, EventStoreDB, Axon. Event streaming: events are the transport — current state lives in a database, events are facts about changes, consumers react and propagate; fit is integration, fan-out, decoupling; tools Kafka, Pulsar, NATS JetStream."
   caption="Figure 5.3 — Event sourcing makes events the state; event streaming uses events as transport — and full CQRS often combines both" %}

The two are not rivals and not mutually exclusive. A common full-CQRS design is
event-sourced on the write side — the log *is* the system of record — while the read
side is a set of streaming projections fed from that same log. The question that
disambiguates them in any given design is simple: is the **event itself** the source
of truth (sourcing), or is it a **fact propagated** from a store that still holds the
truth (streaming)? Sourcing tools cluster around Marten, EventStoreDB, and Axon;
streaming runs on Kafka, Pulsar, and NATS JetStream.

## The event-driven tools landscape

The ecosystem is large and easy to cargo-cult, so it helps to sort the major
open-source tools by the job they do rather than by reputation.

{% include excalidraw.html
   file="05-tools-landscape"
   alt="Three categories. Substrate (the durable log): Kafka and Pulsar. Compute (transform and aggregate): Flink, with alternatives Kafka Streams and Spark Structured Streaming. Movement (data in and out): NiFi and Debezium. Arrows show substrate feeding compute feeding movement; a typical pipeline runs source DB to Debezium/NiFi to Kafka/Pulsar to Flink to sink."
   caption="Figure 5.4 — Three jobs: substrate (the durable log), compute (transform & aggregate), and movement (data in & out)" %}

Three categories cover almost everything. **Substrate** is the durable log itself —
**Kafka** (the de facto event spine: partitioned, ordered, offset-tracked) or
**Pulsar** (pub/sub plus queue plus log, with tiered storage and a Kafka-protocol
shim). **Compute** transforms and aggregates the streams — **Flink** is the heavyweight
stateful engine with windowed aggregations and exactly-once checkpointing, sitting on
top of Kafka or Pulsar; lighter alternatives are Kafka Streams (JVM-only) and Spark
Structured Streaming. **Movement** gets data in and out — **NiFi** for visual ETL with
hundreds of connectors and back-pressure, and **Debezium** for CDC, tailing the
database commit log (the same mechanism the Data chapter builds the outbox on). A
typical pipeline threads all three: source DB → Debezium or NiFi → Kafka or Pulsar →
Flink for windowed compute → sink. These tools complement each other far more often
than they compete, and all are Apache 2.0, so the whole pipeline runs on the same
plain Kubernetes as everything else.

## Choosing the substrate: Kafka vs Pulsar vs AMQP

The tools landscape split the work into substrate, compute, and movement; the
**substrate** — the durable broker the whole system leans on — is the load-bearing
choice. Three common answers, with genuinely different models rather than cosmetic
differences:

| | **Apache Kafka** | **Apache Pulsar** | **AMQP** (e.g. RabbitMQ) |
|---|---|---|---|
| **Model** | partitioned, append-only **log**; consumers track offsets | a log too, but split into **segments** with serving brokers separate from storage | **exchanges route to queues**; a delivered message is removed |
| **Replay** | native — rewind the offset | native — rewind, like Kafka | not built in; a consumed message is gone unless you kept a copy |
| **Ordering** | per partition (per key) | per partition (per key) | per queue |
| **Scaling** | partitions; a rebalance moves consumers | brokers and storage scale **independently**; cold segments can tier to object storage | queues; sharding is largely manual |
| **Multi-tenancy / geo** | add-on tooling | **first-class** — tenants, namespaces, and geo-replication built in | per-vhost; federation/shovel for geo |
| **Latency / throughput** | low latency, very high throughput | low latency, high throughput | very low latency at modest volume; throughput falls as queues deepen |
| **Best when** | high-throughput streaming where the durable log *is* the source of truth | you want Kafka-style streaming **plus** native multi-tenancy, geo, or storage/compute separation | classic task queues, RPC-style work distribution, and rich routing at lower volumes |

The dividing line is **log versus queue**. Kafka and Pulsar are *logs*: messages
persist, independent consumer groups read at their own offsets, and replay is just
rewinding — which is exactly why either can be the source of truth this chapter builds
on. AMQP is a *queue broker*: a message is delivered and removed, routing is rich
(exchanges, bindings, topic patterns), and it excels at work distribution and
request/reply — but "replay last week" means you stood up a separate store, because the
broker didn't keep the messages.

Pulsar's pitch over Kafka is mostly **operational**: because serving and storage are
separate layers, you can scale them independently and tier cold data to object storage,
and multi-tenancy and geo-replication are built in rather than bolted on. The price is
a larger surface to run — more components and moving parts — which only pays off for
teams that actually need those properties.

For this book's running system — `order.placed` as a replayable fact that several
services consume independently — a **log** is the right substrate, and Kafka is the
sensible default. Reach for **Pulsar** when multi-tenancy, geo, or storage/compute
separation are hard requirements, and for **AMQP** when the job is really a *task
queue* with complex routing rather than an event log you replay.

## The log is the source of truth

The mental-model correction most people need: **Kafka is a log, not a queue.**

{% include excalidraw.html
   file="05-log-truth"
   alt="A partitioned append-only log with offsets 0 through 9, head at the latest. Three consumers track independent offsets: a payment consumer at offset 9 (live), an analytics replay reset to offset 0, and a new consumer reading history from the middle with no producer impact."
   caption="Figure 5.5 — A partitioned, append-only log: each consumer tracks its own offset, so replay is just rewinding" %}

Messages aren't deleted when read — they're retained by time or size, and each
consumer group tracks **its own offset** into the partition. That one fact has large
consequences. A live consumer sits at the head, processing new records as they arrive.
An analytics job can reset to offset zero and replay the entire history. A brand-new
consumer can join later and read all of history to build its state, with **no impact
on the producer or on existing consumers** — nobody is draining a queue, so nobody
contends for the messages. Replay is simply moving an offset backward. That is the
foundation for event sourcing, for rebuilding a stream processor's state after a
crash, and for the windowed computation taken up in **06 · Stream Processing**. Both
Kafka (run by Strimzi in our cluster) and Pulsar give you this durable, replayable,
partitioned log — not a queue you drain.

### Cross-check it yourself

Produce one `order.placed` and watch two independent consumer groups receive it —
the fan-out is real, not round-robin. Then stop a consumer mid-handler (before it
commits), restart it, and confirm the message is **redelivered**, not lost: that
redelivery is the at-least-once guarantee, and the reason your handler dedupes.
`kcat` or the Kafka console tools make the offsets and redelivery visible.

The code is in `examples/05-event-driven/`. The run script there builds and runs
it; its `README.md` covers what it does and how to drive it.

---
*Verification status: unverified — code transcribed and normalised from the source
decks, not yet run. The `examples/05-event-driven/` runner moves it to verified.*
