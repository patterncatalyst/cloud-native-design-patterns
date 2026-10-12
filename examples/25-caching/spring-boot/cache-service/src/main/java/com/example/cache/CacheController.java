package com.example.cache;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.atomic.AtomicBoolean;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cache.Cache;
import org.springframework.cache.CacheManager;
import org.springframework.dao.DataAccessException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import tools.jackson.databind.json.JsonMapper;

@RestController
public class CacheController {

    private static final Logger log = LoggerFactory.getLogger(CacheController.class);

    private final ProductService products;
    private final EventRepository events;
    private final MetricRepository metrics;
    private final SafeRedis cache;
    private final Cache readThroughCache;
    private final JsonMapper mapper;
    private final long ttl;

    public CacheController(ProductService products, EventRepository events, MetricRepository metrics,
                           SafeRedis cache, CacheManager cacheManager, JsonMapper mapper,
                           CacheServiceProperties properties) {
        this.products = products;
        this.events = events;
        this.metrics = metrics;
        this.cache = cache;
        this.readThroughCache = cacheManager.getCache(ReadThroughCacheConfig.PRODUCTS);
        this.mapper = mapper;
        this.ttl = properties.ttlSeconds();
    }

    @GetMapping("/cache-keys")
    public Map<String, Object> cacheKeys() {
        Set<String> keys = cache.scanKeys("*");
        if (keys == null) {
            return Map.of("keys", new TreeSet<>(), "error", "cache unavailable");
        }
        return Map.of("keys", new TreeSet<>(keys));
    }

    // -----------------------------------------------------------------------
    // 1. Cache-aside
    // -----------------------------------------------------------------------

    @GetMapping("/cache-aside/products/{pid}")
    public ResponseEntity<ProductResponse> cacheAsideGet(@PathVariable String pid) {
        return productFromCacheOrDb("ca:product:" + pid, pid);
    }

    @PutMapping("/cache-aside/products/{pid}")
    public Map<String, Object> cacheAsideUpdate(@PathVariable String pid, @RequestBody ProductUpdate body) {
        products.update(pid, body);
        cache.delete("ca:product:" + pid);
        return Map.of("ok", true, "pattern", "cache-aside", "action", "invalidated");
    }

    // -----------------------------------------------------------------------
    // 2. Read-through: Spring's Cache.get(key, loader) owns the miss handling
    // -----------------------------------------------------------------------

    @GetMapping("/read-through/products/{pid}")
    public ResponseEntity<ProductResponse> readThroughGet(@PathVariable String pid) {
        var loaded = new AtomicBoolean();
        ProductView product;
        try {
            product = readThroughCache.get(pid, () -> {
                loaded.set(true);
                return products.find(pid).orElseThrow(() -> new UnknownProduct(pid));
            });
        } catch (Cache.ValueRetrievalException e) {
            if (e.getCause() instanceof UnknownProduct) {
                return ResponseEntity.notFound().build();
            }
            throw e;
        } catch (DataAccessException e) {
            // Redis is down: answer from the database
            log.warn("read-through cache unavailable for product={}: {}", pid, e.getMessage());
            loaded.set(true);
            product = products.find(pid).orElse(null);
            if (product == null) {
                return ResponseEntity.notFound().build();
            }
        }
        return ResponseEntity.ok(product.from(loaded.get() ? "db" : "cache"));
    }

    private static final class UnknownProduct extends RuntimeException {
        UnknownProduct(String pid) {
            super("no product " + pid);
        }
    }

    // -----------------------------------------------------------------------
    // 3. Write-through
    // -----------------------------------------------------------------------

    @GetMapping("/write-through/products/{pid}")
    public ResponseEntity<ProductResponse> writeThroughGet(@PathVariable String pid) {
        return productFromCacheOrDb("wt:product:" + pid, pid);
    }

    @PutMapping("/write-through/products/{pid}")
    public Map<String, Object> writeThroughUpdate(@PathVariable String pid, @RequestBody ProductUpdate body) {
        // Write-through: update the database, then immediately populate the cache
        products.update(pid, body).ifPresent(p -> cache.setex("wt:product:" + pid, toJson(p), ttl));
        return Map.of("ok", true, "pattern", "write-through", "action", "set");
    }

