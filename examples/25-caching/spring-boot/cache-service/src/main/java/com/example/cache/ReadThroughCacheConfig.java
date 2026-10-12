package com.example.cache;

import java.time.Duration;
import java.util.Map;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.serializer.JacksonJsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext.SerializationPair;

/**
 * Read-through: the Spring Cache abstraction over Redis. {@code Cache.get(key, loader)} returns the
 * cached value or calls the loader on a miss and stores the result. Entries are plain JSON under
 * {@code rt:product:<id>}, with the configured TTL.
 */
@Configuration
class ReadThroughCacheConfig {

    static final String PRODUCTS = "read-through-products";

    @Bean
    RedisCacheManager cacheManager(RedisConnectionFactory connectionFactory, CacheServiceProperties properties) {
        var products = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofSeconds(properties.ttlSeconds()))
                .disableCachingNullValues()
                .computePrefixWith(cacheName -> "rt:product:")
                .serializeValuesWith(SerializationPair.fromSerializer(
                        new JacksonJsonRedisSerializer<>(ProductView.class)));
        return RedisCacheManager.builder(connectionFactory)
                .withInitialCacheConfigurations(Map.of(PRODUCTS, products))
                .disableCreateOnMissingCache()
                .build();
    }
}
