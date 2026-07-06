package com.example.cache;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

@RestController
public class CacheController {

    private final JdbcClient jdbc;
    private final SafeRedis cache;
    private final ObjectMapper mapper;

    @Value("${cache-service.ttl-seconds:60}")
    private long ttl;

    public CacheController(JdbcClient jdbc, SafeRedis cache, ObjectMapper mapper) {
        this.jdbc = jdbc;
        this.cache = cache;
        this.mapper = mapper;
    }

    // -----------------------------------------------------------------------
    // Health
    // -----------------------------------------------------------------------

    @GetMapping("/healthz")
    public Map<String, Object> healthz() {
        return Map.of("status", "ok");
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
    public ResponseEntity<Map<String, Object>> cacheAsideGet(@PathVariable String pid) {
        String key = "ca:product:" + pid;

        String cached = cache.get(key);
        if (cached != null) {
            Map<String, Object> result = parseJson(cached);
            result.put("source", "cache");
            return ResponseEntity.ok(result);
        }

        Map<String, Object> row = findProduct(pid);
        if (row == null) {
            return ResponseEntity.notFound().build();
        }
        cache.setex(key, toJson(row), ttl);
        row.put("source", "db");
        return ResponseEntity.ok(row);
    }

    @PutMapping("/cache-aside/products/{pid}")
    public ResponseEntity<Map<String, Object>> cacheAsideUpdate(
            @PathVariable String pid, @RequestBody Map<String, Object> body) {
        jdbc.sql("UPDATE products SET name = ?, price_cents = ? WHERE id = ?")
                .param(body.get("name").toString())
                .param(((Number) body.get("price_cents")).intValue())
                .param(pid)
                .update();
        cache.delete("ca:product:" + pid);
        return ResponseEntity.ok(Map.of(
                "ok", true,
                "pattern", "cache-aside",
                "action", "invalidated"));
    }

    // -----------------------------------------------------------------------
    // 2. Read-through
    // -----------------------------------------------------------------------

    @GetMapping("/read-through/products/{pid}")
    public ResponseEntity<Map<String, Object>> readThroughGet(@PathVariable String pid) {
        String key = "rt:product:" + pid;

        // The read-through abstraction: check cache first, populate on miss
        String cached = cache.get(key);
        if (cached != null) {
            Map<String, Object> result = parseJson(cached);
            result.put("source", "cache");
            return ResponseEntity.ok(result);
        }

        Map<String, Object> row = findProduct(pid);
        if (row == null) {
            return ResponseEntity.notFound().build();
        }
        cache.setex(key, toJson(row), ttl);
        row.put("source", "db");
        return ResponseEntity.ok(row);
    }

    // -----------------------------------------------------------------------
    // 3. Write-through
    // -----------------------------------------------------------------------

    @GetMapping("/write-through/products/{pid}")
    public ResponseEntity<Map<String, Object>> writeThroughGet(@PathVariable String pid) {
        String key = "wt:product:" + pid;

        String cached = cache.get(key);
        if (cached != null) {
            Map<String, Object> result = parseJson(cached);
            result.put("source", "cache");
            return ResponseEntity.ok(result);
        }

        Map<String, Object> row = findProduct(pid);
        if (row == null) {
            return ResponseEntity.notFound().build();
        }
        cache.setex(key, toJson(row), ttl);
        row.put("source", "db");
        return ResponseEntity.ok(row);
    }

    @PutMapping("/write-through/products/{pid}")
    public ResponseEntity<Map<String, Object>> writeThroughUpdate(
            @PathVariable String pid, @RequestBody Map<String, Object> body) {
        jdbc.sql("UPDATE products SET name = ?, price_cents = ? WHERE id = ?")
                .param(body.get("name").toString())
                .param(((Number) body.get("price_cents")).intValue())
                .param(pid)
                .update();

        // Write-through: update DB then immediately populate cache
        Map<String, Object> row = findProduct(pid);
        if (row != null) {
            cache.setex("wt:product:" + pid, toJson(row), ttl);
        }
        return ResponseEntity.ok(Map.of(
                "ok", true,
                "pattern", "write-through",
                "action", "set"));
    }

    // -----------------------------------------------------------------------
    // 4. Write-around
    // -----------------------------------------------------------------------

    @PostMapping("/write-around/events")
    public ResponseEntity<Map<String, Object>> writeAroundCreate(@RequestBody Map<String, Object> body) {
        String id = body.get("id").toString();
        String type = body.get("type").toString();
        Object payload = body.get("payload");
        String payloadJson = (payload == null) ? "{}" : toJson(payload);

        jdbc.sql("INSERT INTO events (id, type, payload) VALUES (?, ?, ?::jsonb)")
                .param(id)
                .param(type)
                .param(payloadJson)
                .update();

        // Write-around: DB only, no cache write
        return ResponseEntity.ok(Map.of(
                "ok", true,
                "pattern", "write-around",
                "action", "db-only"));
    }

    @GetMapping("/write-around/events/{eid}")
    public ResponseEntity<Map<String, Object>> writeAroundGet(@PathVariable String eid) {
        String key = "wa:event:" + eid;

        String cached = cache.get(key);
        if (cached != null) {
            Map<String, Object> result = parseJson(cached);
            result.put("source", "cache");
            return ResponseEntity.ok(result);
        }

        var optRow = jdbc.sql("SELECT id, type, payload FROM events WHERE id = ?")
                .param(eid)
                .query((rs, rowNum) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getString("id"));
                    m.put("type", rs.getString("type"));
                    m.put("payload", parseJson(rs.getString("payload")));
                    return m;
                })
                .optional();

