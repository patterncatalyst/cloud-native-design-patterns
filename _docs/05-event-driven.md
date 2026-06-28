---
title: "Event-Driven"
order: 5
part: "Foundations & the system"
description: "Decoupled facts that fan out — the event backbone, producing and consuming with commit-after-side-effect, schemas as the enforced contract, and the difference between event sourcing and event streaming."
duration: 66 minutes
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

## Inside the substrates: architecture and what each is best at

The comparison table is the decision; the architecture is *why* each answer behaves
the way it does. Three different internal designs produce three different sets of
advantages — and knowing the design is what lets you build services that lean on a
broker's strengths instead of fighting them.

### Apache Kafka — the partitioned, replicated log

Kafka is a cluster of brokers serving topics split into **partitions**, and the
partition — not the topic — is the unit of everything. Each partition is an ordered,
append-only log: producers append (keyed by entity, so one entity's events land on one
partition and stay ordered), and each partition is replicated to a set of in-sync
replicas so a broker failure loses nothing. Consumers join a **consumer group**, the
group divides the partitions among its members, and each group tracks **its own
offset**, reading at its own position into the log.

{% include excalidraw.html
   file="05-kafka-architecture"
   alt="Producers, keyed by entity, append to a Kafka cluster drawn as a partitioned, replicated log with Partition 0, 1, and 2, each a leader plus in-sync replicas. Two consumer groups read from the cluster — a payment group that tracks its own offsets and an analytics group with independent offsets that can replay. A note: records are retained by time or size, not deleted on read; partitions give parallelism, replicas give durability, and groups read independently."
   caption="Figure 5.5 — Kafka architecture: a partitioned, replicated log read by independent consumer groups" %}

Its advantages follow from that design. Sequential appends and zero-copy reads push
very high **throughput**; partitions give linear **horizontal scale**; replication
gives **durability**; and because the log is retained rather than consumed, producers
and consumers are **decoupled in time** — a consumer can be down for an hour or added
years later and still get the full story. You build services against it the way this
chapter's producer/consumer code already does: key events by the entity, make
consumers idempotent, and commit the offset *after* the side effect.

### The log is the source of truth

The mental-model correction most people need: **Kafka is a log, not a queue.**

{% include excalidraw.html
   file="05-log-truth"
   alt="A partitioned append-only log with offsets 0 through 9, head at the latest. Three consumers track independent offsets: a payment consumer at offset 9 (live), an analytics replay reset to offset 0, and a new consumer reading history from the middle with no producer impact."
   caption="Figure 5.6 — A partitioned, append-only log: each consumer tracks its own offset, so replay is just rewinding" %}

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

### Apache Pulsar — serving split from storage

Pulsar reaches the same durable-log outcome with a two-layer architecture. A tier of
**stateless brokers** handles serving — connections, routing, subscriptions — while a
separate **Apache BookKeeper** cluster (the "bookies") owns durable storage, writing
the log as **segments** rather than fixed partitions. Because brokers hold no data they
fail over in seconds (another broker just adopts the topic), and because storage is its
own layer, cold segments **tier to object storage** and stay cheap for as long as you
keep them.

{% include excalidraw.html
   file="05-pulsar-architecture"
   alt="Producers publish to a layer of stateless Pulsar brokers, which write segments to an Apache BookKeeper cluster of bookies; BookKeeper offloads cold segments to tiered object storage. Consumers read from the brokers using subscription modes — exclusive, shared, failover, or key_shared. A note: serving and storage scale independently, stateless brokers fail over fast, and a tenant-to-namespace hierarchy gives native multi-tenancy and geo-replication."
   caption="Figure 5.7 — Pulsar architecture: stateless brokers over BookKeeper storage, with tiered offload" %}

The advantages are exactly that split made useful. Serving and storage **scale
independently**, so a spike in consumers doesn't force you to grow storage.
**Multi-tenancy is first-class** — a tenant → namespace → topic hierarchy with
per-tenant isolation and quotas — and **geo-replication** is built in. And one
substrate covers both jobs: its **subscription modes** (exclusive, shared, failover,
key-shared) yield a competing-consumer *queue* and a streaming *log* from the same
topic. The price is operational surface — brokers plus BookKeeper plus a metadata
store — which earns its keep only when you actually need those properties.

### AMQP / RabbitMQ — routing through exchanges

