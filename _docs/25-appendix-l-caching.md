---
title: "Caching Patterns"
marker: "L"
label: "Appendix L"
order: 25
part: "Deep-dive appendices"
description: "Six standard caching patterns — cache-aside, read-through, write-through, write-around, write-back, and refresh-ahead — each with its consistency story, its failure mode, and when to reach for it; plus the anti-patterns and a decision guide."
duration: 24 minutes
---

Caching is the highest-leverage performance tool you have and the easiest to get subtly
wrong. The six patterns in this appendix all use the same pieces — an application, a cache
(Redis here), and a database — and differ in exactly two things: *who does the work* and
*what consistency story you get*. The discipline is to pick the pattern that matches the
consistency you actually need and the read/write profile you actually have, not the one
that sounds best. Every pattern here also adds an invalidation story and a failure-mode
story, so the appendix ends on the anti-patterns and a decision guide for mixing them.

## Five things a cache earns you

A cache is worth its complexity for five concrete reasons. **Application performance** — a
cache hit is microseconds where a database round trip is milliseconds, so the hot path gets
roughly 100× faster on hits. **Backend load** — caching shields the database from repeated
reads of unchanged data, offloading 80–95% of queries on read-heavy workloads with a sensible
TTL. **Throughput** — the same Pod fleet serves far more requests because it spends less time
waiting on the database. **Predictable performance** — p99 latency stops tracking database
load, because the hot path no longer contends on the same lock-bound resource as everyone
else. And **database cost** — fewer queries means smaller or fewer DB instances, a smaller
IOPS budget, and less replication bandwidth; the cache tier is almost always cheaper than the
DB tier it offloads. The trade-off, in one line: every cache adds a consistency story, an
invalidation story, and a failure-mode story — so pick the pattern that matches what you need.

## Cache-aside (look-aside) — the default

Cache-aside is where everyone starts and the right choice for most reads: the application is
in charge. Try the cache; on a miss, read the database, populate the cache on the way back,
and return. It is explicit, debuggable, and has no magic — the cache is just a key-value store
and the app decides what to cache and when. The costs are that every read carries the if/else,
a miss costs two round trips, and the logic repeats across services unless you extract it. The
TTL is the consistency knob: longer means fewer DB hits and more stale-read risk. The one
discipline that keeps it correct is invalidating on writes.

{% include excalidraw.html
   file="24-cache-aside"
   alt="A client calls the application, which reads the cache (GET), falls back to the database with a SELECT on a miss, then populates the cache with SETEX before returning. The application coordinates every step."
   caption="Figure L.1 — Cache-aside: the application coordinates; a miss costs two round trips" %}

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// Spring Web + Spring Data JPA + Spring Data Redis — explicit cache-aside.
@RestController
@RequestMapping("/products")
public class ProductController {
    private static final Duration TTL = Duration.ofSeconds(60);
    private final ProductRepository repo;
    private final RedisTemplate<String, Product> cache;

    public ProductController(ProductRepository repo,
                             RedisTemplate<String, Product> cache) {
        this.repo = repo; this.cache = cache;
    }

    @GetMapping("/{id}")
    public Product get(@PathVariable String id) {
        String key = "product:" + id;
        Product cached = cache.opsForValue().get(key);            // 1. cache lookup
        if (cached != null) return cached;                        //    hit
        Product p = repo.findById(id)                             // 2. DB on miss
            .orElseThrow(() -> new ResponseStatusException(NOT_FOUND));
        cache.opsForValue().set(key, p, TTL);                     // 3. populate
        return p;
    }

    @PutMapping("/{id}")
    @Transactional
    public Product update(@PathVariable String id, @RequestBody Product body) {
        Product p = repo.findById(id).orElseThrow();
        p.update(body);
        cache.delete("product:" + id);                            // 4. invalidate on write
        return repo.save(p);
    }
}
```

```java
// Quarkus REST + Panache + quarkus-redis-client (blocking ValueCommands).
@Path("/products")
public class ProductResource {
    private static final int TTL_S = 60;
    private final ValueCommands<String, Product> cache;

    public ProductResource(RedisDataSource redis) {
        this.cache = redis.value(Product.class);
    }

    @GET @Path("/{id}")
    public Product get(String id) {
        String key = "product:" + id;
        Product cached = cache.get(key);                  // 1. cache lookup
        if (cached != null) return cached;                //    hit
        Product p = Product.findById(id);                 // 2. DB on miss (Panache)
        if (p == null) throw new WebApplicationException(404);
        cache.setex(key, TTL_S, p);                       // 3. populate
        return p;
    }

    @PUT @Path("/{id}") @Transactional
    public Product update(String id, Product body) {
        Product p = Product.findById(id);
        p.update(body);
        cache.del("product:" + id);                       // 4. invalidate on write
        return p;
    }
}
```

```csharp
// ASP.NET Core + EF Core + IDistributedCache (Redis-backed).
[ApiController, Route("products")]
public class ProductsController(ShopDb db, IDistributedCache cache) : ControllerBase
{
    private static readonly DistributedCacheEntryOptions TTL =
        new() { AbsoluteExpirationRelativeToNow = TimeSpan.FromSeconds(60) };

    [HttpGet("{id}")]
    public async Task<ActionResult<Product>> Get(string id, CancellationToken ct)
    {
        var key = $"product:{id}";
        var cached = await cache.GetStringAsync(key, ct);              // 1. cache lookup
        if (cached is not null)
            return Ok(JsonSerializer.Deserialize<Product>(cached));    //    hit

        var p = await db.Products.FindAsync([id], ct);                 // 2. DB on miss
        if (p is null) return NotFound();
        await cache.SetStringAsync(key,                                // 3. populate
            JsonSerializer.Serialize(p), TTL, ct);
        return Ok(p);
    }

    [HttpPut("{id}")]
    public async Task<ActionResult<Product>> Update(
        string id, Product body, CancellationToken ct)
    {
        var p = await db.Products.FindAsync([id], ct);
        if (p is null) return NotFound();
        p.Update(body);
        await db.SaveChangesAsync(ct);
        await cache.RemoveAsync($"product:{id}", ct);                  // 4. invalidate
        return Ok(p);
    }
}
```

```python
from redis.asyncio import Redis
from fastapi import FastAPI, HTTPException
import json

app   = FastAPI()
cache = Redis.from_url("redis://redis:6379")           # connection pool
TTL   = 60                                              # seconds

@app.get("/products/{pid}")
async def get_product(pid: str):
    key = f"product:{pid}"
    if cached := await cache.get(key):                  # 1. cache lookup
        return json.loads(cached)                       #    hit

    product = await db.fetch_one(                       # 2. DB on miss
        "SELECT id, name, price_cents FROM products WHERE id = $1", pid)
    if not product:
        raise HTTPException(404)
    await cache.setex(key, TTL, json.dumps(dict(product)))  # 3. populate
    return dict(product)

