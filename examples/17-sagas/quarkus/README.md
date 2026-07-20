# Example 17: Saga Orchestration (Quarkus)

This example demonstrates saga orchestration with PostgreSQL-based persistence using Quarkus 3.33.2 LTS.

## What it does

Implements a saga orchestrator that coordinates a three-step transaction across payment, inventory, and shipping services:

1. **charge_payment** → generates payment_id
2. **reserve_stock** → generates reservation_id  
3. **book_shipping** → generates shipment_id (or fails if `fail_shipping=true`)

On failure, compensations run in reverse order:
- **refund_payment** (compensates charge_payment)
- **release_stock** (compensates reserve_stock)
- **cancel_shipping** (compensates book_shipping, only if it succeeded)

The orchestrator persists saga state in PostgreSQL and can resume RUNNING sagas after a restart.

## Architecture

```
saga-orchestrator (Quarkus)
├── REST API (port 8080)
│   ├── POST /sagas — create and run saga
│   ├── GET /sagas/{id} — get saga status
│   └── GET /sagas/{id}/log — get saga execution log
├── SagaService (orchestration engine)
│   ├── advance() — execute next step or complete
│   └── compensate() — rollback completed steps
├── StepExecutor (step implementations)
└── PostgreSQL persistence
    ├── sagas table (id, status, step_index, context)
    └── saga_log table (step, action, result)
```

## Running it

```bash
cd /home/rsedor/Dev/cloud-native-design-patterns/examples/17-sagas/quarkus
podman compose up --build
```

Wait for the healthcheck to pass:
```bash
curl http://localhost:8080/healthz
# {"status":"ok"}
```

## Usage

### Happy path (all steps succeed)

```bash
curl -X POST http://localhost:8080/sagas \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ord_001",
    "sku": "widget-pro",
    "total": 199.99
  }'
```

Response (201 Created):
```json
{
  "id": "a1b2c3d4-...",
  "status": "COMPLETED",
  "step_index": 3,
  "context": {
    "order_id": "ord_001",
    "sku": "widget-pro",
    "total": 199.99,
    "charge_payment": {"payment_id": "pmt_...", "amount": 199.99},
    "reserve_stock": {"reservation_id": "rsv_...", "sku": "widget-pro"},
    "book_shipping": {"shipment_id": "shp_..."}
  }
}
```

Check the log:
```bash
curl http://localhost:8080/sagas/<saga-id>/log
```

Response:
```json
[
  {"step": "charge_payment", "action": "execute", "result": {"payment_id": "pmt_...", "amount": 199.99}},
  {"step": "reserve_stock", "action": "execute", "result": {"reservation_id": "rsv_...", "sku": "widget-pro"}},
  {"step": "book_shipping", "action": "execute", "result": {"shipment_id": "shp_..."}}
]
```

### Unhappy path (shipping fails)

```bash
curl -X POST http://localhost:8080/sagas \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ord_002",
    "sku": "widget-pro",
    "total": 199.99,
    "fail_shipping": true
  }'
```

Response (201 Created):
```json
{
  "id": "e5f6g7h8-...",
  "status": "COMPENSATED",
  "step_index": 2,
  "context": {
    "order_id": "ord_002",
    "sku": "widget-pro",
    "total": 199.99,
    "fail_shipping": true,
    "charge_payment": {"payment_id": "pmt_...", "amount": 199.99},
    "reserve_stock": {"reservation_id": "rsv_...", "sku": "widget-pro"}
  }
}
```

Check the log:
```bash
curl http://localhost:8080/sagas/<saga-id>/log
```

Response:
```json
[
  {"step": "charge_payment", "action": "execute", "result": {"payment_id": "pmt_...", "amount": 199.99}},
  {"step": "reserve_stock", "action": "execute", "result": {"reservation_id": "rsv_...", "sku": "widget-pro"}},
  {"step": "book_shipping", "action": "failed", "result": {"error": "shipping service unavailable"}},
  {"step": "release_stock", "action": "execute", "result": {"released": true}},
  {"step": "refund_payment", "action": "execute", "result": {"refunded": true}}
]
```

Note: `cancel_shipping` is correctly skipped because `book_shipping` never succeeded.

### Resume test (restart mid-saga)

The orchestrator can resume RUNNING sagas after a restart. This is tested by verify.sh:

1. Insert a RUNNING saga at step_index=1 (charge_payment completed, reserve_stock next)
2. Stop and remove the saga-orchestrator container
3. Restart the container
4. On startup, the orchestrator detects the RUNNING saga and resumes execution
5. The saga completes with all three steps