AMQP brokers are built around **routing**, not retention. A producer publishes to an
**exchange**, never straight to a queue; the exchange type (direct, topic, fanout,
headers) plus **bindings** decide which **queues** get a copy. Consumers pull from a
queue, **acknowledge** each message, and an acked message is **removed** — the broker's
job is to hand each message to a willing worker, not to keep history. Rejected or
expired messages flow to a **dead-letter** queue, and queues carry priorities, TTLs,
and overflow policies.

{% include excalidraw.html
   file="05-amqp-architecture"
   alt="A producer publishes with a routing key to an exchange (direct, topic, or fanout). Bindings route copies to a queue: orders bound by key and a queue: audit bound by pattern; each queue delivers to competing consumers that acknowledge, after which the message is removed. A dead-letter queue receives nacked, expired, or overflowed messages. A note: routing lives in the exchange and an acked message is removed with no replay, which is why AMQP excels at work distribution, RPC, and rich routing."
   caption="Figure 5.8 — AMQP architecture: an exchange routes through bindings to queues that competing consumers drain" %}

Its strengths are the mirror image of a log's. Routing is **rich and dynamic** — fan a
message to many queues, or route by key or pattern, without the producer knowing its
consumers — and per-message **ack / nack / requeue** makes it excellent for **work
distribution and request/reply**, where each task goes to exactly one worker and is
retried on failure. The trade-offs are the flip side: there is **no replay** (a
consumed message is gone unless you kept a copy), and throughput **degrades as queues
deepen**, because a backed-up queue is the broker holding the very state it was
designed to shed. Reach for it when the job is genuinely a task queue with complex
routing, not an event log you rewind.

For an event backbone the system treats as its memory, the log model is the one that
wins — which is the idea the rest of this chapter builds on.

## Building event-driven microservices: consume, process, produce

An event-driven microservice is small and shaped the same way every time: it
**consumes** from one or more input streams, **processes** each event (often against
some local state), and **produces** to output streams. The broker is the data plane
between services — there are no direct service-to-service calls on the hot path — and
each service owns its own state rather than reaching into anyone else's.

{% include excalidraw.html
   file="05-edm-anatomy"
   alt="An input stream, order.placed, feeds an event-driven microservice drawn as three steps in a row — consume (poll and deserialize), process (map or aggregate), produce (serialize and send) — which emits to an output stream, order.validated. A dashed state store hangs off the process step, marked stateful only, with a read/write arrow. A note: consume to process to produce; the broker is the data plane and the service owns its state."
   caption="Figure 5.9 — The event-driven microservice: consume, process, produce, with state only when the work needs it" %}

Processing comes in two flavours. **Stateless** processing — a map, a filter, an
enrichment — needs no memory of past events: each event is handled on its own, which
makes the service trivial to scale and to restart. **Stateful** processing —
aggregations, joins, running totals, deduplication — needs a **state store** the
service maintains and can rebuild from the log, a richer topic with its own
correctness rules. Most services are mostly stateless with a few stateful steps.

The core loop — consume, transform, re-emit — is the same in every stack. Here a
validator consumes `order.placed`, derives `order.validated`, and produces it, holding
no state:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// Spring Kafka — the return value is produced to the @SendTo topic
@KafkaListener(topics = "order.placed")
@SendTo("order.validated")
public OrderValidated process(Order o) {
  return new OrderValidated(o.id(), validate(o));   // pure transform, no state
}
```

```java
@Incoming("order.placed")                           // consume  (Reactive Messaging)
@Outgoing("order.validated")                        // produce
public OrderValidated process(Order o) {
  return new OrderValidated(o.id(), validate(o));   // map: one in, one out
}
```

```csharp
// MassTransit — consume the fact, publish the derived fact
public class Validator(IBus bus) : IConsumer<OrderPlaced>
{
    public Task Consume(ConsumeContext<OrderPlaced> ctx) =>
        bus.Publish(new OrderValidated(
            ctx.Message.OrderId, Validate(ctx.Message)));   // pure transform
}
```

```python
async for msg in consumer:                            # consume order.placed
    order = deserialize(msg.value)
    validated = OrderValidated(order.id, validate(order))      # transform
    await producer.send_and_wait("order.validated",
        key=order.id.encode(), value=serialize(validated))     # produce
