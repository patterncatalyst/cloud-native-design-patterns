---
title: "API Error Handling"
marker: "E"
label: "Appendix E"
order: 18
part: "Deep-dive appendices"
description: "One error contract — a stable code, a safe message, a trace id, a retryable flag, field details — mapped onto REST, gRPC, Kafka and GraphQL, plus the retry-storm controls that keep a single failure from becoming an outage."
duration: 18 minutes
---

Cloud-native systems rarely fall apart on the happy path; they fall apart on the
error path, because that path gets the least design attention and the least
testing. This appendix fixes the error path the same way the rest of the book
fixes everything else: **agree one contract, then encode it consistently.** Pick a
single error model — a stable machine code, a safe human message, a correlation id,
a retryable flag, and structured field details — and map *that same model* onto each
protocol the system speaks: REST, gRPC, Kafka, and GraphQL. We close on the failure
mode that turns a brief wobble into a full outage — the retry storm — and the small
set of controls that prevent it.

## The five facts every error carries

Before any protocol-specific encoding, decide what an error *is* in this system.
Every error, everywhere, carries the same five facts:

- A **stable machine-readable code** clients branch on — `STOCK_UNAVAILABLE`, not a
  localized sentence that changes when someone edits the copy.
- A **human-readable message** that is safe to surface — no internals.
- A **correlation / trace id** that ties the error back to the distributed trace
  from the Observability chapter, so one id pivots from the client's failure to the
  exact span that produced it.
- A **retryable flag**, ideally with a concrete delay, so clients and the mesh back
  off correctly instead of guessing.
- Structured **field-level details** when the problem is about specific inputs.

The four protocols differ only in *where* those facts go on the wire — REST puts
them in a `problem+json` body, gRPC in a status plus typed details, Kafka in record
headers and a dead-letter record, GraphQL in an `errors[]` entry's `extensions`. Agree
the model once as a shared contract, and never leak a stack trace, a SQL fragment,
or an internal class name past the boundary: those are both a security exposure and
a coupling that lets a callee's internals constrain a caller.

## REST — status is the category, the body is the specifics

REST error handling works on two layers, and conflating them is the usual mistake.
The **HTTP status class is the category**, and it is what drives client behaviour: a
`4xx` says the client must fix the request and should not blindly retry; `429` and
`503` say "busy" and must travel with a `Retry-After` header so callers back off;
`5xx` says a server fault that an *idempotent* call may retry with backoff. The
**body carries the specifics**: RFC 9457 Problem Details (media type
`application/problem+json`, which superseded RFC 7807) gives a standard envelope —
`type`, `title`, `status`, `detail`, `instance` — that you extend with the stable
`code` and the `traceId`.

The discipline that makes this maintainable is **one mapping seam**: domain code
raises a typed exception, and exactly one place turns it into the wire format, so
ad-hoc error JSON never spreads across endpoints. Notice what every version below
deliberately omits — no stack trace, no exception class name, no SQL. The status
matches the category (`409`, a conflict the client can act on), and the body carries
the code and the trace id for correlation.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

```java
// Spring Framework 7's built-in ProblemDetail = RFC 9457 out of the box
@RestControllerAdvice                          // one place: domain → wire
public class ApiExceptionHandler extends ResponseEntityExceptionHandler {

    @ExceptionHandler(StockException.class)
    public ProblemDetail handleStock(StockException e) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
            HttpStatus.CONFLICT, e.getMessage());                        // 409
        pd.setType(URI.create("https://errors.acme.io/stock"));
        pd.setTitle("Insufficient stock");
        pd.setProperty("code", "STOCK_UNAVAILABLE");                     // stable
        pd.setProperty("traceId",
            Span.current().getSpanContext().getTraceId());               // correlate
        return pd;                              // Content-Type: application/problem+json
    }
}

// Typed alternative — throw an ErrorResponseException subclass from anywhere
// and Spring shapes the problem+json for you:
public class OrderNotFound extends ErrorResponseException {
    public OrderNotFound(String id) {
        super(HttpStatus.NOT_FOUND,
              ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND,
                  "Order " + id + " not found"), null);
    }
}
```

