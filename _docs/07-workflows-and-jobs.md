---
title: "Workflows & Jobs"
order: 7
part: "The operational platform"
description: "Coordinating multi-step processes — orchestration versus choreography and when each fits — and where non-request work lives on Kubernetes: Jobs, CronJobs, and KEDA-scaled queue workers."
duration: 17 minutes
---

Part 1 built the synchronous surface and the asynchronous backbone. Part 2 is the
platform *around* the system. It opens with the question every multi-service
process raises: when a single business action spans several services, who
coordinates it — and where does the work that isn't a request go?

## Orchestration vs. choreography

There are two ways to coordinate a multi-step process, and they are mirror images.

**Orchestration** puts a central coordinator in charge: it commands each service
in turn — reserve stock, take payment, book shipping — and owns the end-to-end
flow. It is easy to follow, easy to observe, and easy to audit. Its failure mode
is the **god-service**: the coordinator accretes business logic until it becomes
the monolith you were trying to avoid.

**Choreography** has no central brain: each service reacts to the previous one's
event and emits its own. It is maximally decoupled — adding a step means adding a
subscriber. Its failure mode is the opposite: the end-to-end flow is *emergent*,
so nobody owns it and nobody can answer "where is order 42 stuck?".

The deeper distinction is the direction of control. Orchestration moves **commands**
outward from a coordinator that holds the workflow state explicitly — which is why
you can query that state and answer where any instance is. Choreography moves
**events** between peers that each hold only their own slice, so the workflow exists
only as the sum of their reactions: cheaper to extend, harder to see. Neither is more
"correct"; they trade *visibility and central ownership* against *coupling*, and most
large systems use both — orchestration for the few flows that need an auditable
lifecycle, choreography for the many simple fan-outs around them.

{% include excalidraw.html
   file="07-orchestration-vs-choreography"
   alt="Top: a saga orchestrator commands payment, shipping, and notification in turn. Bottom: payment, shipping, and notification react to each other's events in a chain with no central coordinator"
   caption="Figure 7.1 — A central coordinator that owns the flow, versus services reacting to events" %}

## Choosing between the two

The heuristic:

- **Orchestration** for complex, long-lived business processes where you need
  auditability and a clear owner — order fulfilment, loan approval. You want to be
  able to ask where a given instance is, and get an answer.
- **Choreography** for simple, additive reactions where decoupling matters more
  than visibility — send a welcome email when a user signs up. Adding a reaction
  shouldn't require touching a coordinator.

The trap is using choreography for a process that's actually complex, then
discovering six months later that no single place describes what the process *is*.
When the flow has compensations and a lifecycle, that lifecycle wants to live
somewhere explicit — which is exactly the persisted saga state machine in **Appendix D · Sagas**.

## Where non-request work lives

The other half of this chapter is a rule: **long, batch, or periodic work never
belongs on the request path.** Doing heavy work inside an HTTP handler blocks the
request and times out the client. Kubernetes gives you three homes for it:

- A **Job** runs a task to completion and exits — a data migration, a one-off
  export. It retries on failure up to a `backoffLimit` and is the right home for
  anything that must run once and finish.
- A **CronJob** schedules Jobs on a cron expression — the reconciliation that runs
  at 02:00 — and its `concurrencyPolicy` decides what happens when a run is still
  going as the next is due (skip it, replace it, or allow the overlap).
- A **queue worker** continuously drains a topic and is scaled by KEDA on lag,
  exactly as in the stream-processing chapter; it scales to zero when the topic is
  quiet.

{% include excalidraw.html
   file="07-jobs-cronjobs"
   alt="Three columns of non-request work on Kubernetes. Job: run-to-completion, data backfill, schema migration, retries with backoffLimit. CronJob: scheduled with a cron expression, nightly reconcile, report generation, concurrencyPolicy. Queue worker: long-lived consumer scaled by KEDA, image resize and email, off the request path."
   caption="Figure 7.2 — Three homes for non-request work: run-once Jobs, scheduled CronJobs, and KEDA-scaled queue workers" %}

```yaml
# A CronJob schedules a Job; the Job runs to completion and exits.
apiVersion: batch/v1
kind: CronJob
metadata: { name: nightly-reconcile }
spec:
  schedule: "0 2 * * *"                 # 02:00 daily
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: Never
          containers:
            - name: reconcile
              image: order-service:1.4.0
              args: ["reconcile", "--since=24h"]
```

A queue worker isn't a Job at all — it's an ordinary Deployment that loops on a
topic, with the `ScaledObject` from the stream-processing chapter giving it
scale-to-zero. The shape of the work picks the home: run-once is a Job, scheduled
is a CronJob, continuous is a scaled Deployment.

## The queue worker the YAML above never shows

The CronJob and the ScaledObject are infra — they schedule and scale the work. But
the *worker itself* is application code: a loop that drains a topic, processes each
message off the request path, and commits.

{% include excalidraw.html
   file="07-queue-worker"
   alt="An HTTP request places an order and returns 201 immediately; the order-service publishes an order.placed fact to Kafka. A separate queue-worker pod (scaled by KEDA) drains the topic, processes the work (send email, resize image, generate report), commits the offset, and the heavy work never blocks the request."
   caption="Figure 7.3 — The queue worker drains the topic off the request path; the request returns immediately" %}

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// ImageResizeWorker.java — off the request path, KEDA-scaled on lag
@Component
public class ImageResizeWorker {

