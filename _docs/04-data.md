---
title: "04 · Data"
order: 4
part: "Foundations & the system"
description: "Read/write model separation, change data capture, and the transactional outbox that makes 'save the state and publish the event' a single atomic act."
duration: 20 minutes
---

A cloud-native service rarely owns its data in isolation. The moment an order is
placed, something else needs to know — payment wants to charge, inventory wants
to reserve stock, shipping wants to plan a label. The naive way to make that
happen is to write the order to the database and then publish an event to Kafka.
Those are two separate writes to two separate systems, and nothing makes them
happen together. This chapter is about the patterns that keep your data correct
when more than one system has to agree on what just happened: separating the
read and write models, capturing change from the database itself, and the
transactional outbox that turns "save the state **and** publish the event" into
one atomic act.

## Two models, one stream of truth

The first idea is **CQRS** — Command Query Responsibility Segregation — using
*different* models for writes and reads. The write side optimises for invariants
and consistency: a normalised schema in a transactional store. The read side
optimises for the shape of the question being asked: a denormalised table, a
search index, or a document store, whatever answers the query fastest. The two
are linked by a stream of changes flowing from the write side to the read side.

The cost is eventual consistency — a small lag between the write committing and
the read model catching up. The benefit is that each side can scale and evolve
independently. Reach for it when reads and writes genuinely have different
shapes and access patterns; skip it when a single store handles both happily,
because the separation is not free.

## Capturing change without a second write