```

```cpp
auto records = consumer.poll(std::chrono::milliseconds(200));  // consume
for (const auto& rec : records) {
  Order o = deserialize(rec.value());
  auto out = serialize(OrderValidated{o.id, validate(o)});     // transform
  producer.send(kafka::clients::producer::ProducerRecord(
      "order.validated", kafka::Key(o.id), kafka::Value(out)), cb);  // produce
}
```

```go
fetches := cl.PollFetches(ctx)                        // consume
fetches.EachRecord(func(r *kgo.Record) {
	o := deserialize(r.Value)
	out := serialize(OrderValidated{ID: o.ID, OK: validate(o)})    // transform
	cl.Produce(ctx, &kgo.Record{Topic: "order.validated",
		Key: []byte(o.ID), Value: out}, nil)          // produce
})
```

Keep the produce idempotent and commit the consumer offset *after* the produce
succeeds — the commit-after-side-effect rule again — so a crash between producing and
committing replays cleanly instead of dropping the derived event.

## The sidecar pattern: business logic on one side, the broker on the other

The consume/produce machinery — serialization, schema resolution, offset management,
retries, tracing — is identical across services and has nothing to do with any one
service's business logic. The **sidecar pattern** factors it out: a small companion
process in the same pod owns all broker I/O, and the business microservice talks to it
over a simple local API (here, gRPC on `localhost`). The service links **no broker
client at all**.

{% include excalidraw.html
   file="05-sidecar"
   alt="Two pods, service A in Go and service B in Python. In each, a business-logic component with no broker client talks over local gRPC to a sidecar that handles broker I/O. Both sidecars connect to a single Kafka cluster (topics, offsets, schema) to consume and produce. A note: the sidecar owns serde, schema, offsets, retries, and tracing, so business logic stays pure and polyglot."
   caption="Figure 5.10 — The sidecar pattern: a companion process owns broker I/O so the service stays pure and language-agnostic" %}

Three things fall out of that split. **Polyglot** — the business service can be in any
language, because the sidecar speaks the broker and the service only speaks a local
gRPC contract (which is why this book's six languages integrate identically).
**Cross-cutting concerns are centralized** — schema, serde, retry, dead-lettering, and
tracing live in one audited place instead of being re-implemented per service. And
**business logic stays pure** — testable with no broker, since publishing is just a
local call. The cost is a second process per pod and one extra local hop, usually a
fair price for the decoupling. Publishing through the sidecar carries no Kafka types in
the service:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// the sidecar (localhost, same pod) owns Kafka — no broker client here
@GrpcClient("sidecar")
private EventBusGrpc.EventBusBlockingStub sidecar;

void emit(Order o) {
  sidecar.publish(PublishRequest.newBuilder()
      .setTopic("order.placed").setKey(o.id())
      .setPayload(o.toByteString()).build());       // sidecar does serde + send
}
```

```java
@GrpcClient("sidecar") EventBus sidecar;            // local sidecar, same pod

void emit(Order o) {
  sidecar.publish(PublishRequest.newBuilder()
      .setTopic("order.placed").setKey(o.id())
      .setPayload(o.toByteString()).build())
    .await().indefinitely();                        // this service links no Kafka client
}
```

```csharp
// EventBusClient targets the local sidecar; no Kafka client in this service
async Task Emit(Order o) =>
    await _sidecar.PublishAsync(new PublishRequest {
        Topic = "order.placed", Key = o.Id, Payload = o.ToByteString() });
```

```python
# the sidecar (localhost) owns Kafka; this service only speaks gRPC to it
stub = eventbus_pb2_grpc.EventBusStub(channel)        # channel → localhost:50051

def emit(o: Order):
    stub.Publish(eventbus_pb2.PublishRequest(
        topic="order.placed", key=o.id, payload=o.SerializeToString()))
```

```cpp
// sidecar stub over a localhost channel — this service links no Kafka client
auto sidecar = EventBus::NewStub(channel);
void emit(const Order& o) {
  PublishRequest req;
  req.set_topic("order.placed"); req.set_key(o.id);
  req.set_payload(o.SerializeAsString());
  PublishReply reply; grpc::ClientContext ctx;
  sidecar->Publish(&ctx, req, &reply);                // sidecar does serde + send
}
```

```go
// the sidecar (localhost) owns the broker; business code only makes a gRPC call
func emit(ctx context.Context, sidecar pb.EventBusClient, o *Order) error {
	_, err := sidecar.Publish(ctx, &pb.PublishRequest{
		Topic: "order.placed", Key: o.ID, Payload: serialize(o)})
	return err
}
```

This is the pattern projects like Dapr generalize; you can also hand-roll a thin
sidecar around the same `EventBus` contract when you want full control of the broker
specifics.

## Eventification: turning data into streams

