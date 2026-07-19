package com.cndp.cache;

import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import io.quarkus.logging.Log;
import io.quarkus.redis.datasource.RedisDataSource;
import io.quarkus.redis.datasource.hash.HashCommands;
import io.quarkus.redis.datasource.keys.KeyCommands;
import io.quarkus.redis.datasource.set.SetCommands;
import io.quarkus.redis.datasource.sortedset.ScoreRange;
import io.quarkus.redis.datasource.sortedset.SortedSetCommands;
import io.quarkus.redis.datasource.value.ValueCommands;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

@ApplicationScoped
public class SafeRedis {

    private final ValueCommands<String, String> values;
    private final KeyCommands<String> keys;
    private final HashCommands<String, String, String> hashes;
    private final SetCommands<String, String> sets;
    private final SortedSetCommands<String, String> sortedSets;

    @Inject
    public SafeRedis(RedisDataSource redis) {
        this.values = redis.value(String.class);
        this.keys = redis.key();
        this.hashes = redis.hash(String.class);
        this.sets = redis.set(String.class);
        this.sortedSets = redis.sortedSet(String.class);
    }

    public String get(String key) {
        try {
            return values.get(key);
        } catch (Exception e) {
            Log.warnf("Redis GET failed for key=%s: %s", key, e.getMessage());
            return null;
        }
    }

    public void setex(String key, String value, long ttlSeconds) {
        try {
            values.setex(key, ttlSeconds, value);
        } catch (Exception e) {
            Log.warnf("Redis SETEX failed for key=%s: %s", key, e.getMessage());
        }
    }

    public void delete(String key) {
        try {
            keys.del(key);
        } catch (Exception e) {
            Log.warnf("Redis DELETE failed for key=%s: %s", key, e.getMessage());
        }
    }

    public void hset(String key, Map<String, String> mapping) {
        try {
            for (var entry : mapping.entrySet()) {
                hashes.hset(key, entry.getKey(), entry.getValue());
            }
        } catch (Exception e) {
            Log.warnf("Redis HSET failed for key=%s: %s", key, e.getMessage());
            throw e;
        }
    }

    public Map<String, String> hgetall(String key) {
        try {
            Map<String, String> result = hashes.hgetall(key);
            return result == null ? Collections.emptyMap() : result;
        } catch (Exception e) {
            Log.warnf("Redis HGETALL failed for key=%s: %s", key, e.getMessage());
            return Collections.emptyMap();
        }
    }

    public void sadd(String key, String member) {
        try {
            sets.sadd(key, member);
        } catch (Exception e) {
            Log.warnf("Redis SADD failed for key=%s: %s", key, e.getMessage());
            throw e;
        }
    }

    public Set<String> spop(String key, int count) {
        try {
            Set<String> popped = sets.spop(key, count);
            return popped == null ? Collections.emptySet() : popped;
        } catch (Exception e) {
            Log.warnf("Redis SPOP failed for key=%s: %s", key, e.getMessage());
            return Collections.emptySet();
        }
    }

    public long scard(String key) {
        try {
            return sets.scard(key);
        } catch (Exception e) {
            Log.warnf("Redis SCARD failed for key=%s: %s", key, e.getMessage());
            return -1L;
        }
    }

    public void zadd(String key, String member, double score) {
        try {
            sortedSets.zadd(key, score, member);
        } catch (Exception e) {
            Log.warnf("Redis ZADD failed for key=%s: %s", key, e.getMessage());
        }
    }

    public void zremrangebyscore(String key, double min, double max) {
        try {
            sortedSets.zremrangebyscore(key, ScoreRange.from(min, max));
        } catch (Exception e) {
            Log.warnf("Redis ZREMRANGEBYSCORE failed for key=%s: %s", key, e.getMessage());
        }
    }

    public Set<String> zrange(String key, long start, long end) {
        try {
            List<String> result = sortedSets.zrange(key, start, end);
            return result == null ? Collections.emptySet() : new LinkedHashSet<>(result);
        } catch (Exception e) {
            Log.warnf("Redis ZRANGE failed for key=%s: %s", key, e.getMessage());
            return Collections.emptySet();
        }
    }

    public long ttl(String key) {
        try {
            return keys.ttl(key);
        } catch (Exception e) {
            Log.warnf("Redis TTL failed for key=%s: %s", key, e.getMessage());
            return -2L;
        }
    }

    public Set<String> scanKeys(String pattern) {
        try {
            List<String> result = keys.keys(pattern);
            return result == null ? Collections.emptySet() : new LinkedHashSet<>(result);
        } catch (Exception e) {
            Log.warnf("Redis KEYS failed for pattern=%s: %s", pattern, e.getMessage());
            return null;
        }
    }
}
