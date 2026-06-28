---
title: "Saga State & Compensation"
marker: "D"
label: "Appendix D"
order: 17
part: "Deep-dive appendices"
description: "The deep mechanics behind the saga — where the orchestrator keeps state so it survives a crash, how compensation unwinds committed steps in reverse, and how to thread one step's output to the next without coupling the services."
duration: 20 minutes
---

The Data chapter drew the happy path of a saga. This appendix is the three hard
parts that picture glosses over: **where the state lives**, **how compensation
unwinds a failure**, and **how step B gets data that only step A produced** —
without coupling B to A.

## Where the saga keeps its state

The orchestrator must survive a crash mid-flow, so in-memory state is a
non-starter — a pod restart would strand every in-flight saga with no idea what to
compensate. The workhorse option is a **DB-backed state machine**: one row per saga
instance holding its `status`, a `step_index`, and a `context` blob, with *you*
owning the transitions. Crucially, the state update and the next command commit
**together** in one transaction — the same outbox discipline from the Data chapter,
applied to the saga's own progress.

{% include excalidraw.html
   file="17-saga-state"
   alt="Four ways a saga can keep its state. In-memory: a dict or object only, lost on pod restart, never for real sagas. DB state machine: one row per saga instance with status and context JSON, and you own the transitions. Event-sourced: append step events and rebuild by replay, with full audit history. Workflow engine: Temporal or Camunda, durable execution with retries and timers built in. Whatever the store, the state transition and the outbound command must commit together."
   caption="Figure D.1 — Where saga state can live; the DB-backed state machine is the workhorse, but the commit-together rule is the same for all" %}

```python
STEPS = ["charge_payment", "reserve_stock", "book_shipping"]

async def advance(saga_id: str):
    async with db.transaction():                 # state + command commit together
        s = await db.get_saga(saga_id, for_update=True)   # row lock
        if s.status != "RUNNING":
            return                               # idempotent: already done/failed
        step = STEPS[s.step_index]
        result = await invoke(step, s.context)   # call the owning service
        s.context[step] = result                 # accumulate output into context
        s.step_index += 1
        if s.step_index == len(STEPS):
            s.status = "COMPLETED"
```

Because `advance` is idempotent and the row is locked, **resuming after a crash** is
trivial: on startup, scan for sagas still `RUNNING` and call `advance` again. It
picks up exactly where it left off.

## Compensation unwinds a failed saga

There is no cross-service rollback — when `book_shipping` fails, the `charge_payment`
that already committed in the payment service is *real money*. So compensation
runs a defined **semantic inverse** for each step that completed — `charge → refund`,
`reserve → release` — **in reverse order**, and only for the steps that actually
finished.

{% include excalidraw.html
   file="17-saga-compensation"
   alt="Forward path: charge_payment then reserve_stock then book_shipping, which fails. On failure the saga compensates in reverse: release_stock then refund_payment — only the steps that completed, newest first"
   caption="Figure D.2 — On failure, run each completed step's inverse, newest first" %}

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
static final Map<String,String> COMPENSATIONS = Map.of(   // inverse per step
    "charge_payment", "refund_payment",
    "reserve_stock",  "release_stock",
    "book_shipping",  "cancel_shipping");

@Transactional
public void compensate(String sagaId) {
    Saga s = em.find(Saga.class, sagaId, LockModeType.PESSIMISTIC_WRITE);
    // undo only the steps that actually completed, newest first
    for (String step : reversed(STEPS.subList(0, s.getStepIndex()))) {
        invoke(COMPENSATIONS.get(step), s.getContext());  // semantic inverse
    }
    s.setStatus("COMPENSATED");
}
```

```java
static final Map<String,String> COMPENSATIONS = Map.of(   // inverse per step
    "charge_payment", "refund_payment",
    "reserve_stock",  "release_stock",
    "book_shipping",  "cancel_shipping");

@Transactional
public void compensate(String sagaId) {
    Saga s = Saga.findById(sagaId, LockModeType.PESSIMISTIC_WRITE);
    for (String step : reversed(STEPS.subList(0, s.stepIndex))) {  // newest first
        invoke(COMPENSATIONS.get(step), s.context);               // semantic inverse
    }
    s.status = "COMPENSATED";
}
```

```csharp
static readonly Dictionary<string,string> Compensations = new()  // inverse per step
{
    ["charge_payment"] = "refund_payment",
    ["reserve_stock"]  = "release_stock",
    ["book_shipping"]  = "cancel_shipping",
};