An event-driven system runs on streams, but most of an organization's data starts life
trapped inside the database of the service that owns it — data on the *inside*, useless
to anyone else. **Data liberation** is the practice of getting that data out as an event
stream the rest of the system can build on. The cleanest mechanism is **change data
capture (CDC)**: a connector like Debezium tails the database's commit log and emits an
event for every row change — the same log-tailing the Data chapter's outbox relies on.
When you own the writer, the **outbox** is the alternative: write the event in the same
transaction as the state change, then relay it. Either way you have **eventified** a
table into a stream.

{% include excalidraw.html
   file="05-eventification"
   alt="A source database with an orders table feeds a CDC connector (Debezium) that tails the commit log and turns each row change into an event on the topic order.changed, which consumers read to build their own views. Notes: table-to-stream (eventify) and stream-to-table (materialize) are two views of the same data with the log as the bridge; the outbox, writing the event in the same transaction, is the alternative when you own the writer."
   caption="Figure 5.11 — Eventification: change data capture liberates a table into an event stream" %}

The idea underneath is the **table–stream duality**. A stream of changes folded forward
gives you a table — its current state — and a table's change history *is* a stream. They
are two views of the same data, and the log is the bridge between them. That duality is
what the next pattern depends on.

## Event-carried state transfer and local views

Once data is liberated, events come in two styles. An **event notification** is thin —
"order A-1001 was placed" — and tells a consumer only that something happened; to act on
it, the consumer must **call back** to the source for the details, which quietly
re-introduces the synchronous coupling events were meant to remove. **Event-carried
state transfer (ECST)** instead puts enough state *in the event* — the order's customer,
total, and status — so the consumer needs no call-back at all.

{% include excalidraw.html
   file="05-ecst-vs-notification"
   alt="Two rows. Event notification: a source service sends a thin OrderPlaced with just an id to a consumer, which must make a synchronous GET /orders/{id} call back to the source API to get the details. Event-carried state transfer: the source service sends a fat OrderPlaced carrying the full state, and the consumer folds it into a local view via upsert, with no call-back. A note: carry enough state and the consumer never calls back — reads go local and the source decouples."
   caption="Figure 5.12 — Event notification forces a call-back; event-carried state transfer lets the consumer keep a local view" %}

With ECST the consumer **folds** events into its own **local, denormalized materialized
view** — a read model shaped exactly for its queries, kept current by the stream and
rebuildable by replay. Reads become local and fast, and a momentary outage of the source
no longer stalls the consumer. The cost is **denormalization**: the same facts now live
in several services' views, kept eventually consistent by the stream — the deliberate
trade an event-driven system makes, spending storage and duplication to buy decoupling
and autonomy. The consumer side is a fold into an upsert; the event alone is enough to
build the row:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
@KafkaListener(topics = "order.placed")             // ECST: the event carries the state
public void onOrder(Order o) {
  views.upsert(new OrderView(o.id(), o.customer(),  // build a local denormalized row
      o.total(), o.status()));                      // no call-back to the source
}
```

```java
@Incoming("order.placed")                           // fold the event into a local view
public void onOrder(Order o) {
  views.upsert(new OrderView(o.id(), o.customer(),
      o.total(), o.status()));                      // local read model, no call-back
}
```

```csharp
public class OrderViewProjector(IViewStore views) : IConsumer<OrderPlaced>
{
    public Task Consume(ConsumeContext<OrderPlaced> ctx) =>
        views.UpsertAsync(new OrderView(            // denormalized local row
            ctx.Message.OrderId, ctx.Message.Customer,
            ctx.Message.Total, ctx.Message.Status));  // built from the event alone
}
```

```python
async for msg in consumer:                            # ECST consumer
    o = deserialize(msg.value)
    await views.upsert(OrderView(                      # local materialized view
        o.id, o.customer, o.total, o.status))          # no call-back to the source
