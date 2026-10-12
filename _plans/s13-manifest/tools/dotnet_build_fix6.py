#!/usr/bin/env python3
"""S13 .NET deck edits (fix6): slides follow the EF Core / HealthChecks / BackgroundService / HybridCache examples.

Run from the worktree root. Writes lgtm-presentation/edits/Designing-Cloud-Native-APIs-DotNet.fix6.json.
Notes are rebuilt from the committed text copy with exact, asserted replacements.
"""
import json, re, sys
from pathlib import Path

ROOT = Path.cwd()
TEXT = (ROOT / "lgtm-presentation/text/Designing-Cloud-Native-APIs-DotNet.md").read_text()
SLIDES = re.split(r"(?m)^(?=## \[\d{3}\] )", TEXT)[1:]
OUT = ROOT / "lgtm-presentation/edits/Designing-Cloud-Native-APIs-DotNet.fix6.json"
MAX_COLS = 95
ops = []
ERR = []


def sld(n):
    m = re.search(r"sldId (\d+)\)", SLIDES[n - 1].split("\n")[0])
    return int(m.group(1))


def notes_paragraphs(n):
    paras, cur = [], []
    for line in SLIDES[n - 1].split("\n"):
        if line.startswith(">"):
            t = line[1:].strip()
            if t:
                cur.append(t)
            else:
                if cur:
                    paras.append(" ".join(cur)); cur = []
    if cur:
        paras.append(" ".join(cur))
    return paras


def set_code(n, lines, why, pt=None):
    lines = [x for l in lines for x in l.split("\n")]
    for l in lines:
        if len(l) > MAX_COLS:
            ERR.append((n, len(l), l))
    op = {"op": "set_code", "sldId": sld(n), "lines": lines, "cat": "code", "_slide": n, "_why": why, "_src": "s13"}
    if pt:
        op["pt"] = pt
    ops.append(op)


def replace(n, find, repl, why, scope="slide", expect=1, cat="code"):
    assert find in SLIDES[n - 1], (n, find)
    ops.append({"op": "replace", "scope": scope, "sldIds": [sld(n)], "find": find, "repl": repl,
                "expect": expect, "cat": cat, "_slide": n, "_why": why, "_src": "s13"})


def notes(n, pairs, why):
    paras = notes_paragraphs(n)
    text = "\n".join(paras)
    for old, new in pairs:
        if isinstance(old, tuple):  # span: (start, end)
            a = text.index(old[0]); b = text.index(old[1], a) + len(old[1])
            text = text[:a] + new + text[b:]
        else:
            assert old in text, (n, old)
            text = text.replace(old, new, 1)
    ops.append({"op": "set_notes", "sldId": sld(n), "paragraphs": text.split("\n"), "cat": "notes",
                "_slide": n, "_why": why, "_src": "s13"})


# ---------------------------------------------------------------- 15: Example 01
replace(15, "csharp · .NET 10 + ASP.NET Core + Npgsql", "csharp · .NET 10 + ASP.NET Core + EF Core health checks",
        "examples/01: AddHealthChecks + MapHealthChecks over an EF Core context")
set_code(15, [
    "// Program.cs (excerpt), examples/01-cloud-native-principles/dotnet",
    "builder.Services.AddDbContext<OrdersContext>(o => o.UseNpgsql(connString)); // factor III",
    "builder.Services.AddHealthChecks()",
    "    .AddDbContextCheck<OrdersContext>(\"database\", tags: [\"ready\"]);  // readiness: can connect",
    "var app = builder.Build();",
    "app.MapHealthChecks(\"/healthz\", new HealthCheckOptions               // liveness: process up",
    "{",
    "    Predicate = _ => false,                                           // no dependency checks",
    "    ResponseWriter = (ctx, _) => ctx.Response.WriteAsJsonAsync(new { status = \"ok\" }),",
    "});",
    "app.MapHealthChecks(\"/readyz\", new HealthCheckOptions                // readiness: 200 or 503",
    "{",
    "    Predicate = r => r.Tags.Contains(\"ready\"),",
    "    ResponseWriter = (ctx, report) =>",
    "    {",
    "        var up = report.Status == HealthStatus.Healthy;               // down: out of rotation",
    "        return ctx.Response.WriteAsJsonAsync(new { status = up ? \"ready\" : \"down\",",
    "            checks = new { database = up ? \"ok\" : \"unreachable\" } });",
    "    },",
    "});",
], "examples/01: health checks replace the hand-written probes; readiness answers 503 when the database is down")
notes(15, [(("The two probes are mapped by hand in Example 01", "the example writes the handlers by hand so every language serves the same paths and bodies."),
    "The two probes come from AddHealthChecks and MapHealthChecks in Example 01: /healthz is liveness (am I alive? if not, restart me, and Kubernetes kills the Pod) and runs no dependency check; /readyz is readiness (can I serve? if not, take me out of rotation but don't kill me): its check is AddDbContextCheck, which asks the EF Core context whether it can reach Postgres, and when that fails the endpoint answers 503 with status down, which removes the Pod from the Service endpoints. The probe reads the status code, not the body: Kubernetes treats any answer from 200 to 399 as ready. Getting these wrong is a top cause of cascading restarts, the same way wrong IIS app-pool ping settings used to crash apps under load. A ResponseWriter keeps the bodies identical in every language, so each stack serves the same paths and JSON; the package is Microsoft.Extensions.Diagnostics.HealthChecks.EntityFrameworkCore.")],
    "notes follow the health-check code")