@app.put("/products/{pid}")
async def update_product(pid: str, body: dict):
    await db.execute("UPDATE products SET name=$1, price_cents=$2 WHERE id=$3",
                     body["name"], body["price_cents"], pid)
    await cache.delete(f"product:{pid}")                # 4. invalidate on write
    return {"ok": True}
```

```cpp
{% raw %}// Cache-aside with sw/redis++ + libpq.
#include <sw/redis++/redis++.h>
constexpr int TTL = 60;                       // seconds

Task<> Products::get(HttpRequestPtr req, auto cb, std::string pid) {
  auto key = "product:" + pid;
  if (auto cached = cache_.get(key)) {        // 1. lookup
    cb(json_response(*cached)); co_return;    //    hit
  }
  PgConn conn = co_await pg_.acquire();
  auto row = conn.exec_params(                // 2. miss → DB
    "SELECT id, name, price_cents FROM products WHERE id = $1", pid);
  if (row.empty()) throw HttpException{404};
  auto body = to_json(row).dump();
  cache_.setex(key, TTL, body);               // 3. populate
  cb(json_response(body));
}

Task<> Products::update(HttpRequestPtr req, auto cb, std::string pid) {
  auto body = req->bodyJson();
  PgConn conn = co_await pg_.acquire();
  conn.exec_params("UPDATE products SET name=$1, price_cents=$2 WHERE id=$3",
                   body["name"], body["price_cents"], pid);
  cache_.del("product:" + pid);               // 4. invalidate
  cb(json_response({{"ok", true}}));
}{% endraw %}
```

```go
// cache-aside with go-redis + pgx
const ttl = 60 * time.Second