```java
public record Problem(String type, String title, int status,
                      String detail, String code, String traceId) {}

@ServerExceptionMapper                       // one place: domain → wire
public RestResponse<Problem> mapStock(StockException e) {
    var body = new Problem(
        "https://errors.acme.io/stock", "Insufficient stock", 409,
        e.getMessage(),
        "STOCK_UNAVAILABLE",                 // stable machine code
        Span.current().getSpanContext().getTraceId());  // correlate
    return RestResponse.ResponseBuilder
        .create(Response.Status.CONFLICT, body)
        .type("application/problem+json")    // RFC 9457
        .build();
}
```

```csharp
// ProblemDetails (RFC 9457) ships in the box with ASP.NET Core since .NET 6.
// .NET 8 added IExceptionHandler — the central seam for mapping typed exceptions.

// Program.cs
builder.Services.AddProblemDetails();             // standard problem+json output
builder.Services.AddExceptionHandler<DomainExceptionHandler>();
app.UseExceptionHandler();                        // wires up the chain

// One place: domain → wire (the single global exception-to-response seam)
public class DomainExceptionHandler : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(HttpContext ctx, Exception ex,
                                                 CancellationToken ct)
    {
        var (status, problem) = ex switch
        {
            StockException s => (StatusCodes.Status409Conflict,
                new ProblemDetails {
                    Type   = "https://errors.acme.io/stock",
                    Title  = "Insufficient stock",
                    Status = StatusCodes.Status409Conflict,
                    Detail = s.Message,
                    Extensions = {
                        ["code"]    = "STOCK_UNAVAILABLE",        // stable
                        ["traceId"] = Activity.Current?.TraceId.ToString(),
                    }
                }),
            _ => (StatusCodes.Status500InternalServerError, new ProblemDetails())
        };
        ctx.Response.StatusCode  = status;
        ctx.Response.ContentType = "application/problem+json";    // RFC 9457
        await ctx.Response.WriteAsJsonAsync(problem, ct);
        return true;
    }
}
```

```python
from fastapi import Request
from fastapi.responses import JSONResponse

class StockError(Exception):
    def __init__(self, detail): self.detail = detail

@app.exception_handler(StockError)          # one place: domain → wire
async def on_stock_error(request: Request, exc: StockError):
    return JSONResponse(
        status_code=409,
        media_type="application/problem+json",   # RFC 9457
        content={
            "type":    "https://errors.acme.io/stock",
            "title":   "Insufficient stock",
            "status":  409,
            "detail":  exc.detail,
            "code":    "STOCK_UNAVAILABLE",       # stable machine code
            "traceId": current_trace_id(),        # correlate w/ the trace
        })
```

```cpp
// One central exception → wire mapping; Drogon middleware catches and shapes.
struct StockError : public std::exception {
  std::string detail;
  explicit StockError(std::string d) : detail(std::move(d)) {}
  const char* what() const noexcept override { return detail.c_str(); }
};

// Drogon error-handling middleware — one place: domain → wire
Task<> error_middleware(HttpRequestPtr req, auto next) {
  try { co_await next(req); }
  catch (const StockError& e) {
    json body = {
      {"type",    "https://errors.acme.io/stock"},
      {"title",   "Insufficient stock"},
      {"status",  409},
      {"detail",  e.detail},
      {"code",    "STOCK_UNAVAILABLE"},         // stable
      {"traceId", current_trace_id()},          // correlate
    };
    auto r = HttpResponse::newHttpJsonResponse(body);
    r->setStatusCode(k409Conflict);
    r->setContentTypeString("application/problem+json");  // RFC 9457
    co_yield r;
  }
}
```

Each one registers a single handler family and lets the framework attach the
`application/problem+json` content type. In a larger codebase you would key a
base-class handler on the error family — one `switch` on a `code` — so a new domain
error means a new case, not a new endpoint-local block of error JSON.

## gRPC — the canonical code *is* the contract

gRPC ships a small, fixed set of canonical status codes, and **choosing the right
one is the contract**, because clients and the Istio mesh decide retry behaviour
straight from the code. `INVALID_ARGUMENT` and `NOT_FOUND` are client bugs: do not
retry. `FAILED_PRECONDITION` and `ALREADY_EXISTS` are state issues: do not retry.
`UNAVAILABLE` and `ABORTED` are transient: retry with backoff. `RESOURCE_EXHAUSTED`
means you are being rate-limited — honour the `RetryInfo` delay. `DEADLINE_EXCEEDED`
means the timeout needs tuning. The cardinal sin is collapsing everything into a
generic `INTERNAL`, which strips automated clients of the one signal they use to
decide whether and when to retry.