        if (optRow.isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        Map<String, Object> data = optRow.get();
        cache.setex(key, toJson(data), ttl);
        data.put("source", "db");
        return ResponseEntity.ok(data);
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
        return ResponseEntity.ok(Map.of(
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

        var optRow = jdbc.sql("SELECT id, payload FROM metrics WHERE id = ?")
                .param(mid)
                .query((rs, rowNum) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("source", "db");
                    m.put("id", rs.getString("id"));
                    m.put("payload", parseJson(rs.getString("payload")));
                    return m;
                })
                .optional();

        if (optRow.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(optRow.get());
    }

    @GetMapping("/write-back/flush-status")
    public Map<String, Object> writeBackFlushStatus() {
        Long dirtyCount = cache.scard("metric:dirty");
        Long dbCount = jdbc.sql("SELECT count(*) FROM metrics")
                .query(Long.class)
                .single();
        return Map.of(
                "dirty_keys", dirtyCount,
                "persisted_rows", dbCount);
    }

    // -----------------------------------------------------------------------
    // 6. Refresh-ahead
    // -----------------------------------------------------------------------

    @GetMapping("/refresh-ahead/products/{pid}")
    public ResponseEntity<Map<String, Object>> refreshAheadGet(@PathVariable String pid) {
        String key = "ra:product:" + pid;

        // Track this product as hot
        cache.zadd("product:hot", pid, System.currentTimeMillis() / 1000.0);

        String cached = cache.get(key);
        if (cached != null) {
            Map<String, Object> result = parseJson(cached);
            result.put("source", "cache");
            return ResponseEntity.ok(result);
        }

        Map<String, Object> row = findProduct(pid);
        if (row == null) {
            return ResponseEntity.notFound().build();
        }
        cache.setex(key, toJson(row), ttl);
        row.put("source", "db");
        return ResponseEntity.ok(row);
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    private Map<String, Object> findProduct(String pid) {
        return jdbc.sql("SELECT id, name, price_cents FROM products WHERE id = ?")
                .param(pid)
                .query((rs, rowNum) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getString("id"));
                    m.put("name", rs.getString("name"));
                    m.put("price_cents", rs.getInt("price_cents"));
                    return m;
                })
                .optional()
                .orElse(null);
    }

    private String toJson(Object obj) {
        try {
            return mapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("JSON serialization failed", e);
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseJson(String json) {
        try {
            return new LinkedHashMap<>(mapper.readValue(json, Map.class));
        } catch (JsonProcessingException e) {
            throw new RuntimeException("JSON deserialization failed", e);
        }
    }
}