# ---------------------------------------------------------------- 31: CQRS projection
replace(31, "// Projection — a Confluent.Kafka consumer, idempotent upsert into the read model",
        "// Projection — a BackgroundService on Confluent.Kafka, idempotent upsert", "projection runs as a BackgroundService (examples/05, 11)")
replace(31, "var cr = consumer.Consume(ct);", "var cr = consumer.Consume(stoppingToken);   // in ExecuteAsync", "host-owned cancellation token")
replace(31, "await reads.UpsertAsync(summary, ct); ", "await reads.UpsertAsync(summary, stoppingToken);", "host-owned cancellation token")
notes(31, [("The projection is a Confluent.Kafka consumer loop.", "The projection is a BackgroundService that runs a Confluent.Kafka consumer loop; the host cancels its stoppingToken on shutdown.")],
      "projection is a BackgroundService")

# ---------------------------------------------------------------- 34: outbox (example 04)
set_code(34, [
    "// POST /orders (excerpt), examples/04-data/dotnet: EF Core + Debezium CDC, the .NET outbox.",
    "// For WCF/COM+ refugees: this replaces the MSDTC two-phase commit you used",
    "// to make 'save the order and queue the event' atomic across databases.",
    "app.MapPost(\"/orders\", async (OrderRequest request, OrdersContext db) =>",
    "{",
    "    var order = new Order { Id = Guid.NewGuid().ToString(), Sku = request.Sku,",
    "                            Quantity = request.Quantity, Status = \"confirmed\" };",
    "    var dto = OrderDto.From(order);",
    "    db.Orders.Add(order);                         // state change",
    "    db.Outbox.Add(new OutboxEvent                 // same SaveChanges: outbox row",
    "    {",
    "        AggregateId = order.Id,",
    "        EventType = \"order.placed\",",
    "        Payload = JsonSerializer.SerializeToElement(dto, JsonSerializerOptions.Web),",
    "    });",
    "    await db.SaveChangesAsync();                  // one local txn; Debezium tails the WAL",
    "    return Results.Json(dto, statusCode: StatusCodes.Status201Created);",
    "});",
    "// No Kafka call on the request path: if the broker is down, the order still",
    "// commits and the event ships when the Debezium connector catches up.",
    "// Wolverine (MIT) ships an EF Core transactional outbox if you prefer a framework.",
], "examples/04: order and outbox row added to one DbContext and committed by one SaveChangesAsync")
notes(34, [("write the OutboxEntry entity manually as shown", "write the OutboxEvent entity manually as shown, where one SaveChangesAsync commits the order and the outbox row in a single transaction")],
      "entity name and single-commit wording follow examples/04")