```

```cpp
auto records = consumer.poll(std::chrono::milliseconds(200));
for (const auto& rec : records) {
  Order o = deserialize(rec.value());
  views.upsert(OrderView{o.id, o.customer, o.total, o.status});  // local view, no call-back
}
```

```go
fetches := cl.PollFetches(ctx)
fetches.EachRecord(func(r *kgo.Record) {
	o := deserialize(r.Value)
	views.Upsert(OrderView{ID: o.ID, Customer: o.Customer,        // local view
		Total: o.Total, Status: o.Status})        // built from the event, no call-back
})
```

## Stateful microservices: the state store and its changelog

Stateless processing handles each event alone; **stateful** processing — running totals,
counts, joins, deduplication — has to remember things between events. The cloud-native
way to remember is a **local state store**: an embedded key-value store, co-located with
the partition the instance owns, that the processor reads and writes on the hot path.
There is no network round-trip to a shared database, so it is fast — but it is *local*,
so it has to survive the instance dying.

That is what the **changelog** is for. Every write to the state store is also appended to
a **compacted changelog topic** in the broker, which makes the store durable and,
crucially, **rebuildable**: when an instance crashes or a rebalance moves its partition
to another instance, the new owner replays the changelog to restore the store before it
resumes. State lives locally for speed and in the log for safety — the table–stream
duality doing real work.

{% include excalidraw.html
   file="05-state-store-changelog"
   alt="An order.placed topic feeds a stateful instance whose process step reads and writes a local state store called customer-totals. Every write is mirrored to a compacted, durable changelog topic. When a rebalance creates a new instance, it restores the store by replaying the changelog. A note: every write also goes to the changelog, so on failure or rebalance you replay it to rebuild the store and state is never lost."
   caption="Figure 5.13 — A stateful instance keeps a local state store and mirrors every write to a compacted changelog it can replay to recover" %}

Maintaining a per-customer running total looks different in each ecosystem, because the
embedded-store-plus-changelog machinery is exactly what the JVM stream-processing
frameworks give you for free and the others assemble:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// Spring Kafka Streams — the aggregate is a state store with an automatic changelog
@Bean
KStream<String, Order> totals(StreamsBuilder b) {
  KStream<String, Order> orders = b.stream("order.placed");
  orders.groupBy((k, o) -> o.customer())
        .aggregate(() -> 0.0,
            (cust, o, total) -> total + o.total(),    // running total per customer
            Materialized.as("customer-totals"));        // store + changelog topic
  return orders;
}
```

```java
// Quarkus Kafka Streams — same DSL; the store is changelog-backed
@Produces
Topology totals() {
  StreamsBuilder b = new StreamsBuilder();
  b.stream("order.placed", Consumed.with(Serdes.String(), orderSerde))
   .groupBy((k, o) -> o.customer())
   .aggregate(() -> 0.0,
       (cust, o, total) -> total + o.total(),
       Materialized.as("customer-totals"));            // durable, rebuildable
  return b.build();
}
```

```csharp
// Streamiz.Kafka.Net — the Kafka Streams model on .NET
var builder = new StreamBuilder();
builder.Stream<string, Order>("order.placed")
    .GroupBy((k, o) => o.Customer)
    .Aggregate(() => 0.0,
        (cust, o, total) => total + o.Total,
        InMemory.As<string, double>("customer-totals"));  // store + changelog
```

```python
# faust-streaming — a Table is a state store backed by a changelog topic
totals = app.Table("customer-totals", default=float)

@app.agent(app.topic("order.placed", value_type=Order))
async def aggregate(orders):
    async for o in orders.group_by(Order.customer):
        totals[o.customer] += o.total            # running total, durable + rebuildable
```

```cpp
// no Kafka Streams in C++: keep a local store, mirror each write to a compacted topic
double total = store.get(o.customer);            // local state store
store.put(o.customer, total + o.total);          // update local state
producer.send(kafka::clients::producer::ProducerRecord(
    "customer-totals", kafka::Key(o.customer),
    kafka::Value(serialize(total + o.total))), cb);   // changelog: replay to rebuild
```

```go
// goka — a group table is a state store whose changelog goka manages and recovers
func aggregate(ctx goka.Context, msg any) {
	o := msg.(*Order)
	var total float64
	if v := ctx.Value(); v != nil {              // current state for this key
		total = v.(float64)
	}
	ctx.SetValue(total + o.Total)                // goka writes the changelog + recovers
}
```

The honest ecosystem note: Kafka Streams (Spring, Quarkus), its .NET port Streamiz, and
Python's Faust give you the state store and its changelog as first-class `KTable` / `Table`
abstractions; Go's **goka** does the same with a group table; and in C++, with no such
framework, you keep the store and mirror writes to a compacted topic by hand — more code,
the identical pattern.

## State that doesn't depend on event order

A partitioned log only guarantees order *within* a partition, and even there a retry or
rebalance can redeliver. So a stateful handler has to stay correct when events arrive
**out of order or more than once**. The discipline is to make state updates independent
of arrival order:

- **Version or timestamp the events** and apply **last-writer-wins** — keep an update only
  if its version is newer than what you hold, so a late `v1` can't clobber a `v2` already
  applied.
