package com.cndp.cache;

import java.sql.ResultSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

import javax.sql.DataSource;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.quarkus.logging.Log;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.PUT;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.config.inject.ConfigProperty;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class CacheResource {

    @Inject
    DataSource dataSource;

    @Inject
    SafeRedis cache;

    @Inject
    ObjectMapper mapper;

    @ConfigProperty(name = "cache-service.ttl-seconds", defaultValue = "60")
    long ttl;

    @GET
    @Path("healthz")
    public Map<String, Object> healthz() {
        return Map.of("status", "ok");
    }

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
    public Response cacheAsideGet(@PathParam("pid") String pid) {
        String key = "ca:product:" + pid;

        String cached = cache.get(key);
        if (cached != null) {
            Map<String, Object> result = parseJson(cached);
            result.put("source", "cache");
            return Response.ok(result).build();
        }

        Map<String, Object> row = findProduct(pid);
        if (row == null) {
            return Response.status(404).build();
        }
        cache.setex(key, toJson(row), ttl);
        row.put("source", "db");
        return Response.ok(row).build();
    }

    @PUT
    @Path("cache-aside/products/{pid}")
    public Response cacheAsideUpdate(@PathParam("pid") String pid, Map<String, Object> body) {
        try (var conn = dataSource.getConnection();
             var ps = conn.prepareStatement("UPDATE products SET name = ?, price_cents = ? WHERE id = ?")) {
            ps.setString(1, body.get("name").toString());
            ps.setInt(2, ((Number) body.get("price_cents")).intValue());
            ps.setString(3, pid);
            ps.executeUpdate();
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

    @GET
    @Path("read-through/products/{pid}")
    public Response readThroughGet(@PathParam("pid") String pid) {
        String key = "rt:product:" + pid;

        String cached = cache.get(key);
        if (cached != null) {
            Map<String, Object> result = parseJson(cached);
            result.put("source", "cache");
            return Response.ok(result).build();
        }

        Map<String, Object> row = findProduct(pid);
        if (row == null) {
            return Response.status(404).build();
        }
        cache.setex(key, toJson(row), ttl);
        row.put("source", "db");
        return Response.ok(row).build();
    }

    @GET
    @Path("write-through/products/{pid}")
    public Response writeThroughGet(@PathParam("pid") String pid) {
        String key = "wt:product:" + pid;

        String cached = cache.get(key);
        if (cached != null) {
            Map<String, Object> result = parseJson(cached);
            result.put("source", "cache");
            return Response.ok(result).build();
        }

        Map<String, Object> row = findProduct(pid);
        if (row == null) {
            return Response.status(404).build();
        }
        cache.setex(key, toJson(row), ttl);
        row.put("source", "db");
        return Response.ok(row).build();
    }

    @PUT
    @Path("write-through/products/{pid}")
    public Response writeThroughUpdate(@PathParam("pid") String pid, Map<String, Object> body) {
        try (var conn = dataSource.getConnection();
             var ps = conn.prepareStatement("UPDATE products SET name = ?, price_cents = ? WHERE id = ?")) {
            ps.setString(1, body.get("name").toString());
            ps.setInt(2, ((Number) body.get("price_cents")).intValue());
            ps.setString(3, pid);
            ps.executeUpdate();
        } catch (Exception e) {
            Log.errorf("write-through update failed: %s", e.getMessage());
            return Response.serverError().build();
        }

        Map<String, Object> row = findProduct(pid);
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
    public Response writeAroundCreate(Map<String, Object> body) {
        String id = body.get("id").toString();
        String type = body.get("type").toString();
        Object payload = body.get("payload");
        String payloadJson = (payload == null) ? "{}" : toJson(payload);

        try (var conn = dataSource.getConnection();
             var ps = conn.prepareStatement(
                     "INSERT INTO events (id, type, payload) VALUES (?, ?, ?::jsonb)")) {
            ps.setString(1, id);
            ps.setString(2, type);
            ps.setString(3, payloadJson);
            ps.executeUpdate();
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
    public Response writeAroundGet(@PathParam("eid") String eid) {
        String key = "wa:event:" + eid;

        String cached = cache.get(key);
        if (cached != null) {
            Map<String, Object> result = parseJson(cached);
            result.put("source", "cache");
            return Response.ok(result).build();
        }

        try (var conn = dataSource.getConnection();
             var ps = conn.prepareStatement("SELECT id, type, payload FROM events WHERE id = ?")) {
            ps.setString(1, eid);
            try (var rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return Response.status(404).build();
                }
                Map<String, Object> data = new LinkedHashMap<>();
                data.put("id", rs.getString("id"));
                data.put("type", rs.getString("type"));
                data.put("payload", parseJson(rs.getString("payload")));
                cache.setex(key, toJson(data), ttl);
                data.put("source", "db");
                return Response.ok(data).build();
            }
        } catch (Exception e) {
            Log.errorf("write-around read failed: %s", e.getMessage());
            return Response.serverError().build();
        }
    }

    @PUT
    @Path("write-back/metrics/{mid}")
    public Response writeBackWrite(@PathParam("mid") String mid, Map<String, Object> body) {
        Map<String, String> mapping = new LinkedHashMap<>();
        mapping.put("value", body.get("value").toString());
        mapping.put("tags", toJson(body.get("tags")));

        try {
            cache.hset("metric:" + mid, mapping);
            cache.sadd("metric:dirty", mid);
        } catch (Exception e) {
            return Response.status(503)
                    .entity(Map.of("error", "cache unavailable")).build();
        }
        return Response.ok(Map.of(
                "ok", true,
                "pattern", "write-back",
                "action", "cached-for-flush")).build();
    }

    @GET
    @Path("write-back/metrics/{mid}")
    public Response writeBackGet(@PathParam("mid") String mid) {
        Map<String, String> data = cache.hgetall("metric:" + mid);
        if (!data.isEmpty()) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("source", "cache");
            result.put("id", mid);
            result.putAll(data);
            return Response.ok(result).build();
        }

        try (var conn = dataSource.getConnection();
             var ps = conn.prepareStatement("SELECT id, payload FROM metrics WHERE id = ?")) {
            ps.setString(1, mid);
            try (var rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return Response.status(404).build();
                }
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("source", "db");
                row.put("id", rs.getString("id"));
                row.put("payload", parseJson(rs.getString("payload")));
                return Response.ok(row).build();
            }
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
        try (var conn = dataSource.getConnection();
             var stmt = conn.createStatement();
             var rs = stmt.executeQuery("SELECT count(*) FROM metrics")) {
            if (rs.next()) {
                dbCount = rs.getLong(1);
            }
        } catch (Exception e) {
            Log.errorf("flush-status query failed: %s", e.getMessage());
        }
        return Map.of(
                "dirty_keys", dirtyCount,
                "persisted_rows", dbCount);
    }

    @GET
    @Path("refresh-ahead/products/{pid}")
    public Response refreshAheadGet(@PathParam("pid") String pid) {
        String key = "ra:product:" + pid;

        cache.zadd("product:hot", pid, System.currentTimeMillis() / 1000.0);

        String cached = cache.get(key);
        if (cached != null) {
            Map<String, Object> result = parseJson(cached);
            result.put("source", "cache");
            return Response.ok(result).build();
        }

        Map<String, Object> row = findProduct(pid);
        if (row == null) {
            return Response.status(404).build();
        }
        cache.setex(key, toJson(row), ttl);
        row.put("source", "db");
        return Response.ok(row).build();
    }

    private Map<String, Object> findProduct(String pid) {
        try (var conn = dataSource.getConnection();
             var ps = conn.prepareStatement(
                     "SELECT id, name, price_cents FROM products WHERE id = ?")) {
            ps.setString(1, pid);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return null;
                }
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("id", rs.getString("id"));
                m.put("name", rs.getString("name"));
                m.put("price_cents", rs.getInt("price_cents"));
                return m;
            }
        } catch (Exception e) {
            Log.errorf("findProduct failed for %s: %s", pid, e.getMessage());
            return null;
        }
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