# ---------------------------------------------------------------- 38: consumer as BackgroundService (examples 05, 11)
set_code(38, [
    "// Confluent.Kafka 2.16.0 — the low-level Kafka client (Apache 2.0).",
    "// Auto-commit off, commit after the work: at-least-once processing.",
    "// producer — order-service emits the fact",
    "var producer = new ProducerBuilder<Null, string>(",
    "    new ProducerConfig { BootstrapServers = kafkaBootstrap }).Build();",
    "await producer.ProduceAsync(\"order.placed\",",
    "    new Message<Null, string> { Value = json });     // awaits the broker ack",
    "// consumer — ShipmentWorker : BackgroundService; the host cancels stoppingToken on SIGTERM",
    "using var consumer = new ConsumerBuilder<Ignore, string>(new ConsumerConfig",
    "{",
    "    BootstrapServers = config.GetValue(\"KAFKA_BOOTSTRAP\", \"kafka:9094\"),",
    "    GroupId          = \"shipping-group\",",
    "    AutoOffsetReset  = AutoOffsetReset.Earliest,",
    "    EnableAutoCommit = false,",
    "}).Build();",
    "consumer.Subscribe(\"order.placed\");",
    "while (!stoppingToken.IsCancellationRequested)",
    "{",
    "    var cr = consumer.Consume(stoppingToken);",
    "    await HandleAsync(cr.Message.Value);   // exists? skip; unique index on order_id backs it",
    "    consumer.Commit(cr);                   // ack after — at-least-once",
    "}",
], "examples/05: consumers are BackgroundServices with an idempotent handler")
notes(38, [("In the running example the loop runs in a plain console worker that PosixSignalRegistration cancels on SIGTERM.",
            "In the running example each consumer is a BackgroundService in a Worker SDK host: the host cancels its stoppingToken on SIGTERM, and the handler looks the order up before inserting, with the unique index on order_id as the backstop, so a redelivered record is processed once.")],
      "consumers are hosted services, not console loops")

# ---------------------------------------------------------------- 45: stream processor
replace(45, "// StreamProcessor/Program.cs (excerpt) — Streamiz.Kafka.Net 1.8.2",
        "// StreamProcessor/RevenueStream.cs (excerpt), a BackgroundService — Streamiz.Kafka.Net 1.8.2",
        "examples/06: the processor is a BackgroundService")
replace(45, "StartAsync(cts.Token);", "StartAsync(stoppingToken);", "host-owned cancellation token")
notes(45, [("The processor in the running example keys each order by merchant", "The processor in the running example is a BackgroundService in a Worker SDK host; it keys each order by merchant")],
      "processor is a BackgroundService")

# ---------------------------------------------------------------- 80: valet key config
replace(80, "var valetSecret = Environment.GetEnvironmentVariable(\"VALET_SECRET\")", "var valetSecret = builder.Configuration.GetValue(\"VALET_SECRET\",", "examples/12: IConfiguration instead of Environment")
replace(80, "    ?? \"demo-secret-do-not-use-in-prod\";", "    \"demo-secret-do-not-use-in-prod\");", "examples/12: IConfiguration instead of Environment")
notes(80, [("keyed with VALET_SECRET (HMACSHA256)", "keyed with VALET_SECRET, read through IConfiguration (HMACSHA256)")], "config through IConfiguration")

# ---------------------------------------------------------------- 126: saga
set_code(126, [
    "// SagaEngine.cs (excerpt), examples/17-sagas/dotnet: one durable step per call",
    "static readonly string[] Steps = { \"charge_payment\", \"reserve_stock\", \"book_shipping\" };",
    "public async Task AdvanceAsync(string sagaId, CancellationToken ct = default)",
    "{",
    "    await using var db = await dbFactory.CreateDbContextAsync(ct);",
    "    await using var tx = await db.Database.BeginTransactionAsync(ct);",
    "    var saga = (await db.Sagas.FromSql(                          // pessimistic row lock",
    "        $\"SELECT * FROM sagas WHERE id = {sagaId} FOR UPDATE\")\n        .ToListAsync(ct)).SingleOrDefault();",
    "    if (saga is not { Status: \"RUNNING\" }) { await tx.CommitAsync(ct); return; }  // idempotent",
    "    if (saga.StepIndex >= Steps.Length) saga.Status = \"COMPLETED\";",
    "    else try {",
    "        var step = Steps[saga.StepIndex];",
    "        saga.Context[step] = ExecuteStep(step, saga.Context);   // call the service",
    "        saga.StepIndex++;",
    "    }",
    "    catch (Exception) {",
    "        saga.Status = \"COMPENSATING\";                           // hand off to the unwinder",
    "    }",
    "    await db.SaveChangesAsync(ct);                              // durable after every step",
    "    await tx.CommitAsync(ct);                                   // the caller advances again",
    "}",
], "examples/17: FromSql ... FOR UPDATE inside an EF Core transaction, IDbContextFactory")
notes(126, [(("Recovery needs no special path:", "equivalent of a Windows Service that processed an MSMQ queue."),
    "Recovery needs no special path: Example 17 resumes RUNNING sagas from an IHostedService at startup by calling AdvanceAsync again, and a BackgroundService with PeriodicTimer (or Quartz.NET on a cron) plus DistributedLock does the same continuously, the cloud-native equivalent of a Windows Service that processed an MSMQ queue.")],
      "recovery follows examples/17")