    @KafkaListener(topics = "image.uploaded", groupId = "resize-worker")
    public void process(ConsumerRecord<String, String> record, Acknowledgment ack) {
        var payload = parsePayload(record.value());
        resizeAndStore(payload);                 // heavy work — never on the HTTP path
        ack.acknowledge();                       // manual commit after success
    }
}
```

```java
// ImageResizeWorker.java — Quarkus SmallRye Reactive Messaging
@ApplicationScoped
public class ImageResizeWorker {

    @Incoming("image-uploaded")                  // mapped to the Kafka topic in config
    @Blocking                                    // heavy work runs on a worker thread
    public CompletionStage<Void> process(Message<String> msg) {
        var payload = parsePayload(msg.getPayload());
        resizeAndStore(payload);                 // heavy work — never on the HTTP path
        return msg.ack();                        // manual commit after success
    }
}
```

```csharp
// ImageResizeWorker.cs — BackgroundService, KEDA-scaled on lag
public class ImageResizeWorker(ILogger<ImageResizeWorker> log) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        using var consumer = new ConsumerBuilder<Ignore, string>(new ConsumerConfig
        {
            BootstrapServers = "kafka:9094",
            GroupId = "resize-worker",
            EnableAutoCommit = false,
        }).Build();
        consumer.Subscribe("image.uploaded");

        while (!ct.IsCancellationRequested)
        {
            var cr = consumer.Consume(ct);
            var payload = ParsePayload(cr.Message.Value);
            await ResizeAndStoreAsync(payload);  // heavy work — never on the HTTP path
            consumer.Commit(cr);                 // manual commit after success
        }
    }
}
```

```python
from aiokafka import AIOKafkaConsumer

async def run_worker():
    consumer = AIOKafkaConsumer(
        "image.uploaded", bootstrap_servers="kafka:9094",
        group_id="resize-worker", enable_auto_commit=False)
    await consumer.start()
    async for msg in consumer:
        payload = parse_payload(msg.value)
        await resize_and_store(payload)          # heavy work — never on the HTTP path
        await consumer.commit()                  # manual commit after success
```

```cpp
// image_resize_worker.cc — modern-cpp-kafka consumer, KEDA-scaled on lag
kafka::clients::consumer::KafkaConsumer consumer(props);
consumer.subscribe({"image.uploaded"});

while (!stop_token.stop_requested()) {
  for (auto& record : consumer.poll(100ms)) {
    auto payload = parse_payload(record.value().toString());
    resize_and_store(payload);                   // heavy work — never on the HTTP path
    consumer.commitSync(record);                 // manual commit after success
  }
}
```

```go
// image_resize_worker.go — franz-go consumer, KEDA-scaled on lag
cl, _ := kgo.NewClient(kgo.SeedBrokers("kafka:9094"),
	kgo.ConsumerGroup("resize-worker"),
	kgo.ConsumeTopics("image.uploaded"),
	kgo.DisableAutoCommit())

for {
	fetches := cl.PollFetches(ctx)
	fetches.EachRecord(func(r *kgo.Record) {
		payload := parsePayload(r.Value)
		resizeAndStore(ctx, payload)             // heavy work — never on the HTTP path
	})
	cl.CommitUncommittedOffsets(ctx)             // manual commit after success
}
```

The point: the HTTP handler publishes the fact and returns immediately. The
worker picks it up, does the heavy processing, and commits. Kill the worker and
the message waits on the topic; restart it and work resumes from the last
committed offset — which is exactly why idempotency matters.

## Orchestration with explicit state

When a multi-step process has compensations and a lifecycle, that lifecycle wants
to live somewhere explicit — a **state machine row** that you can query, audit, and
resume. The orchestrator advances through defined steps, commits each transition
with the next command in one transaction (the same outbox discipline from the Data
chapter), and is idempotent by construction: re-running a step that already committed
is a no-op.

The code for this pattern — the DB-backed saga with row locks, idempotent advance,
and compensation in reverse — is in **Appendix D · Sagas**. What matters here is
that the state is *queryable*: you can always answer "where is order 42?" by reading
the saga row, which is the visibility that choreography sacrifices.

One discipline ties all three homes together: **idempotency**. A Job retries on
failure, a CronJob can re-run or overlap, and a redelivered message re-invokes a
queue worker — so each must be safe to run more than once. Re-running last night's
reconciliation must not double-count; reprocessing a message must not charge a card
twice. This is the same at-least-once-plus-idempotent rule from the event-driven
chapter, applied to scheduled and background work — design the task so a second run
is a no-op, and the platform's retries become a safety net instead of a hazard.

### Cross-check it yourself

Make the boundary visible. Trigger a CronJob's Job manually with `kubectl create
job --from=cronjob/nightly-reconcile run-now` and watch it run to completion and
the pod enter `Completed`, not `Running`. Separately, push a heavy task through an
HTTP handler and watch the client time out — then move the same task behind a queue
worker and watch the request return immediately while the work drains in the
background. That contrast is the whole rule.

---
*Verification status: conceptual chapter with an illustrative Kubernetes manifest —
no per-language runnable example. The coordination patterns it names are made
concrete in the saga appendix.*
