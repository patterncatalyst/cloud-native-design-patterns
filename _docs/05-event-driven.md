---
title: "05 · Event-Driven"
order: 5
part: "Foundations & the system"
description: "Decoupled facts that fan out — the event backbone, producing and consuming with commit-after-side-effect, schemas as the enforced contract, and the difference between event sourcing and event streaming."
duration: 18 minutes
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

## Producing and consuming

Two things matter more than the framework. First, **commit after the side-effect,
not before** — do the work, then acknowledge. Second, because you commit after, a
crash mid-handler means redelivery, so delivery is **at-least-once** and your
handlers **must be idempotent** (dedupe by message key or an idempotency key).

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

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

Events need contracts as much as REST and gRPC do — arguably more, because
consumers are anonymous and you can't call them to coordinate a change. The schema
(Avro, Protobuf, or JSON Schema) lives in the registry. Producers and consumers
fetch it, and **compatibility is checked at publish time**, so a breaking change is
rejected before it ever reaches the topic. That enforcement is what makes
"add a consumer safely" actually safe.

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

## The log is the source of truth

The mental-model correction most people need: **Kafka is a log, not a queue.**
Messages aren't deleted when read — they're retained, and each consumer group
tracks its own offset. So replay is just rewinding an offset: a new consumer can
process all of history, and a fixed consumer can re-run it. That is the foundation
for event sourcing and for rebuilding stream-processing state — the subject of **06 · Stream
Processing**.

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