# ---------------------------------------------------------------- 154: hexagonal
set_code(154, [
    "// domain — the core declares the interfaces (ports) it needs; no framework",
    "public interface IOrderRepository { Task SaveAsync(Order order); /* FindByIdAsync, ... */ }",
    "public interface IEventPublisher  { Task PublishAsync(OrderPlaced evt); }",
    "// pure application logic; C# 12 primary constructor — no DI annotations needed",
    "public class PlaceOrderUseCase(IOrderRepository repo, IEventPublisher events)",
    "{",
    "    public async Task<Order> ExecuteAsync(PlaceOrderCmd cmd)",
    "    {",
    "        var order = Order.Create(cmd);                // aggregate enforces invariants",
    "        await repo.SaveAsync(order);",
    "        await events.PublishAsync(new OrderPlaced(order.Id, order.Sku, order.Quantity));",
    "        return order;",
    "    }",
    "}",
    "// driving adapter — REST; the CLI adapter calls the same use case on a plain Host",
    "app.MapPost(\"/orders\", async (PlaceOrderCmd cmd, PlaceOrderUseCase placeOrder) =>",
    "    Results.Json(OrderView.From(await placeOrder.ExecuteAsync(cmd)), statusCode: 201));",
    "// driven adapters (Adapters/): EfOrderRepository : IOrderRepository over an OrdersContext,",
    "//                             LogEventPublisher : IEventPublisher.",
], "examples/19: minimal-API driving adapter, EF Core repository, primary constructors")
notes(154, [("The REST controller is a thin driving adapter", "The minimal-API endpoint is a thin driving adapter"),
            ("The application service PlaceOrder is pure logic", "The application service PlaceOrderUseCase is pure logic"),
            ("(EfCoreOrderRepository for persistence, KafkaEventPublisher on Confluent.Kafka for events) in separate projects", "(EfOrderRepository over an EF Core OrdersContext for persistence, a log publisher in the example and a Kafka publisher on Confluent.Kafka in production) in separate projects")],
      "adapter names follow examples/19")

replace(154, "(EF Core repo, Kafka publisher). Swap or add one without touching PlaceOrder.", "(EF Core repo, log or Kafka publisher). Swap or add one without touching PlaceOrderUseCase.", "caption follows the use case name", cat="code")
# ---------------------------------------------------------------- 172: shutdown (example 21)
replace(172, "One SIGTERM flips readiness; after DRAIN_DELAY_SECONDS, StopApplication() lets Kestrel drain in-flight requests within ShutdownTimeout (20 s).", "One SIGTERM flips readiness; StoppingAsync waits DRAIN_DELAY_SECONDS, then Kestrel drains in-flight requests within ShutdownTimeout (20 s).", "caption follows the code", cat="code")
set_code(172, [
    "// Program.cs and DrainService.cs (excerpt), examples/21-graceful-shutdown/dotnet",
    "// The default ConsoleLifetime turns one SIGTERM into a graceful stop; the drain is a hosted",
    "// service step and HostOptions.ShutdownTimeout bounds the whole stop.",
    "builder.Services.AddSingleton<ShutdownState>();",
    "builder.Services.AddHostedService<DrainService>();",
    "builder.Services.Configure<HostOptions>(o => o.ShutdownTimeout = TimeSpan.FromSeconds(20));",
    "builder.Services.AddHealthChecks().AddCheck<ShutdownHealthCheck>(\"shutdown\", tags: [\"ready\"]);",
    "// GET /readyz answers 503 once ShutdownState.ShuttingDown is set; /healthz stays 200",
    "public sealed class DrainService(ShutdownState state, IConfiguration config,",
    "    ILogger<DrainService> logger) : IHostedLifecycleService",
    "{",
    "    public async Task StoppingAsync(CancellationToken cancellationToken)  // before StopAsync",
    "    {",
    "        state.MarkShuttingDown();                          // 1. readiness fails first",
    "        var delay = TimeSpan.FromSeconds(config.GetValue(\"DRAIN_DELAY_SECONDS\", 5));",
    "        try { await Task.Delay(delay, cancellationToken); }   // 2. serve on: endpoints update",
    "        catch (OperationCanceledException) { }",
    "        logger.LogInformation(\"shutting down HTTP server (in_flight={InFlight})\",\n            state.InFlight);",
    "    }                       // 3. Kestrel stops in StopAsync: no new requests, drains in-flight",
    "    // 4. the DbContext services are disposed with the host; exit 0",
    "}",
], "examples/21: IHostedLifecycleService.StoppingAsync drain on the default ConsoleLifetime")
notes(172, [(("ASP.NET Core's default ConsoleLifetime stops the host as soon as SIGTERM arrives", "inside the 30-second grace period."),
    "ASP.NET Core's default ConsoleLifetime already turns SIGTERM into a graceful stop, so Example 21 keeps it and adds the drain as one more hosted service. DrainService implements IHostedLifecycleService, and the host runs every StoppingAsync before any StopAsync. In StoppingAsync the service flips ShutdownState, so the ShutdownHealthCheck behind /readyz answers 503 and the Service stops routing, then waits DRAIN_DELAY_SECONDS (5 s, read through IConfiguration; it plays the part of a preStop sleep) while the endpoint removal propagates; /healthz stays 200 and Kestrel keeps serving. Kestrel then stops accepting and finishes in-flight requests in its StopAsync, all bounded by HostOptions.ShutdownTimeout (20 s here; the default is 30 s). The host disposes the DbContext services and the process exits 0, inside the 30-second grace period.")],
      "drain is a hosted lifecycle service, not a signal handler")