    // -----------------------------------------------------------------------
    // 4. Write-around
    // -----------------------------------------------------------------------

    @PostMapping("/write-around/events")
    public Map<String, Object> writeAroundCreate(@RequestBody EventView body) {
        // Write-around: database only, no cache write
        events.save(new EventRecord(body.id(), body.type(), body.payload() == null ? Map.of() : body.payload()));
        return Map.of("ok", true, "pattern", "write-around", "action", "db-only");
    }

    @GetMapping("/write-around/events/{eid}")
    public ResponseEntity<EventResponse> writeAroundGet(@PathVariable String eid) {
        String key = "wa:event:" + eid;

        String cached = cache.get(key);
        if (cached != null) {
            return ResponseEntity.ok(mapper.readValue(cached, EventView.class).from("cache"));
        }

        Optional<EventView> event = events.findById(eid).map(EventRecord::toView);
        if (event.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        cache.setex(key, toJson(event.get()), ttl);
        return ResponseEntity.ok(event.get().from("db"));
    }

    // -----------------------------------------------------------------------
    // 5. Write-back (write-behind)
    // -----------------------------------------------------------------------

    @PutMapping("/write-back/metrics/{mid}")
    public ResponseEntity<Map<String, Object>> writeBackWrite(
            @PathVariable String mid, @RequestBody Map<String, Object> body) {
        Map<String, String> mapping = new LinkedHashMap<>();
        mapping.put("value", body.get("value").toString());
        mapping.put("tags", toJson(body.get("tags")));

        try {
            cache.hset("metric:" + mid, mapping);
            cache.sadd("metric:dirty", mid);
        } catch (Exception e) {
            return ResponseEntity.status(503)
                    .body(Map.of("error", "cache unavailable"));
        }
        // 202: queued in the cache, not yet durable in Postgres
        return ResponseEntity.accepted().body(Map.of(
                "ok", true,
                "pattern", "write-back",
                "action", "cached-for-flush"));
    }

    @GetMapping("/write-back/metrics/{mid}")
    public ResponseEntity<Map<String, Object>> writeBackGet(@PathVariable String mid) {
        Map<String, String> data = cache.hgetall("metric:" + mid);
        if (!data.isEmpty()) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("source", "cache");
            result.put("id", mid);
            result.putAll(data);
            return ResponseEntity.ok(result);
        }

        return metrics.findById(mid)
                .map(m -> {
                    Map<String, Object> result = new LinkedHashMap<>();
                    result.put("source", "db");
                    result.put("id", m.getId());
                    result.put("payload", m.getPayload());
                    return ResponseEntity.ok(result);
                })
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @GetMapping("/write-back/flush-status")
    public Map<String, Object> writeBackFlushStatus() {
        return Map.of(
                "dirty_keys", cache.scard("metric:dirty"),
                "persisted_rows", metrics.count());
    }

    // -----------------------------------------------------------------------
    // 6. Refresh-ahead
    // -----------------------------------------------------------------------

    @GetMapping("/refresh-ahead/products/{pid}")
    public ResponseEntity<ProductResponse> refreshAheadGet(@PathVariable String pid) {
        // Track this product as hot
        cache.zadd("product:hot", pid, System.currentTimeMillis() / 1000.0);
        return productFromCacheOrDb("ra:product:" + pid, pid);
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    /** Cache-aside read shared by the strategies that keep explicit Redis calls. */
    private ResponseEntity<ProductResponse> productFromCacheOrDb(String key, String pid) {
        String cached = cache.get(key);
        if (cached != null) {
            return ResponseEntity.ok(mapper.readValue(cached, ProductView.class).from("cache"));
        }

        Optional<ProductView> product = products.find(pid);
        if (product.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        cache.setex(key, toJson(product.get()), ttl);
        return ResponseEntity.ok(product.get().from("db"));
    }

    private String toJson(Object obj) {
        return mapper.writeValueAsString(obj);
    }
}
