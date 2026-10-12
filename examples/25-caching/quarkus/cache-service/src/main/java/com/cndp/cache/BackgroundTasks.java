package com.cndp.cache;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
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
    private static final int MAX_FLUSH_ATTEMPTS = 5;
    private static final long MAX_FLUSH_BACKOFF_MS = 8000;
    private static final long FLUSH_PERIOD_MS = 1000;

    // Touched only by the flusher (concurrent runs are skipped).
    private volatile int failures;
    private volatile long nextFlushAt;

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

    // Write-back flush policy: a failed upsert is re-queued, with exponential backoff between
    // flush cycles and a bounded number of attempts per id. After MAX_FLUSH_ATTEMPTS the id
    // moves to metric:failed (its value stays in the cache) and is logged, never dropped silently.
    @Scheduled(every = "${cache-service.flush-period:1s}", concurrentExecution = Scheduled.ConcurrentExecution.SKIP)
    void flusher() {
        if (System.currentTimeMillis() < nextFlushAt) {
            return; // backing off after a failed flush
        }
        try {
            Set<String> ids = cache.spop("metric:dirty", FLUSH_BATCH);
            if (ids == null || ids.isEmpty()) {
                return;
            }

            List<String> failed = new ArrayList<>();
            for (String mid : ids) {
                try {
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
                    cache.hdel("metric:attempts", mid);
                } catch (Exception e) {
                    Log.errorf("flusher: flush failed for %s: %s", mid, e.getMessage());
                    failed.add(mid);
                }
            }
            Log.infof("flusher: persisted %d metrics", ids.size() - failed.size());
            if (failed.isEmpty()) {
                failures = 0;
            } else {
                failures++;
                nextFlushAt = System.currentTimeMillis()
                        + Math.min(FLUSH_PERIOD_MS << failures, MAX_FLUSH_BACKOFF_MS);
                requeue(failed);
            }
        } catch (Exception e) {
            Log.errorf("flusher error: %s", e.getMessage());
        }
    }

    private void requeue(List<String> ids) {
        for (String mid : ids) {
            long n = cache.hincrby("metric:attempts", mid, 1);
            try {
                if (n >= MAX_FLUSH_ATTEMPTS) {
                    cache.sadd("metric:failed", mid);
                    cache.hdel("metric:attempts", mid);
                    Log.errorf("flusher: giving up on %s after %d attempts, parked on metric:failed", mid, n);
                } else {
                    cache.sadd("metric:dirty", mid);
                    Log.warnf("flusher: re-queued %s (attempt %d/%d)", mid, n, MAX_FLUSH_ATTEMPTS);
                }
            } catch (Exception e) {
                Log.errorf("flusher: could not re-queue %s: %s", mid, e.getMessage());
            }
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