# ---------------------------------------------------------------- 207, 211: pins and recipe
notes(207, [("Npgsql 10.0.3, Grpc 2.84.0", "EF Core 10.0.12 with Npgsql.EntityFrameworkCore.PostgreSQL 10.0.3, HybridCache 10.10.0, Grpc 2.84.0")], "new pins")
replace(211, "AspNetCore.HealthChecks.NpgSql", "Microsoft.Extensions.Diagnostics.HealthChecks.EntityFrameworkCore", "examples use the first-party EF Core health check")
replace(211, "Map health checks at /healthz and /readyz", "AddHealthChecks with AddDbContextCheck, MapHealthChecks at /healthz and /readyz", "examples use MapHealthChecks")

# ---------------------------------------------------------------- 227..235: caching (example 25)
replace(227, "csharp · ASP.NET Core 10 + EF Core + IDistributedCache", "csharp · ASP.NET Core 10 + EF Core + Redis", "examples/25 cache-aside on a Redis client")
set_code(227, [
    "// Program.cs (excerpt), examples/25-caching/dotnet: cache-aside on a Redis client",
    "app.MapGet(\"/cache-aside/products/{pid}\", async (string pid, CacheContext db) =>",
    "{",
    "    var key = $\"ca:product:{pid}\";",
    "    var cached = await SafeCacheGet(key);                  // 1. cache lookup",
    "    if (cached is not null)",
    "        return Results.Json(Merge(\"cache\", JsonSerializer.Deserialize<JsonElement>(cached)));",
    "    var product = await db.Products.AsNoTracking().Where(p => p.Id == pid)   // 2. DB on a miss",
    "        .Select(p => ProductDto.From(p)).FirstOrDefaultAsync();",
    "    if (product is null) return Results.NotFound(new { error = \"not found\" });",
    "    await SafeCacheSet(key, JsonSerializer.Serialize(product, CacheJson.Options)); // 3. fill",
    "    return Results.Json(Merge(\"db\", product));",
    "});",
    "app.MapPut(\"/cache-aside/products/{pid}\",\n    async (string pid, ProductUpdate update, CacheContext db) =>",
    "{",
    "    await db.Products.Where(p => p.Id == pid).ExecuteUpdateAsync(s => s",
    "        .SetProperty(p => p.Name, update.Name)\n        .SetProperty(p => p.PriceCents, update.PriceCents));",
    "    await SafeCacheDelete($\"ca:product:{pid}\");            // 4. invalidate",
    "    return Results.Json(new { ok = true, pattern = \"cache-aside\", action = \"invalidated\" });",
    "});",
], "examples/25: cache-aside steps on a Redis client with EF Core")
notes(227, [(("Minimal cache-aside in ASP.NET Core.", "so a Redis outage falls back to EF Core and the read still works."),
    "Cache-aside as Example 25 runs it: the handler owns the three steps on a StackExchange.Redis client, because the steps are the lesson. SafeCacheGet and SafeCacheSet swallow Redis failures, so a Redis outage falls back to the EF Core query and the read still works (the verify script stops Redis to prove it). The handler tries the cache first, queries EF Core on a miss, populates the cache with a 60-second TTL and tags the answer with its source. The PUT path updates the row with ExecuteUpdateAsync and then removes the cache entry: invalidate-on-write. IDistributedCache is the Microsoft.Extensions.Caching abstraction behind HybridCache on the read-through slide, which adds typed access and stampede protection.")],
      "cache-aside follows examples/25")

