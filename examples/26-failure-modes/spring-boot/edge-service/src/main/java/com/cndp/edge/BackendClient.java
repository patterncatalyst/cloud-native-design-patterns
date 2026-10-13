package com.cndp.edge;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import io.github.resilience4j.bulkhead.annotation.Bulkhead;
import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.retry.annotation.Retry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.RestClient;

/**
 * Calls to the backend, each guarded by a Resilience4j instance named "backend". The limits live in
 * application.properties (resilience4j.*); the annotations need a Spring proxy, so they sit on this bean
 * and the controller calls through it.
 */
@Component
public class BackendClient {

    private final RestClient rest;
    private final CircuitBreakerRegistry breakers;

    public BackendClient(RestClient.Builder builder, CircuitBreakerRegistry breakers,
                         @Value("${BACKEND_URL:http://backend:8081}") String backendUrl) {
        var factory = new SimpleClientHttpRequestFactory();   // timeout: every call gives up after 2 s
        factory.setConnectTimeout(Duration.ofSeconds(2));
        factory.setReadTimeout(Duration.ofSeconds(2));
        this.rest = builder.baseUrl(backendUrl).requestFactory(factory).build();
        this.breakers = breakers;
    }

    @SuppressWarnings("rawtypes")
    public ResponseEntity<Map> process() {
        return rest.get().uri("/process").retrieve().toEntity(Map.class);
    }

    /** Retried on a 5xx or a timeout with exponential backoff and jitter; counts every attempt. */
    @Retry(name = "backend")
    @SuppressWarnings("rawtypes")
    public ResponseEntity<Map> processWithRetry(AtomicInteger attempts) {
        attempts.incrementAndGet();
        return process();
    }

    /** Behind the breaker; an open breaker or a failed call answers from the fallback. */
    @CircuitBreaker(name = "backend", fallbackMethod = "fallback")
    public Map<String, Object> processWithBreaker() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("source", "live");
        result.put("body", process().getBody());
        result.put("breaker", breakerState());
        return result;
    }

    private Map<String, Object> fallback(Throwable cause) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("source", "fallback");
        result.put("reason", switch (cause) {
            case CallNotPermittedException ignored -> "circuit_open";
            case HttpServerErrorException e -> "upstream_" + e.getStatusCode().value();
            default -> "upstream_unreachable";
        });
        result.put("breaker", breakerState());
        return result;
    }

    /** At most 5 calls in flight; the sixth fails at once with BulkheadFullException (429 in the controller). */
    @Bulkhead(name = "backend")
    @SuppressWarnings("rawtypes")
    public ResponseEntity<Map> processInBulkhead() {
        return process();
    }

    /** closed, open or half-open. */
    public String breakerState() {
        return breakers.circuitBreaker("backend").getState().name().toLowerCase().replace('_', '-');
    }
}