func (s *Server) getProduct(w http.ResponseWriter, r *http.Request) {
	pid := r.PathValue("pid")
	key := "product:" + pid
	if cached, err := s.cache.Get(r.Context(), key).Bytes(); err == nil { // 1. lookup
		writeRaw(w, cached) // hit
		return
	}
	var p Product
	err := s.pool.QueryRow(r.Context(), // 2. miss → DB
		"SELECT id, name, price_cents FROM products WHERE id=$1", pid).
		Scan(&p.ID, &p.Name, &p.PriceCents)
	if errors.Is(err, pgx.ErrNoRows) {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	body, _ := json.Marshal(p)
	s.cache.Set(r.Context(), key, body, ttl) // 3. populate
	writeRaw(w, body)
}

func (s *Server) updateProduct(w http.ResponseWriter, r *http.Request) {
	pid := r.PathValue("pid")
	var b Product
	_ = json.NewDecoder(r.Body).Decode(&b)
	s.pool.Exec(r.Context(),
		"UPDATE products SET name=$1, price_cents=$2 WHERE id=$3", b.Name, b.PriceCents, pid)
	s.cache.Del(r.Context(), "product:"+pid) // 4. invalidate on write
	writeJSON(w, http.StatusOK, map[string]any{"ok": true})
}
```

## Read-through — the cache fetches on miss

Read-through moves the database call from the application into the cache layer: the app calls
`cache.get()` and gets the value back, not knowing or caring whether the cache had it or had to
fetch it. The semantics are identical to cache-aside; the win is cleaner code with a single read
interface and no if/else in every caller. The cost is less control over what triggers a DB hit,
and you need a cache library that supports loaders. The platform frameworks supply this
declaratively (Spring's `@Cacheable`, Quarkus's `@CacheResult`, .NET FusionCache's
`GetOrSetAsync`); with the raw Redis clients you wrap it yourself.

{% include excalidraw.html
   file="24-read-through"
   alt="A client calls the application, which calls cache.get on a single interface. On a miss the cache itself runs a loader against the database. The application never sees the database directly."
   caption="Figure L.2 — Read-through: the cache library owns the miss; the app sees one interface" %}

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// Spring Cache abstraction with Redis backing.
@Configuration
@EnableCaching
public class CacheConfig {
    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory cf) {
        return RedisCacheManager.builder(cf)
            .cacheDefaults(RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofSeconds(60))
                .serializeValuesWith(SerializationPair.fromSerializer(
                    new GenericJackson2JsonRedisSerializer())))
            .build();
    }
}

@Service
public class ProductService {
    private final ProductRepository repo;
    public ProductService(ProductRepository repo) { this.repo = repo; }

    @Cacheable(value = "products", key = "#id")           // ← cache-then-load
    public Product findById(String id) {
        return repo.findById(id)                          // method body = loader
            .orElseThrow(() -> new ResponseStatusException(NOT_FOUND));
    }

    @CacheEvict(value = "products", key = "#id")
    @Transactional
    public Product update(String id, Product body) {
        Product p = repo.findById(id).orElseThrow();
        p.update(body);
        return repo.save(p);
    }
}
```

```java
// Quarkus Cache annotations give read-through semantics declaratively.
// quarkus-cache + quarkus-redis-cache; loader = the method body.
@ApplicationScoped
public class ProductService {

    @CacheResult(cacheName = "product-cache")     // runs only on a miss
    public Product findById(String id) {
        Product p = Product.findById(id);          // Panache
        if (p == null) throw new WebApplicationException(404);
        return p;
    }

    @CacheInvalidate(cacheName = "product-cache")
    @Transactional
    public Product update(String id, Product body) {
        Product p = Product.findById(id);
        p.update(body);
        return p;
    }
}

@Path("/products")
public class ProductResource {
    @Inject ProductService products;

    @GET @Path("/{id}")
    public Product get(String id) {
        return products.findById(id);              // no if/else; cache invisible
    }
}
// application.properties:
//   quarkus.cache.type=redis
//   quarkus.cache.redis.product-cache.expire-after-write=60S
```

```csharp
// FusionCache (MIT): GetOrSetAsync IS read-through, with built-in stampede
// protection — concurrent misses for one key invoke the factory ONCE.
// Program.cs:
//   builder.Services.AddFusionCache()
//       .WithSerializer(new FusionCacheSystemTextJsonSerializer())
//       .WithDistributedCache(sp => sp.GetRequiredService<IDistributedCache>())
//       .WithDefaultEntryOptions(o => o.Duration = TimeSpan.FromSeconds(60)
//                                      .SetFailSafe(true, TimeSpan.FromMinutes(5)));
[ApiController, Route("products")]
public class ProductsController(ShopDb db, IFusionCache cache) : ControllerBase
{
    [HttpGet("{id}")]
    public async Task<ActionResult<Product>> Get(string id, CancellationToken ct)
    {
        var product = await cache.GetOrSetAsync<Product>(
            $"product:{id}",
            async token => await db.Products.FindAsync([id], token),     // loader
            token: ct);
        return product is null ? NotFound() : Ok(product);
    }

    [HttpPut("{id}")]
    public async Task<ActionResult<Product>> Update(
        string id, Product body, CancellationToken ct)
    {
        var p = await db.Products.FindAsync([id], ct);
        if (p is null) return NotFound();
        p.Update(body);
        await db.SaveChangesAsync(ct);
        await cache.RemoveAsync($"product:{id}", token: ct);             // invalidate
        return Ok(p);
    }
}
```

```python
# Wrap Redis with a loader. Callers call get(); the wrapper does lookup,
# DB fetch on miss, and populate.
from redis.asyncio import Redis
from typing import Callable, Awaitable, Optional
import json

class ReadThrough:
    def __init__(self, redis: Redis, loader: Callable[[str], Awaitable[dict]],
                 ttl: int = 60, prefix: str = ""):
        self.redis, self.loader, self.ttl, self.prefix = redis, loader, ttl, prefix

    async def get(self, id: str) -> Optional[dict]:
        key = f"{self.prefix}{id}"
        if cached := await self.redis.get(key):
            return json.loads(cached)         # hit
        value = await self.loader(id)         # miss → loader fetches from DB
        if value is not None:
            await self.redis.setex(key, self.ttl, json.dumps(value))
        return value

products = ReadThrough(                       # wire once at startup
    redis  = Redis.from_url("redis://redis:6379"),
    loader = lambda pid: db.fetch_one("SELECT * FROM products WHERE id=$1", pid),
    ttl    = 60, prefix = "product:",
)

@app.get("/products/{pid}")
async def get_product(pid: str):
    return await products.get(pid)            # one interface; no if/else
```

```cpp
// Read-through wrapper. Caller calls get(); the template handles the rest.
template <typename T>
class ReadThrough {
  using Loader = std::function<Task<std::optional<T>>(const std::string&)>;
  sw::redis::Redis& redis_;
  Loader loader_;
  int ttl_;
  std::string prefix_;
 public:
  ReadThrough(sw::redis::Redis& r, Loader l, int ttl, std::string p)
    : redis_(r), loader_(std::move(l)), ttl_(ttl), prefix_(std::move(p)) {}

  Task<std::optional<T>> get(const std::string& id) {
    auto key = prefix_ + id;
    if (auto hit = redis_.get(key))           // cache hit
      co_return T::from_json(json::parse(*hit));
    auto value = co_await loader_(id);        // miss → loader
    if (value)
      redis_.setex(key, ttl_, value->to_json().dump());
    co_return value;
  }
};
// Wire once at startup — callers don't see Redis directly:
ReadThrough<Product> products{ redis_, &load_product_from_db, 60, "product:" };

Task<> Products::get(HttpRequestPtr req, auto cb, std::string pid) {
  auto p = co_await products.get(pid);
  cb(p ? json_response(*p) : not_found());
}
```

```go
// read-through wrapper via generics; callers call Get(), never see Redis
type ReadThrough[T any] struct {
	redis  *redis.Client
	loader func(context.Context, string) (T, bool, error)
	ttl    time.Duration
	prefix string
}

func (rt ReadThrough[T]) Get(ctx context.Context, id string) (T, bool, error) {
	var zero T
	key := rt.prefix + id
	if b, err := rt.redis.Get(ctx, key).Bytes(); err == nil { // hit
		var v T
		return v, true, json.Unmarshal(b, &v)
	}
	v, ok, err := rt.loader(ctx, id) // miss → loader fetches from DB
	if err != nil || !ok {
		return zero, ok, err
	}
	b, _ := json.Marshal(v)
	rt.redis.Set(ctx, key, b, rt.ttl)
	return v, true, nil
}

// wire once at startup — callers don't see Redis directly
var products = ReadThrough[Product]{
	redis: rdb, loader: loadProductFromDB, ttl: 60 * time.Second, prefix: "product:",
}
```

## Write-through — cache and DB written synchronously

When stale reads after a write are not acceptable, write-through updates both stores on the write
path: write the database, then write the cache, before the response returns. A read immediately
after a write sees the new value, and the cache is never stale for the writer. The costs are that
write latency is the sum of both stores, and there is no two-phase commit — so the discipline is to
write the DB first (the source of truth), write the cache second with a `SET` rather than an
invalidate, and pair it with a short TTL so any window of inconsistency self-heals. The platform
frameworks express it as `@CachePut` (Spring) or a direct `SetAsync` (FusionCache).

{% include excalidraw.html
   file="24-write-through"
   alt="A client sends a write to the application, which writes the database first as the source of truth, then writes (SET) the cache second, before responding. Both stores are updated on the write path."
   caption="Figure L.3 — Write-through: DB first, cache second (SET, not invalidate); never stale, pays both latencies" %}

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// Spring Cache: @CachePut runs the method body AND writes the return to cache.
@Service
public class ProductService {
    private final ProductRepository repo;
    public ProductService(ProductRepository repo) { this.repo = repo; }

    @CachePut(value = "products", key = "#id")            // ← write-through
    @Transactional
    public Product update(String id, Product body) {
        Product p = repo.findById(id).orElseThrow();
        p.update(body);
        return repo.save(p);                              // saved + cached
    }
}

// Explicit alternative — write the cache only after the DB commit:
@Service
public class ProductServiceExplicit {
    private final ProductRepository repo;
    private final RedisTemplate<String, Product> cache;

    @Transactional
    public Product update(String id, Product body) {
        Product p = repo.findById(id).orElseThrow();
        p.update(body);
        return repo.save(p);
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void cacheAfterCommit(ProductUpdatedEvent ev) {
        cache.opsForValue().set("product:" + ev.product().id(),
                                ev.product(), Duration.ofSeconds(60));
    }
}
```

```java
// Quarkus blocking: write the DB first, SET the cache second.
@Path("/products")
public class ProductResource {
    private final ValueCommands<String, Product> cache;
    public ProductResource(RedisDataSource redis) {
        this.cache = redis.value(Product.class);
    }

    @PUT @Path("/{id}") @Transactional
    public Product update(String id, Product body) {
        Product p = Product.findById(id);          // 1. DB first (source of truth)
        p.update(body);
        cache.setex("product:" + id, 60, p);       // 2. cache second — SET, not invalidate
        return p;
    }
}
```

```csharp
// Explicit IDistributedCache write-through: DB first, cache SET second.
[ApiController, Route("products")]
public class ProductsController(ShopDb db, IDistributedCache cache) : ControllerBase
{
    private static readonly DistributedCacheEntryOptions TTL =
        new() { AbsoluteExpirationRelativeToNow = TimeSpan.FromSeconds(60) };

    [HttpPut("{id}")]
    public async Task<ActionResult<Product>> Update(
        string id, Product body, CancellationToken ct)
    {
        var p = await db.Products.FindAsync([id], ct);
        if (p is null) return NotFound();
        p.Update(body);
        await db.SaveChangesAsync(ct);                                 // 1. DB first
        await cache.SetStringAsync($"product:{id}",                    // 2. cache second
            JsonSerializer.Serialize(p), TTL, ct);                     //    SET, not REMOVE
        return Ok(p);
    }
}

// FusionCache flavour — SetAsync updates L1 (memory) + L2 (Redis) and the
// backplane invalidates other Pods' L1:
//   await cache.SetAsync($"product:{id}", p, token: ct);
```

```python
@app.put("/products/{pid}")
async def update_product(pid: str, body: dict):
    key = f"product:{pid}"
    # 1. write the DB first — it's the source of truth
    await db.execute("UPDATE products SET name=$1, price_cents=$2 WHERE id=$3",
                     body["name"], body["price_cents"], pid)
    # 2. write the cache second — set, don't invalidate
    updated = await db.fetch_one("SELECT * FROM products WHERE id=$1", pid)
    await cache.setex(key, TTL, json.dumps(dict(updated)))
    return {"ok": True}
```

```cpp
{% raw %}Task<> Products::update(HttpRequestPtr req, auto cb, std::string pid) {
  auto body = req->bodyJson();
  auto key  = "product:" + pid;
  PgTxn txn = co_await pg_.begin();
  // 1. write the DB first — it's the source of truth
  txn.exec_params("UPDATE products SET name=$1, price_cents=$2 WHERE id=$3",
                  body["name"], body["price_cents"], pid);
  auto updated = txn.fetch_one(
    "SELECT id, name, price_cents FROM products WHERE id=$1", pid);
  co_await txn.commit();
  // 2. write the cache second — set, don't invalidate
  cache_.setex(key, TTL, to_json(updated).dump());
  cb(json_response({{"ok", true}}));
}{% endraw %}
```

```go
func (s *Server) updateProduct(w http.ResponseWriter, r *http.Request) {
	pid := r.PathValue("pid")
	var b Product
	_ = json.NewDecoder(r.Body).Decode(&b)
	key := "product:" + pid
	// 1. write the DB first — it's the source of truth
	s.pool.Exec(r.Context(),
		"UPDATE products SET name=$1, price_cents=$2 WHERE id=$3", b.Name, b.PriceCents, pid)
	var updated Product
	s.pool.QueryRow(r.Context(),
		"SELECT id, name, price_cents FROM products WHERE id=$1", pid).
		Scan(&updated.ID, &updated.Name, &updated.PriceCents)
	// 2. write the cache second — set, don't invalidate
	body, _ := json.Marshal(updated)
	s.cache.Set(r.Context(), key, body, ttl)
	writeJSON(w, http.StatusOK, map[string]any{"ok": true})
}
```

## Write-around — writes skip the cache

When data is written far more often than it is read — audit logs, event records, telemetry — caching
every write is wasteful, because most entries expire before anyone reads them. Write-around writes
the database and leaves the cache alone; the next reader pays the miss and populates it. The cache
then holds only things actually being read, with no pollution by write-only data. The cost is that
the first read after every write is slow, so you pair write-around on the write side with cache-aside
or read-through on the read side. It is the right pattern for any append-heavy or mostly-written
workload.

{% include excalidraw.html
   file="24-write-around"
   alt="A client sends a write to the application, which writes only the database; the cache is untouched. A later read populates the cache lazily."
   caption="Figure L.4 — Write-around: writes go to the DB only; the next read populates the cache" %}

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// Append-heavy data: events, audit logs, telemetry. Writes hit the DB only.
@RestController
@RequestMapping("/events")
public class EventController {
    private final EventRepository repo;
    public EventController(EventRepository repo) { this.repo = repo; }

    @PostMapping
    @Transactional
    public Event record(@RequestBody Event body) {
        return repo.save(body);                              // DB only — cache untouched
    }

    @GetMapping("/{id}")
    @Cacheable(value = "events", key = "#id")               // read side populates lazily
    public Event get(@PathVariable String id) {
        return repo.findById(id)
            .orElseThrow(() -> new ResponseStatusException(NOT_FOUND));
    }
}
```

```java
// Quarkus blocking: write the DB only; read side is cache-aside.
@Path("/events")
public class EventResource {
    private final ValueCommands<String, Event> cache;
    public EventResource(RedisDataSource redis) {
        this.cache = redis.value(Event.class);
    }

    @POST @Transactional
    public Response record(Event body) {
        body.persist();                                     // DB only — cache untouched
        return Response.created(URI.create("/events/" + body.id)).entity(body).build();
    }

    @GET @Path("/{id}")
    public Event get(String id) {
        String key = "event:" + id;
        Event cached = cache.get(key);                      // standard cache-aside read
        if (cached != null) return cached;
        Event e = Event.findById(id);
        if (e == null) throw new WebApplicationException(404);
        cache.setex(key, 60, e);
        return e;
    }
}
```

```csharp
// Append-heavy data: writes hit the DB only; reads use cache-aside.
[ApiController, Route("events")]
public class EventsController(ShopDb db, IDistributedCache cache) : ControllerBase
{
    [HttpPost]
    public async Task<ActionResult<Event>> Record(Event body, CancellationToken ct)
    {
        db.Events.Add(body);
        await db.SaveChangesAsync(ct);                       // DB only — cache untouched
        return CreatedAtAction(nameof(Get), new { id = body.Id }, body);
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<Event>> Get(string id, CancellationToken ct)
    {
        var key = $"event:{id}";
        var cached = await cache.GetStringAsync(key, ct);
        if (cached is not null) return Ok(JsonSerializer.Deserialize<Event>(cached));
        var e = await db.Events.FindAsync([id], ct);
        if (e is null) return NotFound();
        await cache.SetStringAsync(key, JsonSerializer.Serialize(e),
            new DistributedCacheEntryOptions {
                AbsoluteExpirationRelativeToNow = TimeSpan.FromSeconds(60) }, ct);
        return Ok(e);
    }
}
```

```python
# Append-heavy data: writes hit the DB only; reads use cache-aside.
@app.post("/events")
async def record_event(body: dict):
    await db.execute(
        "INSERT INTO events (id, type, payload, ts) VALUES ($1, $2, $3, NOW())",
        body["id"], body["type"], json.dumps(body["payload"]))
    # deliberately NOT writing to cache — most events are never read again
    return {"ok": True}

@app.get("/events/{eid}")
async def get_event(eid: str):
    key = f"event:{eid}"                                   # standard cache-aside read
    if cached := await cache.get(key):
        return json.loads(cached)
    row = await db.fetch_one("SELECT * FROM events WHERE id=$1", eid)
    if row is None:
        raise HTTPException(404)
    await cache.setex(key, 60, json.dumps(dict(row)))
    return dict(row)
```

```cpp
{% raw %}// Append-heavy data: events, logs, telemetry. Writes go straight to the DB.
Task<> Events::record(HttpRequestPtr req, auto cb) {
  auto body = req->bodyJson();
  PgTxn txn = co_await pg_.begin();
  txn.exec_params(
    "INSERT INTO events (id, type, payload, ts) VALUES ($1, $2, $3, NOW())",
    body["id"], body["type"], body["payload"].dump());
  co_await txn.commit();
  // deliberately NOT writing to cache — most events are never read again
  cb(json_response({{"ok", true}}));
}

// Read side is standard cache-aside
Task<> Events::get(HttpRequestPtr req, auto cb, std::string eid) {
  auto key = "event:" + eid;
  if (auto hit = cache_.get(key)) { cb(json_response(*hit)); co_return; }
  auto row = co_await pg_.fetch_one("SELECT * FROM events WHERE id=$1", eid);
  if (row.empty()) throw HttpException{404};
  auto body = to_json(row).dump();
  cache_.setex(key, 60, body);
  cb(json_response(body));
}{% endraw %}
```

```go
// append-heavy data: writes hit the DB only; reads use cache-aside
func (s *Server) recordEvent(w http.ResponseWriter, r *http.Request) {
	var b Event
	_ = json.NewDecoder(r.Body).Decode(&b)
	s.pool.Exec(r.Context(),
		"INSERT INTO events (id, type, payload, ts) VALUES ($1, $2, $3, NOW())",
		b.ID, b.Type, b.Payload)
	// deliberately NOT writing to cache — most events are never read again
	writeJSON(w, http.StatusOK, map[string]any{"ok": true})
}

func (s *Server) getEvent(w http.ResponseWriter, r *http.Request) {
	eid := r.PathValue("eid")
	key := "event:" + eid // standard cache-aside read
	if cached, err := s.cache.Get(r.Context(), key).Bytes(); err == nil {
		writeRaw(w, cached)
		return
	}
	var e Event
	err := s.pool.QueryRow(r.Context(), "SELECT * FROM events WHERE id=$1", eid).
		Scan(&e.ID, &e.Type, &e.Payload)
	if errors.Is(err, pgx.ErrNoRows) {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	body, _ := json.Marshal(e)
	s.cache.Set(r.Context(), key, body, 60*time.Second)
	writeRaw(w, body)
}
```

## Write-back (write-behind) — fast writes, eventual durability

Write-back is the fastest-write pattern and the one with the most caveats. The client writes to the
cache and gets an immediate ack — the cache is the source of truth for that window — while a
background flusher drains the cache to the database, batching writes for efficiency. Write latency
equals cache latency (microseconds), which is enormous throughput on write-heavy workloads. The cost
is durability: a cache crash before the flusher catches up loses unflushed writes, so the cache must
be configured for persistence (Redis AOF or RDB) and you must have thought about what "lost the last
few seconds of writes" means for the business. Reserve it for cases where write throughput is the
constraint *and* eventual durability is genuinely acceptable — real-time game state, telemetry with a
downstream aggregator, write-heavy buffering ahead of a slower store.

{% include excalidraw.html
   file="24-write-back"
   alt="A client writes to the application, which writes to the cache and acks immediately. A background flusher drains dirty keys from the cache to the database asynchronously in batches."
   caption="Figure L.5 — Write-back: ack at cache speed; a background flusher persists later — a crash before flush loses unpersisted writes" %}

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// @Scheduled flusher drains a dirty-set to the DB; @SchedulerLock = one node.
@RestController
@RequestMapping("/metrics")
public class MetricController {
    private static final int BATCH = 100;
    private final RedisTemplate<String, Object> cache;
    private final MetricRepository repo;

    public MetricController(RedisTemplate<String, Object> cache, MetricRepository repo) {
        this.cache = cache; this.repo = repo;
    }

    @PutMapping("/{id}")
    public ResponseEntity<Void> write(@PathVariable String id,
                                      @RequestBody Map<String, Object> body) {
        cache.opsForHash().putAll("metric:" + id, body);
        cache.opsForSet().add("metric:dirty", id);    // mark for flush
        return ResponseEntity.accepted().build();      // 202 — microseconds
    }

    @Scheduled(fixedDelay = 1000)                      // every second
    @SchedulerLock(name = "metrics-flush")            // ShedLock: only one node
    public void flush() {
        Set<Object> ids = cache.opsForSet().pop("metric:dirty", BATCH);
        if (ids == null || ids.isEmpty()) return;
        try {
            List<Metric> rows = ids.stream().map(this::loadFromCache)
                .filter(Objects::nonNull).toList();
            repo.saveAll(rows);                        // batch insert
        } catch (DataAccessException e) {
            cache.opsForSet().add("metric:dirty", ids.toArray());  // retry
        }
    }
}
```

```java
// Quarkus blocking: @Scheduled flusher drains the dirty-set to the DB.
@Path("/metrics")
@ApplicationScoped
public class MetricResource {
    private static final int BATCH = 100;
    private final HashCommands<String, String, String> cache;
    private final SetCommands<String, String> dirty;

    public MetricResource(RedisDataSource redis) {
        this.cache = redis.hash(String.class);
        this.dirty = redis.set(String.class);
    }

    @PUT @Path("/{id}")
    public Response write(String id, Map<String, String> body) {
        cache.hset("metric:" + id, body);             // 1. cache only; return now
        dirty.sadd("metric:dirty", id);               // mark for flush
        return Response.accepted().build();            // 202 — microseconds
    }

    @Scheduled(every = "1s") @Transactional            // 2. background flush
    void flush() {
        Set<String> ids = dirty.spop("metric:dirty", BATCH);
        if (ids == null || ids.isEmpty()) return;
        try {
            Metric.persistAll(loadFromCache(ids));     // batch insert
        } catch (Exception e) {
            dirty.sadd("metric:dirty", ids.toArray(new String[0]));  // 3. retry
        }
    }
}
```

```csharp
// BackgroundService flusher; IConnectionMultiplexer gives SPOP for batch dequeue.
[ApiController, Route("metrics")]
public class MetricsController(IConnectionMultiplexer redis) : ControllerBase
{
    [HttpPut("{id}")]
    public async Task<IActionResult> Write(string id, Metric body, CancellationToken ct)
    {
        var r = redis.GetDatabase();
        await r.HashSetAsync($"metric:{id}", body.ToHashEntries());  // 1. Redis only
        await r.SetAddAsync("metric:dirty", id);                     // mark for flush
        return Accepted();                                            // microseconds
    }
}

public class MetricsFlusher(
    IConnectionMultiplexer redis,
    IServiceScopeFactory scopes,                  // EF Core needs a scoped DbContext
    ILogger<MetricsFlusher> log) : BackgroundService
{
    private const int Batch = 100;

    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        var r = redis.GetDatabase();
        while (!ct.IsCancellationRequested)
        {
            var ids = await r.SetPopAsync("metric:dirty", Batch);    // 2. batch dequeue
            if (ids.Length == 0) { await Task.Delay(1000, ct); continue; }
            try
            {
                using var scope = scopes.CreateScope();
                var db = scope.ServiceProvider.GetRequiredService<ShopDb>();
                foreach (var id in ids)
                {
                    var hash = await r.HashGetAllAsync($"metric:{id}");
                    db.Metrics.Add(Metric.FromHash(id!, hash));
                }
                await db.SaveChangesAsync(ct);                       // batch insert
            }
            catch (Exception ex)
            {
                log.LogError(ex, "flush failed; re-marking {Count} dirty", ids.Length);
                await r.SetAddAsync("metric:dirty", ids);            // 3. retry
            }
        }
    }
}
// Program.cs: builder.Services.AddHostedService<MetricsFlusher>();
```

```python
import asyncio, json
from redis.asyncio import Redis

app   = FastAPI()
cache = Redis.from_url("redis://redis:6379")
BATCH, PERIOD_S = 100, 1.0

@app.put("/metrics/{mid}")
async def write_metric(mid: str, body: dict):
    await cache.hset(f"metric:{mid}", mapping=body)   # 1. cache only; return now
    await cache.sadd("metric:dirty", mid)             # mark for flush
    return {"ok": True}                               # fast — microseconds

async def flusher():
    while True:                                       # 2. drain the dirty set to the DB
        await asyncio.sleep(PERIOD_S)
        ids = await cache.spop("metric:dirty", BATCH)
        if not ids: continue
        rows = []
        for mid in ids:
            data = await cache.hgetall(f"metric:{mid}")
            if data: rows.append((mid.decode(), json.dumps(dict(data))))
        if rows:
            try:
                await db.execute_many(
                    "INSERT INTO metrics (id, payload) VALUES ($1, $2)", rows)
            except Exception:                         # 3. on failure, re-mark dirty
                await cache.sadd("metric:dirty", *[m for m, _ in rows])

@app.on_event("startup")
async def start_flusher():
    asyncio.create_task(flusher())
```

```cpp
{% raw %}// Write to cache, return immediately; a jthread flusher drains to the DB.
constexpr int BATCH = 100;
constexpr auto PERIOD = 1s;

Task<> Metrics::write(HttpRequestPtr req, auto cb, std::string mid) {
  auto body = req->bodyJson();
  cache_.hset("metric:" + mid, body_to_map(body));   // to cache
  cache_.sadd("metric:dirty", mid);                  // mark dirty
  cb(json_response({{"ok", true}}));                 // microseconds
}

// Background flusher — std::jthread, exits cleanly on stop_token.
void flusher(std::stop_token st) {
  while (!st.stop_requested()) {
    std::this_thread::sleep_for(PERIOD);
    std::vector<std::string> ids;
    cache_.spop("metric:dirty", BATCH, std::back_inserter(ids));
    if (ids.empty()) continue;
    try {
      PgTxn txn = pg_.begin();
      for (auto& mid : ids) {
        auto data = cache_.hgetall("metric:" + mid);
        txn.exec_params("INSERT INTO metrics VALUES ($1, $2)",
                        mid, to_json(data).dump());
      }
      txn.commit();
    } catch (...) {                                  // retry next cycle
      for (auto& mid : ids) cache_.sadd("metric:dirty", mid);
    }
  }
}
std::jthread flush_thread{flusher, g_stop.get_token()};{% endraw %}
```

```go
// write to cache, return immediately; a goroutine flushes to the DB in batches
const (
	batch  = 100
	period = 1 * time.Second
)

func (s *Server) writeMetric(w http.ResponseWriter, r *http.Request) {
	mid := r.PathValue("mid")
	var body map[string]any
	_ = json.NewDecoder(r.Body).Decode(&body)
	s.cache.HSet(r.Context(), "metric:"+mid, body) // 1. cache only; return now
	s.cache.SAdd(r.Context(), "metric:dirty", mid) // mark for flush
	writeJSON(w, http.StatusOK, map[string]any{"ok": true}) // fast — microseconds
}

// flusher drains the dirty set to the DB; started once, stops on ctx cancel
func (s *Server) flusher(ctx context.Context) {
	t := time.NewTicker(period)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			ids := s.cache.SPopN(ctx, "metric:dirty", batch).Val() // 2. drain
			if len(ids) == 0 {
				continue
			}
			if err := s.persist(ctx, ids); err != nil { // 3. on failure, re-mark dirty
				s.cache.SAdd(ctx, "metric:dirty", toAny(ids)...)
			}
		}
	}
}
```

## Refresh-ahead — keep hot keys warm

Plain cache-aside has a latency cliff: while a key is cached reads are fast, but the instant its TTL
expires the next reader pays the slow DB fetch. For homepage data, top products, or frequently-queried
entities that spike is user-visible. Refresh-ahead pre-empts it: a background task tracks a set of hot
keys and refreshes their values from the database *before* the TTL fires, so users always read warm
cache. The cost is extra DB load for keys that might not be requested again, plus the need to identify
which keys are hot — typically by touching a Redis sorted set on every read. Use it where miss latency
on a small hot set matters more than DB throughput.

{% include excalidraw.html
   file="24-refresh-ahead"
   alt="A client reads through the application from a cache that is always warm. A background refresher tracks hot keys and fetches them from the database before their TTL expires, refreshing the cache so users never hit a cold miss."
   caption="Figure L.6 — Refresh-ahead: a background task re-warms hot keys before TTL, eliminating user-visible cold misses" %}

{% include codetabs.html langs="Spring Boot|Quarkus|.NET|Python|C++|Go" %}

```java
// @Scheduled task refreshes hot keys (a sorted-set, touched at read time) before TTL.
@Service
public class ProductService {
    private static final Duration TTL = Duration.ofSeconds(60);
    private static final long REFRESH_BEFORE_S = 10;
    private final ProductRepository repo;
    private final RedisTemplate<String, Product> cache;
    private final RedisTemplate<String, String> hot;