notes(228, [("The .NET BCL doesn't ship a declarative read-through cache, but FusionCache (MIT, open-source) is the modern idiomatic answer — it gives you GetOrSetAsync with a factory function (the loader), built-in stampede protection, fail-safe fallback, and L1+L2 layering (in-memory + Redis).",
             "HybridCache (Microsoft.Extensions.Caching.Hybrid, MIT) is the in-box answer: it gives you GetOrCreateAsync with a factory function (the loader), built-in stampede protection and L1+L2 layering (in-memory plus a distributed cache such as Redis)."),
            ("Alternative for the conservative shop: HybridCache (new in .NET 9, Microsoft-built, similar semantics to FusionCache but Microsoft-supported).",
             "Alternative with more features: FusionCache (MIT, open-source) adds fail-safe stale fallback, eager refresh and a backplane.")],
      "read-through is HybridCache in examples/25")
replace(229, "Read-through in ASP.NET Core with FusionCache", "Read-through in ASP.NET Core with HybridCache", "title follows the example", cat="stack")
replace(229, "csharp · ASP.NET Core 10 + FusionCache (MIT, open-source)", "csharp · ASP.NET Core 10 + HybridCache + Redis (L2)", "chip follows the example")
replace(229, "GetOrSetAsync is read-through. Factory runs only on miss. Built-in stampede protection.", "GetOrCreateAsync is read-through. The loader runs only on a miss. Built-in stampede protection.", "caption follows the code")
set_code(229, [
    "// Program.cs (excerpt), examples/25-caching/dotnet: HybridCache is read-through",
    "// builder.Services.AddStackExchangeRedisCache(o => o.Configuration = redisUrl);   // L2",
    "// builder.Services.AddHybridCache(o => o.DefaultEntryOptions = new HybridCacheEntryOptions",
    "//     { Expiration = TimeSpan.FromSeconds(60), LocalCacheExpiration = TimeSpan.FromSeconds(60) });"[:0] + "//     { Expiration = 60 s, LocalCacheExpiration = 60 s });",
    "app.MapGet(\"/read-through/products/{pid}\",\n    async (string pid, CacheContext db, HybridCache cache) =>",
    "{",
    "    var key = $\"rt:product:{pid}\";",
    "    var source = \"cache\";",
    "    var product = await cache.GetOrCreateAsync<ProductDto?>(key, async ct =>",
    "    {",
    "        source = \"db\";                                     // the loader ran: a miss",
    "        return await db.Products.AsNoTracking().Where(p => p.Id == pid)",
    "            .Select(p => ProductDto.From(p)).FirstOrDefaultAsync(ct);             // loader",
    "    });",
    "    if (product is null) { await cache.RemoveAsync(key); return Results.NotFound(); }",
    "    return Results.Json(Merge(source, product));",
    "});",
    "// A write invalidates both levels: await cache.RemoveAsync(key)",
], "examples/25: HybridCache.GetOrCreateAsync with Redis L2 and a source flag")
notes(229, [(("FusionCache is the modern .NET answer", "the API is slightly different."),
    "HybridCache (Microsoft.Extensions.Caching.Hybrid, MIT) is the in-box answer for declarative read-through caching: a two-level cache with an in-process L1 and any IDistributedCache as L2, here Redis through AddStackExchangeRedisCache. The registration sets a 60-second expiry for both levels. The endpoint calls GetOrCreateAsync with a loader that runs only on a cache miss, and HybridCache's built-in concurrency control ensures that if 100 concurrent requests hit the same missing key, the loader runs once and the other 99 await the result: no thundering herd. The loader also sets a flag, so the response reports source db for the request that loaded the value and cache for the others. A missing product returns null, which the endpoint removes from the cache again so a later insert is visible at once. When Redis is unreachable, HybridCache logs the L2 failure and still runs the loader. The trade against a hand-written cache-aside: a library dependency, in exchange for typed values, serialization and stampede protection. Alternative: FusionCache (MIT) adds fail-safe stale fallback, eager refresh and a backplane for multi-Pod L1 invalidation.")],
      "read-through is HybridCache in examples/25")