Beyond the code, attach a `google.rpc.Status` in the trailers carrying the rich
details — `ErrorInfo` (a machine `reason` plus a `domain`) and `RetryInfo` (exactly
how long to wait) — so a gRPC caller receives the same five facts as a REST caller.
`UNAVAILABLE` below tells both the client and the mesh "transient, retryable," and
the `RetryInfo` tells them precisely how long to back off.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

```java
import io.grpc.protobuf.StatusProto;
import com.google.rpc.*;

public void reserveStock(ReserveRequest req,
                         StreamObserver<ReserveReply> responseObserver) {
    if (inventoryDown) {
        var status = com.google.rpc.Status.newBuilder()
            .setCode(Code.UNAVAILABLE_VALUE)            // canonical code
            .setMessage("inventory temporarily down")
            .addDetails(Any.pack(ErrorInfo.newBuilder()
                .setReason("STOCK_DOWN").setDomain("inventory").build()))
            .addDetails(Any.pack(RetryInfo.newBuilder().setRetryDelay(
                Duration.newBuilder().setSeconds(2)).build()))  // back off 2s
            .build();
        responseObserver.onError(
            StatusProto.toStatusRuntimeException(status));
        return;
    }
    responseObserver.onNext(toReply(stock.reserve(req)));
    responseObserver.onCompleted();
}
```

```java
import io.grpc.protobuf.StatusProto;
import com.google.rpc.*;

@Blocking
public ReserveReply reserveStock(ReserveRequest req) {
    if (inventoryDown) {
        var status = com.google.rpc.Status.newBuilder()
            .setCode(Code.UNAVAILABLE_VALUE)            // canonical code
            .setMessage("inventory temporarily down")
            .addDetails(Any.pack(ErrorInfo.newBuilder()
                .setReason("STOCK_DOWN").setDomain("inventory").build()))
            .addDetails(Any.pack(RetryInfo.newBuilder().setRetryDelay(
                Duration.newBuilder().setSeconds(2)).build()))  // back off 2s
            .build();
        throw StatusProto.toStatusRuntimeException(status);
    }
    return toReply(stock.reserve(req));
}
```

```csharp
using Grpc.Core;
using Google.Rpc;            // ErrorInfo, RetryInfo, Status

public override async Task<ReserveReply> ReserveStock(
    ReserveRequest req, ServerCallContext context)
{
    if (_inventoryDown)
    {
        var status = new Google.Rpc.Status
        {
            Code    = (int)Code.Unavailable,        // canonical code
            Message = "inventory temporarily down",
            Details =
            {
                Any.Pack(new ErrorInfo {
                    Reason = "STOCK_DOWN", Domain = "inventory" }),
                Any.Pack(new RetryInfo {
                    RetryDelay = Duration.FromTimeSpan(TimeSpan.FromSeconds(2)) }),
            }
        };
        // grpc-dotnet: throw RpcException with the rich status in trailers
        throw status.ToRpcException();           // extension from Grpc.StatusProto
    }
    return ToReply(await _stock.ReserveAsync(req));
}
```

```python
from grpc_status import rpc_status
from google.rpc import status_pb2, code_pb2, error_details_pb2
from google.protobuf import any_pb2, duration_pb2

async def ReserveStock(self, request, context):
    if inventory_down:
        info = error_details_pb2.ErrorInfo(
            reason="STOCK_DOWN", domain="inventory")    # machine detail
        retry = error_details_pb2.RetryInfo(
            retry_delay=duration_pb2.Duration(seconds=2))  # back off 2s
        status = status_pb2.Status(
            code=code_pb2.UNAVAILABLE,                  # canonical code
            message="inventory temporarily down",
            details=[_pack(info), _pack(retry)])
        await context.abort_with_status(rpc_status.to_status(status))
```