## Implementation notes

- **Manual JDBC transactions**: The `advance()` method uses manual transaction control (`setAutoCommit(false)`) instead of `@Transactional` because of the recursive call pattern. Each step execution is committed independently.
- **Row locking**: `SELECT ... FOR UPDATE` prevents concurrent modifications to the same saga.
- **JSONB handling**: PostgreSQL JSONB columns use `?::jsonb` cast with `setString()` for proper type handling.
- **Recursive advancement**: After each successful step, `advance()` calls itself to process the next step.
- **Startup resumption**: The `StartupResumer` class listens for `StartupEvent` and calls `resumeRunningSagas()` to recover any in-flight sagas.

## Quarkus-specific alternatives

### 1. Narayana LRA (MicroProfile Long Running Actions)

Add `quarkus-narayana-lra` extension for distributed saga coordination with `@LRA` and `@Compensate` annotations:

```java
@Path("/order")
public class OrderResource {
    
    @POST
    @LRA(value = LRA.Type.REQUIRES_NEW, end = true)
    public Response placeOrder(@HeaderParam(LRA_HTTP_CONTEXT_HEADER) URI lraId,
                               OrderRequest order) {
        // Execute forward action
        return Response.ok().build();
    }
    
    @PUT
    @Path("/compensate")
    @Compensate
    public Response compensateOrder(@HeaderParam(LRA_HTTP_CONTEXT_HEADER) URI lraId) {
        // Rollback action
        return Response.ok().build();
    }
}
```

Benefits:
- Declarative saga definition via annotations
- Distributed coordination across microservices
- Built-in timeout and retry handling
- REST-based LRA coordinator

### 2. Quarkus Flow (CNCF Serverless Workflow)

Add `io.quarkiverse.flow:quarkus-flow` extension for workflow orchestration with a fluent Java DSL:

```java
@ApplicationScoped
public class OrderWorkflow {
    
    @Inject
    PaymentService payments;
    
    @Inject
    InventoryService inventory;
    
    @Inject
    ShippingService shipping;
    
    public Workflow<OrderContext, OrderResult> orderSaga() {
        return workflow("order-saga", OrderContext.class, OrderResult.class)
            .tasks(
                function("chargePayment", 
                    ctx -> payments.charge(new ChargeRequest(ctx.orderId(), ctx.total())),
                    ChargeRequest.class)
                    .onError(compensate(ctx -> payments.refund(ctx.paymentId()))),
                
                function("reserveStock",
                    ctx -> inventory.reserve(new ReserveRequest(ctx.sku())),
                    ReserveRequest.class)
                    .onError(compensate(ctx -> inventory.release(ctx.reservationId()))),
                
                function("bookShipping",
                    ctx -> shipping.book(new ShipRequest(ctx.orderId())),
                    ShipRequest.class)
                    .onError(compensate(ctx -> shipping.cancel(ctx.shipmentId())))
            );
    }
}
```

Note: The actual Quarkus Flow API uses `switchWhenOrElse` for error branching. The above is a conceptual sketch showing the saga pattern.

Benefits:
- CNCF Serverless Workflow spec compliant
- Visual workflow designer (VS Code extension)
- Built-in retry, timeout, and error handling
- Event-driven execution model
- OpenTelemetry tracing out of the box

### When to use each

- **This example (manual JDBC)**: Full control, no extra dependencies, educational value, simple deployments
- **Narayana LRA**: Distributed sagas across multiple microservices with REST coordination
- **Quarkus Flow**: Complex workflows with branching, parallel execution, human tasks, or event-driven orchestration

## Verification

Run the automated test suite:

```bash
cd /home/rsedor/Dev/cloud-native-design-patterns/examples/17-sagas
./verify.sh quarkus
```

The test checks all 12 acceptance criteria:
1. Health check returns "status":"ok"
2. Happy path saga completes with COMPLETED status
3. charge_payment appears in log
4. reserve_stock appears in log
5. book_shipping appears in log
6. No compensations in happy path
7. Unhappy path (fail_shipping) reaches COMPENSATED status
8. book_shipping shows failed action
9. Compensations run in reverse order (release_stock, refund_payment)
10. cancel_shipping correctly skipped (not in log)
11. Resume test: saga completes after container restart
12. COMPOSE_FILE env var points to correct path

## Cleanup

```bash
podman compose down -v
```
