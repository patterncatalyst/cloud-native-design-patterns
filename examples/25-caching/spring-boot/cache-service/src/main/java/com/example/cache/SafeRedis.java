package com.example.cache;

import java.time.Duration;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

/**
 * Wraps all Redis operations in try-catch so that a Redis outage
 * never propagates to the client — the service degrades to DB-only.
 */
@Component
public class SafeRedis {

    private static final Logger log = LoggerFactory.getLogger(SafeRedis.class);

    private final StringRedisTemplate redis;

    public SafeRedis(StringRedisTemplate redis) {
        this.redis = redis;
    }

    /** Raw template for operations that need direct access (scheduled tasks). */
    public StringRedisTemplate template() {
        return redis;
    }

    // -- String ops ----------------------------------------------------------

    public String get(String key) {
        try {
            return redis.opsForValue().get(key);
        } catch (Exception e) {
            log.warn("Redis GET failed for key={}: {}", key, e.getMessage());
            return null;
        }
    }

    public void setex(String key, String value, long ttlSeconds) {
        try {
            redis.opsForValue().set(key, value, Duration.ofSeconds(ttlSeconds));
        } catch (Exception e) {
            log.warn("Redis SETEX failed for key={}: {}", key, e.getMessage());
        }
    }

    public void delete(String key) {
        try {
            redis.delete(key);
        } catch (Exception e) {
            log.warn("Redis DELETE failed for key={}: {}", key, e.getMessage());
        }
    }

    // -- Hash ops ------------------------------------------------------------

    public void hset(String key, Map<String, String> mapping) {
        try {
            redis.opsForHash().putAll(key, mapping);
        } catch (Exception e) {
            log.warn("Redis HSET failed for key={}: {}", key, e.getMessage());
            throw e; // write-back needs the caller to know
        }
    }

    @SuppressWarnings("unchecked")
    public Map<String, String> hgetall(String key) {
        try {
            Map<Object, Object> raw = redis.opsForHash().entries(key);
            if (raw.isEmpty()) return Collections.emptyMap();
            Map<String, String> result = new java.util.LinkedHashMap<>();
            raw.forEach((k, v) -> result.put(k.toString(), v.toString()));
            return result;
        } catch (Exception e) {
            log.warn("Redis HGETALL failed for key={}: {}", key, e.getMessage());
            return Collections.emptyMap();
        }
    }

    // -- Set ops -------------------------------------------------------------

    public void sadd(String key, String member) {
        try {
            redis.opsForSet().add(key, member);
        } catch (Exception e) {
            log.warn("Redis SADD failed for key={}: {}", key, e.getMessage());
            throw e; // write-back needs the caller to know
        }
    }

    public Set<String> spop(String key, long count) {
        try {
            List<String> popped = redis.opsForSet().pop(key, count);
            return popped == null ? Collections.emptySet() : new LinkedHashSet<>(popped);
        } catch (Exception e) {
            log.warn("Redis SPOP failed for key={}: {}", key, e.getMessage());
            return Collections.emptySet();
        }
    }

    public Long scard(String key) {
        try {
            return redis.opsForSet().size(key);
        } catch (Exception e) {
            log.warn("Redis SCARD failed for key={}: {}", key, e.getMessage());
            return -1L;
        }
    }

    // -- Sorted-set ops ------------------------------------------------------

    public void zadd(String key, String member, double score) {
        try {
            redis.opsForZSet().add(key, member, score);
        } catch (Exception e) {
            log.warn("Redis ZADD failed for key={}: {}", key, e.getMessage());
        }
    }

    public void zremrangebyscore(String key, double min, double max) {
        try {
            redis.opsForZSet().removeRangeByScore(key, min, max);
        } catch (Exception e) {
            log.warn("Redis ZREMRANGEBYSCORE failed for key={}: {}", key, e.getMessage());
        }
    }

    public Set<String> zrange(String key, long start, long end) {
        try {
            return redis.opsForZSet().range(key, start, end);
        } catch (Exception e) {
            log.warn("Redis ZRANGE failed for key={}: {}", key, e.getMessage());
            return Collections.emptySet();
        }
    }

    public Long ttl(String key) {
        try {
            return redis.getExpire(key);
        } catch (Exception e) {
            log.warn("Redis TTL failed for key={}: {}", key, e.getMessage());
            return -2L;
        }
    }

    // -- Key scanning --------------------------------------------------------

    public Set<String> scanKeys(String pattern) {
        try {
            return redis.keys(pattern);
        } catch (Exception e) {
            log.warn("Redis KEYS failed for pattern={}: {}", pattern, e.getMessage());
            return Collections.emptySet();
        }
    }
}