```cpp
// gRPC rich status: code + ErrorInfo + RetryInfo. C++ via grpc++ + google::rpc.
#include <google/rpc/status.pb.h>
#include <google/rpc/error_details.pb.h>

grpc::Status Inventory::ReserveStock(grpc::ServerContext* ctx,
                                     const ReserveRequest* req,
                                     ReserveReply*         reply) {
  if (inventory_down_) {
    google::rpc::Status status;
    status.set_code(static_cast<int>(grpc::StatusCode::UNAVAILABLE));
    status.set_message("inventory temporarily down");
    google::rpc::ErrorInfo info;                  // machine detail
    info.set_reason("STOCK_DOWN");
    info.set_domain("inventory");
    google::rpc::RetryInfo retry;                 // back-off hint
    retry.mutable_retry_delay()->set_seconds(2);
    status.add_details()->PackFrom(info);
    status.add_details()->PackFrom(retry);
    return ::grpc::Status(
        ::grpc::StatusCode::UNAVAILABLE, status.message(),
        status.SerializeAsString());              // in trailer
  }
  // ... success path ...
  return grpc::Status::OK;
}
```

The shape is identical across stacks: build a `google.rpc.Status` with the canonical
code, pack `ErrorInfo` and `RetryInfo` into its details, and hand it to the
framework's "abort with rich status" call so it lands in the trailers. The client
library unpacks those details and the mesh reads the code — which is why getting the
code right is what prevents both silently lost work and runaway retries.

## Kafka — move failures aside so a poison record can't block the partition

A Kafka consumer has a failure mode that request/response protocols do not: a single
**poison record** can block an entire partition forever. Retry it in place and the
offset never advances, so every record queued behind it is stuck too —
head-of-line blocking at the log level. The fix is to **move the failure aside and
keep the offset moving**: try a bounded number of in-place retries, then route the
record to a delayed-retry topic (reprocessed after a delay, off the live path), and
after *N* attempts send it to a dead-letter queue for humans or tooling. Critically,
you **commit the offset either way**, so the main consumer always makes progress. The
DLQ record carries the original payload plus error and trace headers.

The frameworks differ in how much they do for you. Spring Kafka, SmallRye Reactive
Messaging, and MassTransit express the policy declaratively; with `aiokafka` and
`modern-cpp-kafka` you write the loop yourself — which makes the invariant explicit:
the commit happens on *every* branch.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

```java
@Configuration
public class KafkaErrorConfig {
    @Bean
    public DefaultErrorHandler errorHandler(KafkaTemplate<?, ?> template) {
        // route to orders.DLQ on terminal failure; commit offset; never block
        var dlt = new DeadLetterPublishingRecoverer(template,
            (rec, ex) -> new TopicPartition(rec.topic() + ".DLQ", rec.partition()));

        // in-place retries: 3 attempts, exponential backoff with jitter
        var backoff = new ExponentialBackOffWithMaxRetries(3);
        backoff.setInitialInterval(200);
        backoff.setMultiplier(2.0);
        backoff.setMaxInterval(5_000);

        var handler = new DefaultErrorHandler(dlt, backoff);
        handler.addNotRetryableExceptions(ValidationException.class);  // 4xx → DLQ now
        return handler;
    }
}

@KafkaListener(topics = "orders", containerFactory = "manualAckFactory")
public void consume(Order order) {
    handle(order);          // handler retries; exhausted → DLQ; offset commits either way
}
```

```java
// application.properties — SmallRye Reactive Messaging failure handling:
//   mp.messaging.incoming.orders.failure-strategy=dead-letter-queue
//   mp.messaging.incoming.orders.dead-letter-queue.topic=orders.DLQ
// or delayed-retry-topic first, DLQ only after the retry topics are exhausted:
//   mp.messaging.incoming.orders.failure-strategy=delayed-retry-topic
//   mp.messaging.incoming.orders.delayed-retry-topic.topics=orders.retry.5s,orders.retry.30s

@Incoming("orders")
@Retry(maxRetries = 3, delay = 200, jitter = 100)   // in-place retries first
@Blocking
public void consume(Order order) {
    handle(order);   // exhausted retries → nack → the failure-strategy above
}
// the offset is committed by the strategy, so head-of-line is never blocked
```