    public ProductService(ProductRepository repo,
                          RedisTemplate<String, Product> cache,
                          RedisTemplate<String, String> hot) {
        this.repo = repo; this.cache = cache; this.hot = hot;
    }

    public Product findById(String id) {
        hot.opsForZSet().add("product:hot", id, System.currentTimeMillis());  // touch
        Product cached = cache.opsForValue().get("product:" + id);
        if (cached != null) return cached;
        Product p = repo.findById(id).orElseThrow();
        cache.opsForValue().set("product:" + id, p, TTL);
        return p;
    }

    @Scheduled(fixedDelay = 5000)                      // every 5 seconds
    @SchedulerLock(name = "refresh-hot")              // ShedLock: only one node
    public void refreshHot() {
        long cutoff = System.currentTimeMillis() - 5 * 60_000L;
        hot.opsForZSet().removeRangeByScore("product:hot", 0, cutoff);
        Set<String> hotIds = hot.opsForZSet().range("product:hot", 0, -1);
        if (hotIds == null) return;
        for (String id : hotIds) {
            Long ttl = cache.getExpire("product:" + id, TimeUnit.SECONDS);
            if (ttl != null && ttl > 0 && ttl < REFRESH_BEFORE_S)
                repo.findById(id).ifPresent(p ->
                    cache.opsForValue().set("product:" + id, p, TTL));   // refresh
        }
    }
}
```

```java
// Quarkus blocking: @Scheduled refreshes hot keys before TTL.
@ApplicationScoped
public class ProductService {
    private static final int TTL_S = 60, REFRESH_BEFORE_S = 10;
    private final ValueCommands<String, Product> cache;
    private final SortedSetCommands<String, String> hot;
    private final KeyCommands<String> keys;