replace(231, "csharp · ASP.NET Core 10 + IDistributedCache or FusionCache", "csharp · ASP.NET Core 10 + EF Core + StackExchange.Redis", "examples/25 write-through")
set_code(231, [
    "// Program.cs (excerpt), examples/25-caching/dotnet: write-through, DB first then cache",
    "app.MapPut(\"/write-through/products/{pid}\",\n    async (string pid, ProductUpdate update, CacheContext db) =>",
    "{",
    "    await db.Products.Where(p => p.Id == pid)               // 1. DB first",
    "        .ExecuteUpdateAsync(s => s.SetProperty(p => p.Name, update.Name)",
    "                                  .SetProperty(p => p.PriceCents, update.PriceCents));",
    "    var product = await db.Products.AsNoTracking().Where(p => p.Id == pid)",
    "        .Select(p => ProductDto.From(p)).FirstOrDefaultAsync();",
    "    if (product is not null)                                // 2. cache second: set, not remove",
    "        await SafeCacheSet($\"wt:product:{pid}\",\n            JsonSerializer.Serialize(product, CacheJson.Options));",
    "    return Results.Json(new { ok = true, pattern = \"write-through\", action = \"set\" });",
    "});",
    "// FusionCache flavour — SetAsync writes the value directly.",
    "// L1 (memory) and L2 (Redis) both get updated; backplane invalidates other Pods' L1.",
    "// ... await cache.SetAsync($\"product:{id}\", p, token: ct);",
], "examples/25: write-through on a Redis client")
notes(231, [("The first uses IDistributedCache directly: save EF Core changes, then SetStringAsync to update the cache with the new value",
             "The first is Example 25: update the row through EF Core, read it back, then SET the cache with the new value")],
      "write-through follows examples/25")

replace(233, "csharp · ASP.NET Core 10 + EF Core + IDistributedCache", "csharp · ASP.NET Core 10 + EF Core + Redis", "examples/25 write-around")
set_code(233, [
    "// Program.cs (excerpt), examples/25-caching/dotnet: writes skip the cache; reads cache-aside",
    "app.MapPost(\"/write-around/events\", async (EventRequest request, CacheContext db) =>",
    "{",
    "    db.Events.Add(new EventRecord { Id = request.Id, Type = request.Type,",
    "        Payload = request.Payload ?? JsonSerializer.SerializeToElement(new { }) });",
    "    await db.SaveChangesAsync();                           // DB only, cache untouched",
    "    return Results.Json(new { ok = true, pattern = \"write-around\", action = \"db-only\" });",
    "});",
    "app.MapGet(\"/write-around/events/{eid}\", async (string eid, CacheContext db) =>",
    "{",
    "    var key = $\"wa:event:{eid}\";",
    "    var cached = await SafeCacheGet(key);",
    "    if (cached is not null)",
    "        return Results.Json(Merge(\"cache\", JsonSerializer.Deserialize<JsonElement>(cached)));",
    "    var evt = await db.Events.AsNoTracking().Where(e => e.Id == eid)",
    "        .Select(e => EventDto.From(e)).FirstOrDefaultAsync();",
    "    if (evt is null) return Results.NotFound(new { error = \"not found\" });",
    "    await SafeCacheSet(key, JsonSerializer.Serialize(evt, CacheJson.Options)); // 1st read",
    "    return Results.Json(Merge(\"db\", evt));",
    "});",
], "examples/25: write-around on EF Core and a Redis client")

