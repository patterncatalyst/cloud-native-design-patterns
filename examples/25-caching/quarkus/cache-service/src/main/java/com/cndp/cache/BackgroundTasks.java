package com.cndp.cache;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

import javax.sql.DataSource;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.quarkus.logging.Log;
import io.quarkus.scheduler.Scheduled;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;

@ApplicationScoped
public class BackgroundTasks {

    private static final int FLUSH_BATCH = 100;

    @Inject
    SafeRedis cache;

    @Inject
    DataSource dataSource;

    @Inject
    ObjectMapper mapper;

    @ConfigProperty(name = "cache-service.ttl-seconds", defaultValue = "60")
    long ttl;

    @ConfigProperty(name = "cache-service.refresh-before-seconds", defaultValue = "10")
    long refreshBefore;

    @Scheduled(every = "${cache-service.flush-period:1s}")
    void flusher() {
        try {
            Set<String> ids = cache.spop("metric:dirty", FLUSH_BATCH);
            if (ids == null || ids.isEmpty()) {
                return;
            }

            for (String mid : ids) {
                Map<String, String> data = cache.hgetall("metric:" + mid);
                if (!data.isEmpty()) {
                    String payloadJson = toJson(data);
                    try (var conn = dataSource.getConnection();
                         var ps = conn.prepareStatement(
                                 "INSERT INTO metrics (id, payload) VALUES (?, ?::jsonb) "
                                         + "ON CONFLICT (id) DO UPDATE SET payload = ?::jsonb, ts = NOW()")) {
                        ps.setString(1, mid);
                        ps.setString(2, payloadJson);
                        ps.setString(3, payloadJson);
                        ps.executeUpdate();
                    }
                }
            }
            Log.infof("flusher: persisted %d metrics", ids.size());
        } catch (Exception e) {
            Log.errorf("flusher error: %s", e.getMessage());
        }
    }

    @Scheduled(every = "${cache-service.refresh-period:5s}")
    void refresher() {
        try {
            double cutoff = (System.currentTimeMillis() / 1000.0) - 300;
            cache.zremrangebyscore("product:hot", 0, cutoff);

            Set<String> hotIds = cache.zrange("product:hot", 0, -1);
            if (hotIds == null || hotIds.isEmpty()) {
                return;
            }

            for (String pid : hotIds) {
                long ttlVal = cache.ttl("ra:product:" + pid);
                if (ttlVal > 0 && ttlVal < refreshBefore) {
                    Map<String, Object> row = findProduct(pid);
                    if (row != null) {
                        cache.setex("ra:product:" + pid, toJson(row), ttl);
                        Log.infof("refresher: pre-warmed %s", pid);
                    }
                }
            }
        } catch (Exception e) {
            Log.errorf("refresher error: %s", e.getMessage());
        }
    }

    private Map<String, Object> findProduct(String pid) {
        try (var conn = dataSource.getConnection();
             var ps = conn.prepareStatement(
                     "SELECT id, name, price_cents FROM products WHERE id = ?")) {
            ps.setString(1, pid);
            try (var rs = ps.executeQuery()) {
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
}