```csharp
// MassTransit treats Kafka topics as receive endpoints with full retry policies
// (in-process) and redelivery policies (delayed retry via scheduler).

builder.Services.AddMassTransit(x =>
{
    x.AddConsumer<OrderConsumer>(cfg =>
    {
        cfg.UseMessageRetry(r =>                          // in-place retries
            r.Exponential(retryLimit: 3,
                          minInterval: TimeSpan.FromMilliseconds(200),
                          maxInterval: TimeSpan.FromSeconds(5),
                          intervalDelta: TimeSpan.FromMilliseconds(500))
             .Ignore<ValidationException>());             // 4xx → fault now
        cfg.UseScheduledRedelivery(r =>                   // delayed-retry topics
            r.Intervals(TimeSpan.FromSeconds(5),
                        TimeSpan.FromSeconds(30),
                        TimeSpan.FromMinutes(5)));
    });

    x.UsingKafka((ctx, k) =>
    {
        k.Host("kafka:9092");
        k.TopicEndpoint<Order>("orders", "order-group", e =>
        {
            e.ConfigureConsumer<OrderConsumer>(ctx);
            // faulted messages → orders_error topic automatically
        });
    });
});

public class OrderConsumer(IEmailSender mail) : IConsumer<Order>
{
    public Task Consume(ConsumeContext<Order> ctx) => mail.SendAsync(ctx.Message);
    // retry policy fires; exhausted → redelivery; exhausted again → _error topic
}
```

```python
# bounded in-place retries, then a delayed-retry topic, then a DLQ
async for msg in consumer:
    try:
        await handle(msg)
        await consumer.commit()                       # success
    except PoisonError:
        attempts = int(header(msg, "retries", 0))
        if attempts < MAX_RETRIES:
            await producer.send("orders.retry.30s",    # delayed retry
                value=msg.value,
                headers=[("retries", str(attempts + 1).encode())])
        else:
            await producer.send("orders.DLQ", value=msg.value,
                headers=[("error", b"poison"), ("traceId", tid())])
        await consumer.commit()        # commit so head-of-line is free
```

```cpp
// Bounded in-place retries, then a delayed-retry topic, then a DLQ.
constexpr int MAX_RETRIES = 3;

while (!stop_token.stop_requested()) {
  for (auto& msg : consumer.poll(100ms)) {
    try {
      handle(msg);
      consumer.commitSync();                         // success
    } catch (const PoisonError& e) {
      int  attempts = read_header(msg, "retries", 0);
      auto value    = msg.value();
      if (attempts < MAX_RETRIES) {
        kafka::ProducerRecord rec{"orders.retry.30s",
                                  kafka::Value{value}};
        rec.headers().push_back({"retries",
                                 std::to_string(attempts + 1)});
        producer.send(rec, /*cb*/);                  // delayed retry
      } else {
        kafka::ProducerRecord dlq{"orders.DLQ", kafka::Value{value}};
        dlq.headers().push_back({"error",   "poison"});
        dlq.headers().push_back({"traceId", current_trace_id()});
        producer.send(dlq, /*cb*/);                  // DLQ
      }
      consumer.commitSync();                         // free head-of-line
    }
  }
}
```

The hand-written versions make the contract impossible to miss: the commit sits in
the `except` / `catch` branch as well as the success branch, so whether the record
succeeded, hopped to a retry topic, or landed in the DLQ, the partition advances. The
`retries` header tracks attempts and increments on each delayed-retry hop; after the
ceiling the record goes to the DLQ with its payload and a `traceId` for
investigation. One more requirement makes the whole thing safe: `handle()` must be
**idempotent**, because at-least-once delivery means a retried record may have already
applied in part.

## GraphQL — partial success, with `errors[]`

GraphQL breaks the one-request-one-status assumption that REST and gRPC rely on. A
single query fans out across many resolvers, so the response is almost always
`HTTP 200` and carries *both* a `data` object and an `errors` array. When one field
fails — say `stock` cannot reach inventory — **that field is set to `null`**, an entry
is appended to `errors[]` with a message and the `path` to the failed field, and the
shared contract rides in `extensions`: `code`, `retryable`, `traceId`. Every other
field the client asked for still returns.

The anti-pattern to name out loud is **blanket-failing** the whole operation (or
returning a `500`) when only one field broke — that discards data the client already
successfully fetched. The right move is to raise from the *single field's* resolver
and let the framework null just that field; partial success is a feature, and the
client decides whether to retry only the part that failed.

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++" %}