replace(235, "csharp · ASP.NET Core 10 + StackExchange.Redis + Npgsql", "csharp · ASP.NET Core 10 + StackExchange.Redis + EF Core", "examples/25 write-back")
set_code(235, [
    "// Program.cs and CacheWorkers.cs (excerpt), examples/25-caching/dotnet: write-back",
    "app.MapPut(\"/write-back/metrics/{mid}\", async (string mid, MetricRequest request) =>",
    "{",
    "    // ... HSET metric:<mid> {value, tags}; SADD metric:dirty <mid> (503 when Redis is down)",
    "    return Results.Json(new { ok = true, pattern = \"write-back\", action = \"cached-for-flush\" },",
    "        statusCode: StatusCodes.Status202Accepted);          // 202: queued, not yet durable",
    "});",
    "builder.Services.AddHostedService<MetricFlusher>();      // the flusher, started with the host",
    "// MetricFlusher : BackgroundService, in ExecuteAsync(CancellationToken stoppingToken):",
    "var failures = 0;",
    "while (!stoppingToken.IsCancellationRequested)",
    "{",
    "    await Task.Delay(Math.Min(FlushPeriodMs << failures, MaxFlushBackoffMs), stoppingToken);",
    "    var ids = await db.SetPopAsync(\"metric:dirty\", 100);      // atomic batch dequeue",
    "    if (ids.Length == 0) continue;",
    "    var failed = new List<RedisValue>();  // Upsert: HGETALL, one ExecuteSqlAsync ON CONFLICT",
    "    foreach (var mid in ids)",
    "        try { await Upsert(mid); await db.HashDeleteAsync(\"metric:attempts\", mid); }",
    "        catch (Exception ex)\n        { logger.LogError(ex, \"flush failed for {Id}\", (string?)mid); failed.Add(mid); }",
    "    if (failed.Count == 0) { failures = 0; continue; }",
    "    failures = Math.Min(failures + 1, 3);                    // back off: 2 s, 4 s, 8 s",
    "    await Requeue(db, failed);   // HINCRBY metric:attempts: dirty again, failed after 5",
    "}",
], "examples/25: the flusher is a BackgroundService; the upsert is one ExecuteSqlAsync")
notes(235, [("The flusher is a background loop started with the app (a BackgroundService works the same way) that SPOPs up to 100 dirty ids at once.",
             "The flusher is a BackgroundService registered with AddHostedService, so the host starts it and cancels it on shutdown; each cycle SPOPs up to 100 dirty ids at once."),
            ("Each id is upserted with INSERT ... ON CONFLICT (id) DO UPDATE,", "Each id is upserted with one ExecuteSqlAsync statement, INSERT ... ON CONFLICT (id) DO UPDATE,")],
      "write-back follows examples/25")

# ---------------------------------------------------------------- 259: Appendix M shutdown
set_code(259, [
    "// OrderService (excerpt, example 21): the default ConsoleLifetime plus one hosted service",
    "builder.Services.AddSingleton<ShutdownState>();",
    "builder.Services.AddHostedService<DrainService>();     // StoppingAsync runs first",
    "builder.Services.Configure<HostOptions>(o => o.ShutdownTimeout = TimeSpan.FromSeconds(20));",
    "builder.Services.AddHealthChecks()",
    "    .AddCheck<ShutdownHealthCheck>(\"shutdown\", tags: [\"ready\"])     // 503 once draining",
    "    .AddDbContextCheck<OrdersContext>(\"database\", tags: [\"ready\"]);",
    "// DrainService.StoppingAsync, on the single SIGTERM:",
    "state.MarkShuttingDown();                  // 1. readiness → 503: the Service stops routing",
    "await Task.Delay(delay, cancellationToken);           // 2. endpoints update (5 s)",
    "// 3. Kestrel stops in StopAsync and drains in-flight (ShutdownTimeout 20 s)",
    "app.MapHealthChecks(\"/healthz\", ...);                // liveness stays 200",
    "app.MapHealthChecks(\"/readyz\", ...);                 // ready tag: shutdown + database",
    "app.MapPost(\"/orders\", async (OrderRequest request, OrdersContext db, ShutdownState state) =>",
    "{",
    "    if (state.ShuttingDown)\n        return Results.Json(new { error = \"shutting down\" }, statusCode: 503);",
    "    // ... in-flight requests finish before the host stops; 4. the context is disposed, exit 0",
    "});",
], "examples/21: hosted-service drain")
notes(259, [(("PosixSignalRegistration catches the single SIGTERM", "winding down."),
    "The default ConsoleLifetime turns the single SIGTERM into a graceful stop, and DrainService, a hosted service, runs first: its StoppingAsync flips a flag so /readyz answers 503 and Kubernetes takes the Pod out of the Service, while /healthz stays 200 so the kubelet does not restart a Pod that is winding down."),
            (("After DRAIN_DELAY_SECONDS the handler calls StopApplication():", "inside terminationGracePeriodSeconds."),
    "After DRAIN_DELAY_SECONDS StoppingAsync returns and Kestrel stops accepting and finishes in-flight requests within HostOptions.ShutdownTimeout (20 s), the host disposes its services and the process exits 0, inside terminationGracePeriodSeconds.")],
      "drain is a hosted lifecycle service")

if ERR:
    for e in ERR: print("TOO LONG", e)
    sys.exit(1)
OUT.write_text(json.dumps({"ops": ops}, indent=1, ensure_ascii=False) + "\n")
print("wrote", OUT, len(ops), "ops")