    public ProductService(RedisDataSource redis) {
        this.cache = redis.value(Product.class);
        this.hot   = redis.sortedSet(String.class);
        this.keys  = redis.key();
    }

    public Product findById(String id) {
        hot.zadd("product:hot", System.currentTimeMillis(), id);   // touch hot-set
        Product cached = cache.get("product:" + id);
        if (cached != null) return cached;
        Product p = Product.findById(id);
        cache.setex("product:" + id, TTL_S, p);
        return p;
    }

    @Scheduled(every = "5s")
    void refreshHot() {
        long cutoff = System.currentTimeMillis() - 5 * 60_000L;
        hot.zremrangebyscore("product:hot", 0, cutoff);
        for (String id : hot.zrange("product:hot", 0, -1)) {
            long ttl = keys.ttl("product:" + id);
            if (ttl > 0 && ttl < REFRESH_BEFORE_S) {               // danger zone
                Product p = Product.findById(id);
                if (p != null) cache.setex("product:" + id, TTL_S, p);  // refresh
            }
        }
    }
}
```

```csharp
// BackgroundService + sorted-set hot-key tracking (or FusionCache eager refresh).
public class ProductService(ShopDb db, IConnectionMultiplexer redis)
{
    private static readonly TimeSpan TTL = TimeSpan.FromSeconds(60);

