package com.example.cache;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/** Cache TTL and the periods of the two background tasks. */
@ConfigurationProperties("cache-service")
public record CacheServiceProperties(
        @DefaultValue("60") long ttlSeconds,
        @DefaultValue("1000") long flushPeriodMs,
        @DefaultValue("5000") long refreshPeriodMs,
        @DefaultValue("10") long refreshBeforeSeconds) {
}
