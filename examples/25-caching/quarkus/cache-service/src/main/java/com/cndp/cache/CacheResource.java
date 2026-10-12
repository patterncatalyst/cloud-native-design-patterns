package com.cndp.cache;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.atomic.AtomicBoolean;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.quarkus.cache.Cache;
import io.quarkus.cache.CacheName;
import io.quarkus.logging.Log;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.NotFoundException;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.PUT;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.jboss.resteasy.reactive.RestPath;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class CacheResource {

    @Inject
    Store store;

    /** Explicit Redis client for the strategies that must keep working while Redis is down. */
    @Inject
    SafeRedis cache;

    /** Quarkus Redis cache (quarkus.cache.redis.read-through.*) for the read-through strategy. */
    @CacheName("read-through")
    Cache readThroughCache;

    @Inject
    ObjectMapper mapper;

    @ConfigProperty(name = "cache-service.ttl-seconds", defaultValue = "60")
    long ttl;

    @GET
    @Path("cache-keys")
    public Map<String, Object> cacheKeys() {
        Set<String> keys = cache.scanKeys("*");
        if (keys == null) {
            return Map.of("keys", new TreeSet<>(), "error", "cache unavailable");
        }
        return Map.of("keys", new TreeSet<>(keys));
    }

    @GET
    @Path("cache-aside/products/{pid}")
    public ProductView cacheAsideGet(@RestPath String pid) {
        return cachedProduct("ca:product:" + pid, pid);
    }

    @PUT
    @Path("cache-aside/products/{pid}")
    public Response cacheAsideUpdate(@RestPath String pid, ProductUpdate body) {
        try {
            store.updateProduct(pid, body.name(), body.priceCents());
        } catch (Exception e) {
            Log.errorf("cache-aside update failed: %s", e.getMessage());
            return Response.serverError().build();
        }
        cache.delete("ca:product:" + pid);
        return Response.ok(Map.of(
                "ok", true,
                "pattern", "cache-aside",
                "action", "invalidated")).build();
    }

    /**
     * Read-through: the cache owns the load. Cache.get runs the loader only on a miss, stores the
     * result with the TTL from quarkus.cache.redis.read-through.expire-after-write, and falls back
     * to the loader when Redis is unreachable. The loader flips a flag so the response can report
     * where the value came from.
     */
    @GET
    @Path("read-through/products/{pid}")
    public ProductView readThroughGet(@RestPath String pid) {
        var loaded = new AtomicBoolean(false);
        Product product = readThroughCache.<String, Product>get(pid, key -> {
            loaded.set(true);
            Product row = store.findProduct(key);
            if (row == null) {
                throw new NotFoundException();
            }
            return row;
        }).await().indefinitely();
        return ProductView.of(product, loaded.get() ? "db" : "cache");
    }

    @GET
    @Path("write-through/products/{pid}")
    public ProductView writeThroughGet(@RestPath String pid) {
        return cachedProduct("wt:product:" + pid, pid);
    }

    @PUT
    @Path("write-through/products/{pid}")
    public Response writeThroughUpdate(@RestPath String pid, ProductUpdate body) {
        try {
            store.updateProduct(pid, body.name(), body.priceCents());
        } catch (Exception e) {
            Log.errorf("write-through update failed: %s", e.getMessage());
            return Response.serverError().build();
        }

        Product row = store.findProduct(pid);
        if (row != null) {
            cache.setex("wt:product:" + pid, toJson(row), ttl);
        }
        return Response.ok(Map.of(
                "ok", true,
                "pattern", "write-through",
                "action", "set")).build();
    }

    @POST
    @Path("write-around/events")
    public Response writeAroundCreate(EventRequest body) {
        try {
            store.insertEvent(body.id(), body.type(), body.payload());
        } catch (Exception e) {
            Log.errorf("write-around insert failed: %s", e.getMessage());
            return Response.serverError().build();
        }

        return Response.ok(Map.of(
                "ok", true,
                "pattern", "write-around",
                "action", "db-only")).build();
    }

    @GET
    @Path("write-around/events/{eid}")
    public Response writeAroundGet(@RestPath String eid) {
        String key = "wa:event:" + eid;

        String cached = cache.get(key);
        if (cached != null) {
            Map<String, Object> result = parseJson(cached);
            result.put("source", "cache");
            return Response.ok(result).build();
        }

        try {
            EventEntity event = store.findEvent(eid);
            if (event == null) {
                return Response.status(404).build();
            }
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("id", event.id);
            data.put("type", event.type);
            data.put("payload", event.payload);
            cache.setex(key, toJson(data), ttl);
            data.put("source", "db");
            return Response.ok(data).build();
        } catch (Exception e) {
            Log.errorf("write-around read failed: %s", e.getMessage());
            return Response.serverError().build();
        }
    }

    @PUT
    @Path("write-back/metrics/{mid}")
    public Response writeBackWrite(@RestPath String mid, MetricRequest body) {
        Map<String, String> mapping = new LinkedHashMap<>();
        mapping.put("value", String.valueOf(body.value()));
        mapping.put("tags", toJson(body.tags()));

        try {
            cache.hset("metric:" + mid, mapping);
            cache.sadd("metric:dirty", mid);
        } catch (Exception e) {
            return Response.status(503)
                    .entity(Map.of("error", "cache unavailable")).build();
        }
        // 202: queued in the cache, not yet durable in Postgres
        return Response.accepted(Map.of(
                "ok", true,
                "pattern", "write-back",
                "action", "cached-for-flush")).build();
    }

    @GET
    @Path("write-back/metrics/{mid}")
    public Response writeBackGet(@RestPath String mid) {
        Map<String, String> data = cache.hgetall("metric:" + mid);
        if (!data.isEmpty()) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("source", "cache");
            result.put("id", mid);
            result.putAll(data);
            return Response.ok(result).build();
        }

        try {
            MetricEntity metric = store.findMetric(mid);
            if (metric == null) {
                return Response.status(404).build();
            }
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("source", "db");
            row.put("id", metric.id);
            row.put("payload", metric.payload);
            return Response.ok(row).build();
        } catch (Exception e) {
            Log.errorf("write-back read failed: %s", e.getMessage());
            return Response.serverError().build();
        }
    }

    @GET
    @Path("write-back/flush-status")
    public Map<String, Object> writeBackFlushStatus() {
        long dirtyCount = cache.scard("metric:dirty");
        long dbCount = 0;
        try {
            dbCount = store.countMetrics();
        } catch (Exception e) {
            Log.errorf("flush-status query failed: %s", e.getMessage());
        }
        return Map.of(
                "dirty_keys", dirtyCount,
                "persisted_rows", dbCount);
    }

    @GET
    @Path("refresh-ahead/products/{pid}")
    public ProductView refreshAheadGet(@RestPath String pid) {
        cache.zadd("product:hot", pid, System.currentTimeMillis() / 1000.0);
        return cachedProduct("ra:product:" + pid, pid);
    }

    /**
     * Cache-aside lookup shared by the strategies that read the same way: try Redis, fall back to
     * the database, then fill Redis. Every Redis call is best effort, so a Redis outage only
     * turns hits into database reads.
     */
    private ProductView cachedProduct(String key, String pid) {
        String cached = cache.get(key);
        if (cached != null) {
            return ProductView.of(fromJson(cached, Product.class), "cache");
        }

        Product row = store.findProduct(pid);
        if (row == null) {
            throw new NotFoundException();
        }
        cache.setex(key, toJson(row), ttl);
        return ProductView.of(row, "db");
    }

    private String toJson(Object obj) {
        try {
            return mapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("JSON serialization failed", e);
        }
    }

    private <T> T fromJson(String json, Class<T> type) {
        try {
            return mapper.readValue(json, type);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("JSON deserialization failed", e);
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseJson(String json) {
        return new LinkedHashMap<>(fromJson(json, Map.class));
    }
}