    public async Task<Product?> FindAsync(string id, CancellationToken ct)
    {
        var r = redis.GetDatabase();
        await r.SortedSetAddAsync("product:hot", id,
            DateTimeOffset.UtcNow.ToUnixTimeMilliseconds());        // touch hot-set
        var cached = await r.StringGetAsync($"product:{id}");
        if (cached.HasValue) return JsonSerializer.Deserialize<Product>(cached!);
        var p = await db.Products.FindAsync([id], ct);
        if (p is null) return null;
        await r.StringSetAsync($"product:{id}", JsonSerializer.Serialize(p), TTL);
        return p;
    }
}

public class HotKeyRefresher(
    IConnectionMultiplexer redis, IServiceScopeFactory scopes) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        var r = redis.GetDatabase();
        while (!ct.IsCancellationRequested)
        {
            await Task.Delay(5000, ct);
            var cutoff = DateTimeOffset.UtcNow.AddMinutes(-5).ToUnixTimeMilliseconds();
            await r.SortedSetRemoveRangeByScoreAsync("product:hot", 0, cutoff);
            var hotIds = await r.SortedSetRangeByRankAsync("product:hot");
            using var scope = scopes.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<ShopDb>();
            foreach (var id in hotIds)
            {
                var ttl = await r.KeyTimeToLiveAsync($"product:{id}");
                if (ttl is { TotalSeconds: > 0 and < 10 })
                {
                    var p = await db.Products.FindAsync([id.ToString()], ct);
                    if (p is not null)
                        await r.StringSetAsync($"product:{id}",
                            JsonSerializer.Serialize(p), TTL);              // refresh
                }
            }
        }
    }
}
// FusionCache alternative: o.SetEagerRefresh(0.8f) — refresh at 80% of TTL elapsed.
```

```python
# Background task refreshes hot keys (a sorted set, touched at read time) before TTL.
TTL_S = 60
REFRESH_BEFORE_S = 10