```java
// Spring for GraphQL: a DataFetcherExceptionResolver maps exceptions to
// GraphQLError entries in errors[]; the failing field becomes null,
// the rest of the data still returns.
@Component
public class GraphQLExceptionResolver
        extends DataFetcherExceptionResolverAdapter {
    @Override
    protected GraphQLError resolveToSingleError(Throwable ex,
                                                DataFetchingEnvironment env) {
        if (ex instanceof InventoryUnavailable iu) {
            return GraphqlErrorBuilder.newError(env)
                .errorType(ErrorType.UNAVAILABLE)              // standard category
                .message(iu.getMessage())
                .path(env.getExecutionStepInfo().getPath())
                .extensions(Map.of(
                    "code",      "UNAVAILABLE",                // machine code
                    "retryable", true,
                    "traceId",   Span.current().getSpanContext().getTraceId()))
                .build();
        }
        return null;          // delegate to the next resolver / Spring default
    }
}

@Controller
public class OrderGraphQLController {
    @SchemaMapping(typeName = "Order", field = "stock")
    public Integer stock(Order order) {                // one field's resolver
        try { return inventory.remaining(order.sku()); }
        catch (Unavailable e) {
            throw new InventoryUnavailable("inventory unavailable");  // nulls field
        }
    }
}
```

```java
import io.smallrye.graphql.api.ErrorCode;

@ErrorCode("UNAVAILABLE")                    // → errors[].extensions.code
public class InventoryUnavailable extends RuntimeException {
    public InventoryUnavailable(String m) { super(m); }
}

@GraphQLApi
public class OrderApi {
    public Integer stock(@Source Order order) {     // one field's resolver
        try { return inventory.remaining(order.sku()); }
        catch (Unavailable e) {
            throw new InventoryUnavailable("inventory unavailable"); // nulls field
        }
    }
}
// config: surface the contract fields in errors[].extensions
//   quarkus.smallrye-graphql.error-extension-fields=code,retryable,traceId
```

```csharp
// HotChocolate: an IErrorFilter maps exceptions to GraphQL errors[].
// The failing field becomes null, the rest of the data still returns.
public class GraphQLErrorFilter : IErrorFilter
{
    public IError OnError(IError error) =>
        error.Exception switch
        {
            InventoryUnavailable iu => error
                .WithMessage(iu.Message)
                .WithCode("UNAVAILABLE")                  // → extensions.code
                .SetExtension("retryable", true)
                .SetExtension("traceId", Activity.Current?.TraceId.ToString())
                .RemoveException(),                       // don't leak stack trace
            _ => error                                    // default for everything else
        };
}

// Program.cs
builder.Services.AddGraphQLServer()
    .AddErrorFilter<GraphQLErrorFilter>()
    .AddQueryType<Query>();

// Field resolver — throws normally; the filter turns it into a GraphQL error
[ExtendObjectType<Order>]
public class OrderExtensions
{
    public async Task<int> GetStock(
        [Parent] Order order, IInventoryService inventory)
    {
        try { return await inventory.RemainingAsync(order.Sku); }
        catch (UpstreamException)
        {
            throw new InventoryUnavailable("inventory unavailable");  // nulls field
        }
    }
}
```

```python
import strawberry
from graphql import GraphQLError

@strawberry.type
class Order:
    id: str
    total: float

    @strawberry.field
    async def stock(self) -> int | None:        # one field's resolver
        try:
            return await inventory.remaining(self.sku)
        except Unavailable:
            raise GraphQLError(                  # nulls THIS field only
                "inventory unavailable",
                extensions={"code": "UNAVAILABLE",   # machine code
                            "retryable": True,
                            "traceId": current_trace_id()})
```

```cpp
{% raw %}// In cppgraphqlgen, throw service::schema_exception to null a single field.
// Other fields in the same query still return data.
class OrderResolver : public object::Order {
 public:
  service::AwaitableScalar<int> getStock() const {     // one resolver
    try {
      co_return co_await inventory_.remaining(order_.sku);
    } catch (const Unavailable& e) {
      throw service::schema_exception{ {
        service::schema_error{
          "inventory unavailable",                  // safe message
          {{ "path", "order.stock" }},              // the field
          {{ "extensions", {
              { "code",      "UNAVAILABLE" },        // machine
              { "retryable", true            },
              { "traceId",   current_trace_id() },
          }}}
        }
      } };
    }
  }
  // getId(), getSku(), getTotal() still return normally — partial response
};{% endraw %}
```