public async Task CompensateAsync(string sagaId, CancellationToken ct)
{
    await using var tx = await db.Database.BeginTransactionAsync(ct);
    var s = await db.Sagas.FromSqlInterpolated(
        $"SELECT * FROM sagas WHERE id={sagaId} FOR UPDATE").SingleAsync(ct);
    // undo only completed steps, newest first
    foreach (var step in s.CompletedSteps().Reverse())
        await Invoke(Compensations[step], s.Context, ct);          // semantic inverse
    s.Status = "COMPENSATED";
    await tx.CommitAsync(ct);
}
```

```python
COMPENSATIONS = {                                # inverse for each forward step
    "charge_payment": "refund_payment",
    "reserve_stock":  "release_stock",
    "book_shipping":  "cancel_shipping",
}

async def compensate(saga_id: str):
    async with db.transaction():
        s = await db.get_saga(saga_id, for_update=True)
        # undo only the steps that actually completed, newest first
        for step in reversed(STEPS[: s.step_index]):
            await invoke(COMPENSATIONS[step], s.context)   # semantic inverse
        s.status = "COMPENSATED"
```

```cpp
// Compensations are a separate boost::sml branch in OrderSaga's table:
//   "comp_stock"_s + event<StockReleased>   = "comp_pay"_s,
//   "comp_pay"_s   + event<PaymentRefunded> = X,          // done
// The same advance() loop drives forward steps and compensations;
// invoke_next() dispatches on the current state name, newest-first.
Task<> compensate(sml::sm<OrderSaga>& sm, Saga& s) {
  for (auto& step : reversed(s.completed_steps()))         // newest first
    co_await invoke(inverse_of(step), s.context);          // semantic inverse
  s.status = "COMPENSATED";
}
```

```go
// compensations — the semantic inverse for each forward step
var compensations = map[string]string{
	"charge_payment": "refund_payment",
	"reserve_stock":  "release_stock",
	"book_shipping":  "cancel_shipping",
}

func compensate(ctx context.Context, pool *pgxpool.Pool, sagaID string) error {
	tx, err := pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	s, err := getSagaForUpdate(ctx, tx, sagaID) // row lock
	if err != nil {
		return err
	}
	// undo only the steps that actually completed, newest first
	done := steps[:s.StepIndex]
	for i := len(done) - 1; i >= 0; i-- {
		if err := invoke(ctx, compensations[done[i]], s.Context); err != nil { // inverse
			return err
		}
	}
	s.Status = "COMPENSATED"
	return tx.Commit(ctx)
}
```

Compensations themselves can fail, so each must be **idempotent and retryable** — a
refund that times out gets retried until it sticks, and a saga stuck compensating is
an alert, not a silent loss.

## When step B needs data only step A produced

A common source of bad designs: the orchestrator calls A, then B — but B needs a
value only A produced (a `reservation_id`, a warehouse region). The tempting wrong
answer is to have **B call A directly** — which recreates the exact service-to-service
coupling the architecture exists to avoid, and hides a dependency the orchestrator
can't see.

The right answer is already in the code above: A's result goes into the saga's
**`context` blob** (`s.context[step] = result`), and the orchestrator passes that
context into B. The data flows *through the orchestrator*, the only component that
legitimately knows the whole flow. B stays unaware of A, and because the context is
persisted with the saga state, it survives a crash too — resume rehydrates it for
free.

{% include excalidraw.html
   file="17-saga-context"
   alt="The orchestrator owns the saga context. It calls service A, which returns a reservation_id and warehouse region; that output is persisted into the saga context (reservation_id r-77, region eu-1) written after A and read before B; the orchestrator then calls service B with the context, which supplies the reservation_id B needs. If the orchestrator crashes between persisting A's output and calling B, on restart it loads the saga context, sees A is done, and resumes at B without re-calling A."
   caption="Figure D.3 — A's output flows to B through the orchestrator's persisted context — B never calls A, and a crash resumes cleanly" %}

### Cross-check it yourself

Force the unhappy path. Run the saga with `book_shipping` rigged to fail, and
confirm the database shows `release_stock` then `refund_payment` executing in that
order — and that `cancel_shipping` does *not* run, because shipping never completed.
Then kill the orchestrator pod mid-flow and restart it: the `RUNNING` saga should
resume from its persisted `step_index` and `context`, not start over. Reverse-order
inverses over only the completed steps, plus a clean resume, is the saga actually
working.

---
*Verification status: unverified — code transcribed and normalised from the source
decks, not yet run. The `examples/17-sagas/` runner moves it to verified.*