@app.get("/products/{pid}")
async def get_product(pid: str):
    key = f"product:{pid}"
    await cache.zadd("product:hot", {pid: time.time()})  # touch hot-list
    if cached := await cache.get(key):
        return json.loads(cached)
    row = await db.fetch_one("SELECT * FROM products WHERE id=$1", pid)
    if not row: raise HTTPException(404)
    await cache.setex(key, TTL_S, json.dumps(dict(row)))
    return dict(row)

async def refresher():
    while True:
        await asyncio.sleep(5)
        cutoff = time.time() - 300                       # keys touched in last 5 min
        await cache.zremrangebyscore("product:hot", 0, cutoff)
        for pid_b in await cache.zrange("product:hot", 0, -1):
            pid = pid_b.decode()
            ttl = await cache.ttl(f"product:{pid}")
            if 0 < ttl < REFRESH_BEFORE_S:               # refresh window
                row = await db.fetch_one("SELECT * FROM products WHERE id=$1", pid)
                if row:
                    await cache.setex(f"product:{pid}", TTL_S, json.dumps(dict(row)))

@app.on_event("startup")
async def start_refresher():
    asyncio.create_task(refresher())
```

```cpp
// A jthread refreshes hot keys (a sorted set, touched at read time) before TTL.
constexpr int TTL_S = 60;
constexpr int REFRESH_BEFORE_S = 10;

Task<> Products::get(HttpRequestPtr req, auto cb, std::string pid) {
  auto key = "product:" + pid;
  cache_.zadd("product:hot", pid, now_seconds());  // touch
  if (auto hit = cache_.get(key)) { cb(json_response(*hit)); co_return; }
  auto row = co_await pg_.fetch_one("SELECT * FROM products WHERE id=$1", pid);
  if (row.empty()) throw HttpException{404};
  auto body = to_json(row).dump();
  cache_.setex(key, TTL_S, body);
  cb(json_response(body));
}