What carries a committed change to the read model — or to any other service —
without a fragile second write? **Change Data Capture (CDC).** The application
writes ordinary SQL. The database commits, and that change lands in the
write-ahead log that already exists for replication and crash recovery (the WAL
on Postgres, the binlog on MySQL, the transaction log on SQL Server).
[Debezium](https://debezium.io) tails that log through the database's native
replication protocol, turns each row-level change into an event, and publishes
it with commit ordering preserved. The application does not know Debezium
exists. There is no dual write: the commit is the single source of truth and the
event is a strictly downstream consequence of it.

> **WAL — Write-Ahead Log.** The database's commit-ordered, durable log. It
> already exists so the database can replicate and recover from a crash;
> Debezium simply subscribes to it.

## The dual-write bug, and the outbox that fixes it

Here is the bug this chapter exists to prevent. If you write to your database and
*then* publish to Kafka as two separate operations, a crash in between leaves you
inconsistent: the order exists but the event was never sent, or the event went
out for an order that rolled back. No amount of retrying fixes it, because at the
moment of the crash there is no record of what still needs doing.

The **transactional outbox** closes the gap. Write the state change and an
*outbox row* in one local database transaction. Because both rows commit
together or not at all, the outbox row is exactly as durable as the order
itself. A CDC relay then tails the log and publishes the committed outbox rows.
The database commit remains the single source of truth, and the event becomes a
guaranteed, ordered consequence of it.

{% include excalidraw.html
   file="04-data-outbox"
   alt="The REST handler writes the order and an outbox row in one local transaction to Postgres; Debezium tails the write-ahead log and publishes the order.placed event to Kafka, which fans out to consumers"
   caption="Figure 4.1 — One local transaction; CDC turns the committed outbox row into an ordered event" %}

### The code, in your language

Pick your stack — the tab selection follows you through the rest of the book. The
shape is identical everywhere: open one local transaction, persist the state
change, persist the outbox row in the *same* transaction, commit. No broker call
sits on the request path.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

```java
// Spring Data JPA: the state change AND the outbox row in one @Transactional.
@Service
public class OrderService {
    private final OrderRepository orders;
    private final OutboxRepository outbox;

    public OrderService(OrderRepository orders, OutboxRepository outbox) {
        this.orders = orders;
        this.outbox = outbox;
    }

    @Transactional                               // single local transaction
    public Order create(OrderIn body) {
        Order order = Order.from(body);
        orders.save(order);                      // state change
        outbox.save(OutboxEntry.of(              // same txn -> outbox row
            "order.placed", "orders", order.id(), order.toJson()));
        return order;                            // Debezium tails the WAL, publishes
    }
}
// Broker down? The order still commits; the event ships when CDC catches up.
```

```java
// Debezium Quarkus Outbox: fire a CDI event inside the same transaction.
@ApplicationScoped
public class OrderService {
    @Inject Event<ExportedEvent<?, ?>> event;    // from debezium-quarkus-outbox

    @Transactional                               // single local transaction
    public Order create(OrderIn body) {
        Order order = Order.from(body);
        order.persist();                         // Panache: state change
        event.fire(OrderPlaced.of(order));       // same txn -> writes outbox row
        return order;                            // Debezium tails the WAL, publishes
    }
}
// Broker down? The order still commits; the event ships when CDC catches up.
```

```csharp
// EF Core + Debezium CDC. For WCF/COM+ refugees: this REPLACES the MSDTC
// two-phase commit you used to make "save the order AND queue the event" atomic.
public class OrderService(OrdersDbContext db) : IOrderService
{
    public async Task<Order> CreateAsync(OrderIn body)
    {
        await using var tx = await db.Database.BeginTransactionAsync();

        var order = Order.From(body);
        db.Orders.Add(order);                        // state change
        db.Outbox.Add(new OutboxEntry(               // same txn -> outbox row
            EventType:     "order.placed",
            AggregateType: "orders",
            AggregateId:   order.Id,
            Payload:       JsonSerializer.Serialize(order),
            CreatedAt:     DateTimeOffset.UtcNow));

        await db.SaveChangesAsync();                 // single local commit
        await tx.CommitAsync();                      // Debezium tails WAL -> Kafka
        return order;
    }
}
// MassTransit ships a built-in transactional outbox if you prefer the framework path.
```

```python
async def create(body: OrderIn) -> Order:
    async with db.transaction():             # single local transaction
        order = await db.execute(insert_order, body)
        await db.execute(
            insert_outbox,                   # same txn -> atomic with the state change
            topic="order.placed",
            key=order.id,
            payload=order.json(),
        )
    return order                             # Debezium tails the WAL and publishes

# No await-kafka on the request path: if the broker is down, the order still
# commits and the event is delivered when CDC catches up.
```

```cpp
Task<Order> Orders::create_impl(OrderIn body) {
    PgTxn txn = co_await pg_.begin();                  // single local txn
    Order o   = co_await txn.exec_one(insert_order_sql, body);
    co_await txn.exec(
        insert_outbox_sql,                             // atomic with the state change
        "order.placed",   // topic
        o.id,             // key
        to_json(o));      // payload
    co_await txn.commit();                             // Debezium publishes
    co_return o;
}
// PgTxn is RAII: the destructor rolls back if commit() was never called, so any
// exception thrown inside the handler unwinds the transaction cleanly.
```

### How the code works

Read any one of those tabs as if you were typing it yourself, and the same four
moves appear:

1. **Open one local transaction.** `@Transactional` in Spring and Quarkus, an
   explicit `BeginTransactionAsync` in .NET, an `async with db.transaction()` in
   Python, `pg_.begin()` in C++. Everything that follows commits together or not
   at all. This is the whole trick — there is exactly one commit, to one
   database, so there is no distributed transaction to coordinate.
2. **Persist the state change.** Save the order. Nothing about this line knows an
   event is coming.
3. **Persist the outbox row in the same transaction.** This is the line people
   are tempted to "optimise" into a Kafka call — don't. Writing a row to an
   `outbox` table keeps the event inside the transaction's atomicity. Quarkus
   hides the row behind `event.fire(...)` via `debezium-quarkus-outbox`, but it
   is still an outbox-row insert under the hood.
4. **Commit, and stop.** No broker call sits on the request path. Debezium, an
   independent connector, reads the committed outbox rows from the WAL and
   publishes them. If Kafka is down when the request runs, the order still
   commits and the event is delivered once the connector catches up.

The differences between tabs are ecosystem texture, not substance: Quarkus folds
the outbox write into a CDI event, .NET makes the transaction boundary explicit
because it replaces the MSDTC two-phase commit that older .NET services leaned
on, and C++ leans on RAII so a thrown exception unwinds the transaction without a
`finally`. The pattern is the same in all five.

> **At-least-once, so be idempotent.** Because the event is delivered after the
> commit and may be redelivered if the relay restarts, consumers must dedupe — by
> the message key or an idempotency key. "Exactly-once" in practice is
> at-least-once plus idempotent consumers. We return to this in **05 ·
> Event-Driven**.

### Cross-check it yourself

You do not have to trust that the commit and the event stay in step — you can
watch it. With the example running, stop the Kafka broker, place an order, and
confirm two things independently: the row is present in the database
(`SELECT … FROM orders`) and the outbox row is sitting unsent. Bring the broker
back and confirm the `order.placed` event arrives without replaying the request.
The order committing while the broker is down, and the event arriving later
without a re-request, is the property the outbox buys you.

The code is in `examples/04-data/`. The run script there builds and runs it; its
`README.md` covers what it does and how to drive it.

---
*Verification status: unverified — the code is transcribed from the source decks
and not yet run against a live Postgres + Debezium + Kafka stack. The
`examples/04-data/` runner exists to move this to verified.*
