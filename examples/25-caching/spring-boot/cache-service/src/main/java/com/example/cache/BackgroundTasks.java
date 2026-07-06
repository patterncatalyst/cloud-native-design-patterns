package com.example.cache;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Background scheduled tasks for write-back flushing and refresh-ahead warming.
 */
@Component
public class BackgroundTasks {

    private static final Logger log = LoggerFactory.getLogger(BackgroundTasks.class);
    private static final int FLUSH_BATCH = 100;

    private final SafeRedis cache;
    private final JdbcClient jdbc;
    private final ObjectMapper mapper;

    @Value("${cache-service.ttl-seconds:60}")
    private long ttl;

    @Value("${cache-service.refresh-before-seconds:10}")
    private long refreshBefore;

    public BackgroundTasks(SafeRedis cache, JdbcClient jdbc, ObjectMapper mapper) {
        this.cache = cache;
        this.jdbc = jdbc;
        this.mapper = mapper;
    }

    // -----------------------------------------------------------------------
    // Write-back flusher: drain dirty set to Postgres in batches
    // -----------------------------------------------------------------------

    @Scheduled(fixedDelayString = "${cache-service.flush-period-ms:1000}")
    public void flusher() {
        try {
            Set<String> ids = cache.spop("metric:dirty", FLUSH_BATCH);
            if (ids == null || ids.isEmpty()) {
                return;
            }

            for (String mid : ids) {
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
            }
            log.info("flusher: persisted {} metrics", ids.size());
        } catch (Exception e) {
            log.error("flusher error", e);
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
        } catch (JsonProcessingException e) {
            throw new RuntimeException("JSON serialization failed", e);
        }
    }
}