- Prefer **commutative** updates — adding to a counter, unioning a set — where order
  simply doesn't matter.
- Make every handler **idempotent**, so a duplicate is a no-op (dedupe by event id, or
  fold into an upsert).

For stateful **joins**, the two sides must be **co-partitioned** — same key, same
partition count — so matching keys land on the same instance and its state store can see
both sides at once.

{% include excalidraw.html
   file="05-order-independent-state"
   alt="Three status events arrive out of order — v2 PACKED first, v1 PAID second, v3 SHIPPED third. A handler that keeps the highest version (last-writer-wins) feeds a state that converges to v3 SHIPPED, correct in any order. A note: version-keyed or commutative updates plus idempotency on duplicates make state correct regardless of arrival order."
   caption="Figure 5.14 — Last-writer-wins by version makes state converge correctly no matter the arrival order" %}

The same guarded upsert handles both out-of-order and duplicate status events — apply one
only if its version beats what is already stored:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
@KafkaListener(topics = "order.status")
public void onStatus(OrderStatus e) {
  OrderView cur = views.find(e.id());
  if (cur == null || e.version() > cur.version())     // last-writer-wins by version
    views.upsert(new OrderView(e.id(), e.status(), e.version()));  // ignore stale/dup
}
```

```java
@Incoming("order.status")
public void onStatus(OrderStatus e) {
  OrderView cur = views.find(e.id());
  if (cur == null || e.version() > cur.version())     // higher version wins
    views.upsert(new OrderView(e.id(), e.status(), e.version()));
}
```

```csharp
public Task Consume(ConsumeContext<OrderStatus> ctx)
{
    var e = ctx.Message; var cur = _views.Find(e.Id);
    if (cur is null || e.Version > cur.Version)        // last-writer-wins
        _views.Upsert(new OrderView(e.Id, e.Status, e.Version));
    return Task.CompletedTask;
}
```

```python
async for msg in consumer:
    e = deserialize(msg.value)
    cur = await views.find(e.id)
    if cur is None or e.version > cur.version:         # ignore stale / duplicate
        await views.upsert(OrderView(e.id, e.status, e.version))
```

```cpp
OrderStatus e = deserialize(rec.value());
auto cur = views.find(e.id);
if (!cur || e.version > cur->version)                  // last-writer-wins by version
  views.upsert(OrderView{e.id, e.status, e.version});  // stale / duplicate ignored
```

```go
e := deserialize(r.Value)
cur, ok := views.Find(e.ID)
if !ok || e.Version > cur.Version {                    // highest version wins
	views.Upsert(OrderView{ID: e.ID, Status: e.Status, Version: e.Version})
}
```

## Event time, processing time, and determinism

A stream processor sees two clocks. **Processing time** is when the consumer happens to
handle an event; **event time** is when the thing actually happened, carried *in* the
event. They drift apart — an event can be produced at 10:00, sit in a partition, and be
processed at 10:05 — and they drift by different amounts after a backlog or a replay. The
rule that keeps results stable is to compute on **event time, never the wall clock**. Do
that and reprocessing the same input — after a bug fix, or to rebuild a consumer — is
**deterministic**: it yields the same output it did the first time. Anchor a computation
to processing time and a replay tomorrow produces different windows than it did today.

Event time forces a decision about **late and out-of-order events**, since the network
delivers neither in order nor on time. A **watermark** is the processor's running
estimate that "event time has reached T; expect nothing older." It lets time-based
computation know when it is safe to act: windows up to T can close, and an event older
than T that shows up afterwards is **late** — held within a grace period, or routed to a
side output rather than silently corrupting a closed result.

{% include excalidraw.html
   file="05-event-time-watermark"
   alt="Events arrive in processing-time order with event-times 12, then 10 (out of order), then 9 (late). A handler orders them by event time with a watermark at T equals 11. Windows up to 11 close into a deterministic result; the event with event-time 9, which is older than T, is late and goes to a side output. A note: key computation off event time, not the wall clock, so replaying the log yields the same answer."
   caption="Figure 5.15 — Event time plus a watermark: close windows by event time and handle late events deliberately" %}

The deep mechanics of windows and watermarks — tumbling, sliding, and session windows,
and how a stateful engine like Flink advances them — are the subject of **06 · Stream
Processing**; here the point is the discipline that makes an event-driven system
replayable: deterministic, event-time computation.

## Checkpoints, recovery, and reprocessing

The changelog rebuilds a *state store*; a **checkpoint** does the same for a whole
processor. At intervals the engine snapshots its processing state **together with the
input offsets that produced it**, atomically. On a crash, recovery is exact: restore the
state from the last checkpoint, seek the input back to the offsets that checkpoint
recorded, and replay forward. Because state and position move as a unit, no event is
skipped and none is double-counted.

{% include excalidraw.html
   file="05-checkpoint-recovery"
   alt="A processor consumes from an input log, holding local state and an offset, and periodically snapshots state and offset together to a checkpoint store. On a crash, recovery restores from the checkpoint, seeks the input to the saved offset, and resumes the processor by replaying forward. A note: snapshot state and input offset together so on failure you restore and replay from there — and rewind on purpose to reprocess and rebuild."
   caption="Figure 5.16 — A checkpoint snapshots state and offset as a unit, so recovery restores both and replays the gap" %}

The last piece is making the *output* survive recovery too. Replaying after a crash
re-emits events, so either every downstream consumer is idempotent (the last-writer-wins
discipline from the stateful section) or the produce and the offset commit are wrapped in
a **transaction** so they land **exactly once**. The transactional consume-process-produce
looks like this:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// Spring Kafka transactions — produce and offset commit are one atomic unit
@KafkaListener(topics = "order.placed")
@Transactional("kafkaTxManager")
public void process(Order o) {
  kafka.send("order.validated", o.id(), validate(o));   // exactly-once on replay
}
```

