package com.example.cache;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import tools.jackson.core.JacksonException;
import tools.jackson.databind.json.JsonMapper;

/**
 * Background scheduled tasks for write-back flushing and refresh-ahead warming.
 */
@Component
public class BackgroundTasks {

    private static final Logger log = LoggerFactory.getLogger(BackgroundTasks.class);
    private static final int FLUSH_BATCH = 100;
    private static final int MAX_FLUSH_ATTEMPTS = 5;
    private static final long MAX_FLUSH_BACKOFF_MS = 8000;

    // Touched only by the scheduler thread (fixed-delay runs never overlap).
    private int failures;
    private long nextFlushAt;

    private final SafeRedis cache;
    private final JdbcClient jdbc;
    private final JsonMapper mapper;

    @Value("${cache-service.ttl-seconds:60}")
    private long ttl;

    @Value("${cache-service.flush-period-ms:1000}")
    private long flushPeriodMs;

    @Value("${cache-service.refresh-before-seconds:10}")
    private long refreshBefore;

    public BackgroundTasks(SafeRedis cache, JdbcClient jdbc, JsonMapper mapper) {
        this.cache = cache;
        this.jdbc = jdbc;
        this.mapper = mapper;
    }

    // -----------------------------------------------------------------------
    // Write-back flusher: drain dirty set to Postgres in batches.
    // A failed upsert is re-queued, with exponential backoff between flush cycles and a
    // bounded number of attempts per id. After MAX_FLUSH_ATTEMPTS the id moves to
    // metric:failed (its value stays in the cache) and is logged, never dropped silently.
    // -----------------------------------------------------------------------

    @Scheduled(fixedDelayString = "${cache-service.flush-period-ms:1000}")
    public void flusher() {
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
                        jdbc.sql("INSERT INTO metrics (id, payload) VALUES (?, ?::jsonb) "
                                + "ON CONFLICT (id) DO UPDATE SET payload = ?::jsonb, ts = NOW()")
                                .param(mid)
                                .param(payloadJson)
                                .param(payloadJson)
                                .update();
                    }
                    cache.hdel("metric:attempts", mid);
                } catch (Exception e) {
                    log.error("flusher: flush failed for {}: {}", mid, e.getMessage());
                    failed.add(mid);
                }
            }
            log.info("flusher: persisted {} metrics", ids.size() - failed.size());
            if (failed.isEmpty()) {
                failures = 0;
            } else {
                failures++;
                nextFlushAt = System.currentTimeMillis()
                        + Math.min(flushPeriodMs << failures, MAX_FLUSH_BACKOFF_MS);
                requeue(failed);
            }
        } catch (Exception e) {
            log.error("flusher error", e);
        }
    }

    private void requeue(List<String> ids) {
        for (String mid : ids) {
            long n = cache.hincrby("metric:attempts", mid, 1);
            try {
                if (n >= MAX_FLUSH_ATTEMPTS) {
                    cache.sadd("metric:failed", mid);
                    cache.hdel("metric:attempts", mid);
                    log.error("flusher: giving up on {} after {} attempts, parked on metric:failed", mid, n);
                } else {
                    cache.sadd("metric:dirty", mid);
                    log.warn("flusher: re-queued {} (attempt {}/{})", mid, n, MAX_FLUSH_ATTEMPTS);
                }
            } catch (Exception e) {
                log.error("flusher: could not re-queue {}: {}", mid, e.getMessage());
            }
        }
    }

    // -----------------------------------------------------------------------
    // Refresh-ahead: re-warm hot keys before their TTL fires
    // -----------------------------------------------------------------------

    @Scheduled(fixedDelayString = "${cache-service.refresh-period-ms:5000}")
    public void refresher() {
        try {
            double cutoff = (System.currentTimeMillis() / 1000.0) - 300;
            cache.zremrangebyscore("product:hot", 0, cutoff);

            Set<String> hotIds = cache.zrange("product:hot", 0, -1);
            if (hotIds == null || hotIds.isEmpty()) {
                return;
            }

            for (String pid : hotIds) {
                Long ttlVal = cache.ttl("ra:product:" + pid);
                if (ttlVal != null && ttlVal > 0 && ttlVal < refreshBefore) {
                    var optRow = jdbc.sql("SELECT id, name, price_cents FROM products WHERE id = ?")
                            .param(pid)
                            .query((rs, rowNum) -> {
                                Map<String, Object> m = new LinkedHashMap<>();
                                m.put("id", rs.getString("id"));
                                m.put("name", rs.getString("name"));
                                m.put("price_cents", rs.getInt("price_cents"));
                                return m;
                            })
                            .optional();

                    if (optRow.isPresent()) {
                        cache.setex("ra:product:" + pid, toJson(optRow.get()), ttl);
                        log.info("refresher: pre-warmed {}", pid);
                    }
                }
            }
        } catch (Exception e) {
            log.error("refresher error", e);
        }
    }

    private String toJson(Object obj) {
        try {
            return mapper.writeValueAsString(obj);
        } catch (JacksonException e) {
            throw new RuntimeException("JSON serialization failed", e);
        }
    }
}