void refresher(std::stop_token st) {
  while (!st.stop_requested()) {
    std::this_thread::sleep_for(5s);
    cache_.zremrangebyscore("product:hot", 0, now_seconds() - 300);
    std::vector<std::string> hot;
    cache_.zrange("product:hot", 0, -1, std::back_inserter(hot));
    for (auto& pid : hot) {
      auto ttl = cache_.ttl("product:" + pid);
      if (ttl > 0 && ttl < REFRESH_BEFORE_S) {     // danger zone
        auto row = pg_.fetch_one("SELECT * FROM products WHERE id=$1", pid);
        if (!row.empty())
          cache_.setex("product:" + pid, TTL_S, to_json(row).dump());
      }
    }
  }
}
```

```go
// a goroutine refreshes hot keys (a sorted set, touched at read time) before TTL
const (
	ttlS          = 60 * time.Second
	refreshBefore = 10 * time.Second
)

func (s *Server) getProduct(w http.ResponseWriter, r *http.Request) {
	pid := r.PathValue("pid")
	key := "product:" + pid
	s.cache.ZAdd(r.Context(), "product:hot",
		redis.Z{Score: float64(time.Now().Unix()), Member: pid}) // touch hot-list
	if cached, err := s.cache.Get(r.Context(), key).Bytes(); err == nil {
		writeRaw(w, cached)
		return
	}
	var p Product
	err := s.pool.QueryRow(r.Context(), "SELECT * FROM products WHERE id=$1", pid).
		Scan(&p.ID, &p.Name, &p.PriceCents)
	if errors.Is(err, pgx.ErrNoRows) {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	body, _ := json.Marshal(p)
	s.cache.Set(r.Context(), key, body, ttlS)
	writeRaw(w, body)
}

func (s *Server) refresher(ctx context.Context) {
	t := time.NewTicker(5 * time.Second)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			cutoff := strconv.FormatInt(time.Now().Add(-5*time.Minute).Unix(), 10)
			s.cache.ZRemRangeByScore(ctx, "product:hot", "0", cutoff)
			for _, pid := range s.cache.ZRange(ctx, "product:hot", 0, -1).Val() {
				if d := s.cache.TTL(ctx, "product:"+pid).Val(); d > 0 && d < refreshBefore {
					s.refresh(ctx, pid) // inside the refresh window
				}
			}
		}
	}
}
```

## When NOT to cache, and what to watch for

Caching is a complexity tax, only worth paying when reads genuinely hurt — the cheapest cache is no
cache, so if reads are already fast, don't add one. The failure modes to design against:

- **Don't cache rarely-read data.** Caching write-once-read-never data thrashes the cache and gains
  nothing. Profile read patterns first.
- **Don't cache without a TTL.** An unbounded cache grows until it evicts at random — the worst kind of
  failure, because it is unpredictable. Always set an explicit TTL or a `maxmemory-policy`
  (`allkeys-lru` is the typical default); an unbounded Redis with no eviction policy will OOM-kill
  itself.
- **Avoid cache stampedes (thundering herd).** When a hot key expires and many concurrent readers all
  miss at once, they all hit the database simultaneously and it can tip over. Mitigate with a per-key
  lock in the loader (only one fetches, the rest wait), with refresh-ahead, or by jittering TTLs
  slightly per entry so similar keys don't expire together.
- **Watch cache-aside or write-around without invalidation.** The write goes to the DB but a stale
  cached value can persist for the full TTL — the most common stale-data bug in production. Invalidate
  on every write, or use a shorter TTL.
- **Never treat the cache as the source of truth.** A cache outage must mean slower reads, not data
  loss, so always have a DB fallback path — and test it by stopping Redis in staging.

## Choosing the right caching pattern

The patterns are not mutually exclusive; matching them to read/write profiles is the engineering work.
**Cache-aside** is the default for most reads — explicit control, reads dominating writes.
**Read-through** is the same semantics with cleaner code when you have a loader-capable library.
**Write-through** trades write latency for zero stale-read risk, and fits read-heavy data with
infrequent but consistency-critical writes (financial, healthcare, regulatory). **Write-around** suits
append-heavy workloads — telemetry, events, logs — where re-reads are rare. **Write-back** is the niche
extreme-write-throughput pattern, valid only when eventual durability is acceptable and the cache is
configured for persistence. **Refresh-ahead** is the hot-key pattern, eliminating user-visible misses on
a small identified hot set at the cost of extra DB load on it. Most production systems run cache-aside
for the bulk of traffic, layer refresh-ahead on the hot keys they have identified, and use write-through
only where stale reads are genuinely forbidden — a mix, not a single rule.

### Cross-check it yourself

Prove the two properties that matter: the cache actually offloads the database, and a cache outage
degrades rather than breaks. Put read load on the cache-aside endpoint with `hey` and watch the
database's query counter (Postgres `pg_stat_statements`, or the query log): after the first miss per
key the DB call count should flatten while throughput climbs, and p99 should drop sharply — that is the
offload working. Then, with load still running, **stop Redis**. The correct behaviour is that latency
rises (every read becomes a DB read) but requests still return `200` — if you instead see `5xx`, the
cache is wired as a source of truth rather than an optimisation, which is the one caching mistake you
cannot ship. Finally, for write-through, write a key and immediately read it back: the read must return
the new value with no DB round trip; for write-around, write then read and confirm the first read is a
miss (the DB log shows the `SELECT`) while the second is a hit.

---
*Verification status: unverified — code transcribed and normalised from the source decks, not yet run.
Normalisations applied: all six Quarkus blocks were converted from the decks' reactive Mutiny (`Uni`,
`Reactive*Commands`) to the blocking Redis Data Source and Panache APIs to match the house style and the
other four languages; the .NET read/update paths were corrected from a `?? return` syntax shortcut to an
explicit null check. Worth confirming on a real build: the Spring `@CachePut`/`@Cacheable` serializer
config, the Quarkus blocking `ValueCommands`/`HashCommands`/`SortedSetCommands` signatures and
`@Scheduled` flush semantics, the FusionCache `GetOrSetAsync`/`SetEagerRefresh` options, the
`redis.asyncio` `spop`/`zrange` return decoding, and the sw/redis++ `spop`/`zrange` output-iterator
forms. The ShedLock annotation on the Spring flusher and refresher is required for correctness in a
multi-Pod deployment (one flusher node, not N). The `examples/25-caching/` runner moves it to verified.*