```java
// SmallRye KafkaTransactions — produce inside the transaction, offsets bound on commit
@Inject @Channel("order.validated") KafkaTransactions<OrderValidated> tx;

@Incoming("order.placed")
public Uni<Void> process(Order o) {
  return tx.withTransaction(em -> {
    em.send(validate(o));                               // produce in-transaction
    return Uni.createFrom().voidItem();
  });
}
```

```csharp
// Confluent.Kafka transactions — output + consumed offsets commit together
producer.BeginTransaction();
producer.Produce("order.validated", Msg(Validate(o)));         // produce
producer.SendOffsetsToTransaction(offsets, groupMeta, timeout); // + offsets
producer.CommitTransaction();                                   // atomic
```

```python
# aiokafka transaction — produce and offsets commit atomically
async with producer.transaction():
    await producer.send("order.validated",
        value=serialize(validate(o)), key=o.id.encode())
    await producer.send_offsets_to_transaction(offsets, group_id)
```

```cpp
// modern-cpp-kafka transactions
producer.beginTransaction();
producer.send(record("order.validated", o.id, validate(o)));   // produce
producer.sendOffsetsToTransaction(offsets, groupMeta, timeout);
producer.commitTransaction();                                   // atomic
```

```go
// franz-go transactions — a transactional id is configured on the client
cl.BeginTransaction()
cl.Produce(ctx, &kgo.Record{Topic: "order.validated",
	Key: []byte(o.ID), Value: serialize(validate(o))}, nil)    // produce
cl.EndTransaction(ctx, kgo.TryCommit)                          // commit output + offsets
```

Reprocessing is the same machinery used on purpose. Because the log retains history and
the processor keys off event time, you can **rewind the offsets** — to a checkpoint, or
all the way to zero — and reprocess: to fix a bug in the logic, to rebuild a consumer's
state from scratch, or to populate a brand-new view. Replay is not only a recovery path;
it is how an event-driven system evolves without migrations.

## Choreography and orchestration

A single event rarely finishes a business process; an order has to be paid for, stocked,
and shipped, and those steps live in different services. There are two ways to coordinate
them.

**Choreography** has no coordinator. Each service reacts to an event and emits its own:
`OrderPlaced` makes payment charge and emit `PaymentTaken`, which makes inventory reserve
and emit `StockReserved`, on down the line. It is maximally decoupled — services know only
the events, not each other — and it scales naturally. The cost is that the end-to-end flow
is **emergent**: no single place describes the whole process, so understanding or changing
it means tracing events across services.

**Orchestration** adds a coordinator that owns the workflow explicitly. The orchestrator
issues **commands** ("charge this order"), waits for replies, and decides the next step.
The flow is now legible and centrally monitored — one component knows the whole story — but
the orchestrator is a **coupling point** and one more thing to keep available.

{% include excalidraw.html
   file="05-choreography-orchestration"
   alt="Top: choreography — order-service emits OrderPlaced to payment-service, which emits PaymentTaken to inventory-service, which emits StockReserved to shipping-service, a reacting chain with no coordinator. Bottom: orchestration — a central orchestrator that drives the workflow exchanges command and reply messages with payment, inventory, and shipping services. A note: choreography's flow is emergent and decoupled; orchestration's flow is explicit but the coordinator is a coupling point."
   caption="Figure 5.17 — Choreography reacts to events with no coordinator; orchestration centralizes the flow in one" %}