The pattern is the same everywhere: raise (or `co_return`-throw) from the single
field's resolver, and let the framework catch it, null *that* field, and append the
`errors[]` entry with your `extensions`. Resisting the urge to let the exception
bubble to the top is the whole discipline — the client sees the order, the total, a
`null` stock, reads `extensions.code`, and retries just `stock`.

## How a retry storm forms — and how to stop it

Everything above makes retryability explicit, which is exactly why this last section
matters: **retries that are not bounded are how a brief blip becomes a full outage.**
The loop is a positive feedback loop. A service slows; calls start timing out; clients
retry — often three times — which *triples* the load on the already-struggling
service; which causes more timeouts; which causes more retries. Naive retry logic is
the amplifier.

{% include excalidraw.html
   file="18-retry-storm"
   alt="Top: a feedback loop between clients and a struggling order service — clients retry three times, tripling load, which produces more timeouts, which produces more retries. Bottom: six controls that break the loop — timeout, bounded retries, backoff plus jitter, circuit breaker, retry budget, and shed load."
   caption="Figure E.1 — Unbounded retries amplify a struggling service; each control removes one multiplier from the loop" %}

The controls that break the loop are the lower band of the figure, and they compose:

- **Timeout** every call, so a slow dependency cannot pin a caller's thread or
  connection indefinitely.
- **Bound the retries** to a small number, and only for *idempotent* calls — retrying
  a non-idempotent write risks doubling the side effect.
- **Backoff with jitter** so a thundering herd of clients does not retry in lockstep
  and re-synchronise the spike.
- A **circuit breaker** that trips while the dependency is down, failing fast instead
  of piling on more doomed calls.
- A **retry budget** that caps retries as a percentage of live traffic, so retries can
  never become the majority of load.
- **Shed load early** with `429` / `503` (or `UNAVAILABLE`) rather than queueing work
  you have no capacity to finish.

The Istio configuration from the Communications chapter gives several of these — the
timeout, the bounded retry policy, the outlier-detection circuit breaker — at the mesh
layer, so they apply uniformly without every service re-implementing them.

## One contract, four encodings

The cross-cutting checklist that ties the appendix together: the same five facts ride
every protocol, expressed as `problem+json`, a `google.rpc.Status`, a GraphQL
`extensions` object, or a Kafka DLQ header. Let each protocol carry the *category*
natively — HTTP status, gRPC code, a GraphQL `errors[]` entry, a Kafka DLQ-versus-retry
routing decision — instead of inventing a parallel scheme. Make retryability explicit
and machine-readable so clients and the mesh back off correctly rather than guessing.
Never leak internals onto the wire; map them to a code and keep the detail in the
server-side log, joined back by the trace id. And bound every retry — timeout, small
maximum, backoff plus jitter, circuit breaker, retry budget — while keeping every
handler idempotent. Get those right and the failure paths become as boring as the
happy ones.

### Cross-check it yourself

Prove the contract holds on the wire, in two protocols. For REST, trigger the stock
conflict and inspect the response with curl: `curl -i` should show `HTTP/1.1 409`, a
`Content-Type: application/problem+json` header, and a body whose `code` is
`STOCK_UNAVAILABLE` and whose `traceId` is present — paste that trace id into Grafana
Tempo and confirm it lands on the span that raised the error. For gRPC, call the
method with `grpcurl` against a downed inventory and confirm the status is
`UNAVAILABLE` (not `INTERNAL`) and that the `RetryInfo` detail carries the two-second
delay. Then exercise the storm controls directly: point `hey` at the REST endpoint
(or `ghz` at the gRPC one) with the dependency forced to fail, and watch the circuit
breaker trip — total downstream calls should *plateau* rather than climb with offered
load. A flat downstream-call line under rising pressure is the retry budget and breaker
doing their job; a climbing one means a control is missing.

---
*Verification status: unverified — code transcribed and normalised from the source
decks (the Quarkus gRPC and Kafka consumers are shown in blocking style), not yet run.
The framework symbols most worth confirming on a real build: Spring's
`ProblemDetail.setProperty`, the Quarkus `@ServerExceptionMapper` `RestResponse`
shape, ASP.NET Core's `IExceptionHandler`, `grpcio-status` `rpc_status.to_status`,
and the cppgraphqlgen `schema_error` extensions structure. The `examples/18-errors/`
runner moves it to verified.*