Neither is universally right. Choreography suits simple, stable flows where decoupling
matters most; orchestration earns its keep when a process is complex, needs visibility, or
changes often. Many systems mix them — choreography between bounded contexts, orchestration
within one.

## The saga: a transaction across services

The hard part of any multi-service flow is failure: payment succeeds, then shipping can't
be booked — and there is no distributed lock to roll the whole thing back, because each
service owns its own data. A **saga** is the event-driven answer. It models the process as
a sequence of **local transactions**, each in one service, each emitting an event that
triggers the next. If a step fails, the saga runs **compensating actions** — semantic undos
like "refund the payment" and "release the stock" — in reverse, returning the system to a
consistent state without ever holding a lock across services.

{% include excalidraw.html
   file="05-saga-compensation"
   alt="A saga runs T1 charge payment, then T2 reserve stock, then T3 book shipping, which fails. The failure triggers compensation in reverse: C2 release stock, then C1 refund payment. A note: each step is a local transaction; on a failure, run compensating actions in reverse — atomicity without a distributed lock, with the full treatment in Appendix D."
   caption="Figure 5.18 — A saga: local transactions forward, compensating actions in reverse when a step fails" %}

A saga can be driven either way. A **choreographed saga** advances on events and triggers
compensations the same way — fully decentralized. An **orchestrated saga** lets the
orchestrator drive both the forward steps and the compensations, which is easier to reason
about when there are many steps. A choreographed step is just a consume-act-emit handler
that emits "advance" on success and "compensate" on failure:

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
@KafkaListener(topics = "order.placed")              // a choreographed saga step
public void onOrder(Order o) {
  try {
    payments.charge(o.id(), o.total());              // local transaction
    kafka.send("payment.taken", o.id(), new PaymentTaken(o.id()));    // advance
  } catch (PaymentDeclined e) {
    kafka.send("payment.failed", o.id(), new PaymentFailed(o.id()));  // compensate upstream
  }
}
```

```java
@Incoming("order.placed")
@Outgoing("payment.result")                          // routed to taken / failed downstream
public PaymentResult onOrder(Order o) {
  try {
    payments.charge(o.id(), o.total());              // local transaction
    return PaymentResult.taken(o.id());              // advance the saga
  } catch (PaymentDeclined e) {
    return PaymentResult.failed(o.id());             // trigger compensation
  }
}
```

```csharp
public async Task Consume(ConsumeContext<OrderPlaced> ctx)
{
    try {
        await _payments.Charge(ctx.Message.OrderId, ctx.Message.Total);  // local tx
        await ctx.Publish(new PaymentTaken(ctx.Message.OrderId));        // advance
    } catch (PaymentDeclined) {
        await ctx.Publish(new PaymentFailed(ctx.Message.OrderId));       // compensate
    }
}
```

```python
async for msg in consumer:                            # a choreographed saga step
    o = deserialize(msg.value)
    try:
        await payments.charge(o.id, o.total)          # local transaction
        await producer.send("payment.taken", serialize(PaymentTaken(o.id)))   # advance
    except PaymentDeclined:
        await producer.send("payment.failed", serialize(PaymentFailed(o.id))) # compensate
```

```cpp
Order o = deserialize(rec.value());
try {
  payments.charge(o.id, o.total);                     // local transaction
  producer.send(rec_for("payment.taken", o.id, PaymentTaken{o.id}));    // advance
} catch (const PaymentDeclined&) {
  producer.send(rec_for("payment.failed", o.id, PaymentFailed{o.id}));  // compensate
}
```

```go
o := deserialize(r.Value)
if err := payments.Charge(o.ID, o.Total); err != nil {            // local transaction
	cl.Produce(ctx, recFor("payment.failed", o.ID, PaymentFailed{o.ID}), nil)  // compensate
} else {
	cl.Produce(ctx, recFor("payment.taken", o.ID, PaymentTaken{o.ID}), nil)    // advance
}
```

Sagas trade atomicity for availability: the system is **eventually** consistent, briefly
passing through states where payment is taken but stock isn't yet reserved, which the
compensations resolve. The full mechanics — idempotent compensations, the semantic-lock and
pivot-transaction patterns, and what to do when a step can't be compensated — are the
subject of **Appendix D**.

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
