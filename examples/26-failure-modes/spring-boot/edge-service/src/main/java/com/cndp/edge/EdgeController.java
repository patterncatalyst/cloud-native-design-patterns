package com.cndp.edge;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import io.github.resilience4j.bulkhead.BulkheadFullException;
import io.github.resilience4j.bulkhead.BulkheadRegistry;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@RestController
public class EdgeController {

    private final BackendClient backend;
    private final CircuitBreakerRegistry breakers;
    private final BulkheadRegistry bulkheads;
    private final String backendUrl;

    public EdgeController(BackendClient backend, CircuitBreakerRegistry breakers, BulkheadRegistry bulkheads,
                          @Value("${BACKEND_URL:http://backend:8081}") String backendUrl) {
        this.backend = backend;
        this.breakers = breakers;
        this.bulkheads = bulkheads;
        this.backendUrl = backendUrl;
    }

    // 1. Timeout: the client gives up after 2 s.
    @GetMapping("/with-timeout")
    public Map<String, Object> withTimeout() {
        long start = System.nanoTime();
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            var response = backend.process();
            result.put("status", response.getStatusCode().value());
            result.put("elapsed_s", elapsedSeconds(start));
            result.put("body", response.getBody());
        } catch (ResourceAccessException e) {
            result.put("error", "timeout");
            result.put("elapsed_s", elapsedSeconds(start));
            result.put("pattern", "timeout");
        }
        return result;
    }

    // 2. Retry with exponential backoff and jitter (resilience4j.retry.instances.backend).
    @GetMapping("/with-retry")
    public Map<String, Object> withRetry() {
        long start = System.nanoTime();
        var attempts = new AtomicInteger();
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            var response = backend.processWithRetry(attempts);
            result.put("status", response.getStatusCode().value());
            result.put("attempts", attempts.get());
            result.put("elapsed_s", elapsedSeconds(start));
            result.put("body", response.getBody());
        } catch (RestClientException e) {
            result.put("error", e instanceof HttpServerErrorException http
                    ? "HTTP " + http.getStatusCode().value() : "timeout");
            result.put("attempts", attempts.get());
            result.put("elapsed_s", elapsedSeconds(start));
            result.put("pattern", "retry-exhausted");
        }
        return result;
    }

    // 3. Circuit breaker with a fallback (resilience4j.circuitbreaker.instances.backend).
    @GetMapping("/with-breaker")
    public Map<String, Object> withBreaker() {
        return backend.processWithBreaker();
    }

    // 4. Deadline propagation: the backend gets what is left of the caller's budget.
    @GetMapping("/with-deadline")
    public Map<String, Object> withDeadline(@RequestParam(value = "budget_ms", defaultValue = "1000") int budgetMs) {
        long start = System.nanoTime();
        int remaining = budgetMs - 50;   // edge overhead
        Map<String, Object> result = new LinkedHashMap<>();
        if (remaining < 50) {
            result.put("error", "deadline_exceeded");
            result.put("reason", "insufficient budget at edge");
            result.put("budget_ms", budgetMs);
            result.put("remaining_ms", remaining);
            return result;
        }
        var factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofMillis(remaining));
        factory.setReadTimeout(Duration.ofMillis(remaining));
        try {
            var response = RestClient.builder().requestFactory(factory).build().get()
                    .uri(backendUrl + "/process")
                    .header("X-Deadline-Ms", String.valueOf(remaining))
                    .retrieve()
                    .toEntity(Map.class);
            result.put("status", response.getStatusCode().value());
            result.put("budget_ms", budgetMs);
            result.put("remaining_ms", remaining);
            result.put("elapsed_s", elapsedSeconds(start));
            result.put("body", response.getBody());
        } catch (ResourceAccessException e) {
            result.put("error", "deadline_exceeded");
            result.put("reason", "timed out waiting for backend");
            result.put("budget_ms", budgetMs);
            result.put("elapsed_s", elapsedSeconds(start));
        }
        return result;
    }

    // 5. Bulkhead: at most 5 calls in flight (resilience4j.bulkhead.instances.backend).
    @GetMapping("/with-bulkhead")
    public Map<String, Object> withBulkhead() {
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            var response = backend.processInBulkhead();
            result.put("status", response.getStatusCode().value());
            result.put("body", response.getBody());
        } catch (HttpServerErrorException e) {
            result.put("status", e.getStatusCode().value());
        } catch (ResourceAccessException e) {
            result.put("error", "timeout");
        }
        return result;
    }

    @ExceptionHandler(BulkheadFullException.class)
    @ResponseStatus(HttpStatus.TOO_MANY_REQUESTS)
    public Map<String, Object> bulkheadFull() {
        return Map.of("error", "bulkhead_full", "pattern", "bulkhead");
    }

    // State endpoints, read from the Resilience4j registries.
    @GetMapping("/breaker-state")
    public Map<String, Object> breakerState() {
        var metrics = breakers.circuitBreaker("backend").getMetrics();
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("name", "backend");
        result.put("state", backend.breakerState());
        result.put("failure_rate", metrics.getFailureRate());
        result.put("buffered_calls", metrics.getNumberOfBufferedCalls());
        result.put("not_permitted_calls", metrics.getNumberOfNotPermittedCalls());
        return result;
    }

    @GetMapping("/bulkhead-state")
    public Map<String, Object> bulkheadState() {
        var bulkhead = bulkheads.bulkhead("backend");
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("max_concurrent", bulkhead.getBulkheadConfig().getMaxConcurrentCalls());
        result.put("available", bulkhead.getMetrics().getAvailableConcurrentCalls());
        return result;
    }

    private static double elapsedSeconds(long startNanos) {
        return Math.round((System.nanoTime() - startNanos) / 1_000_000.0) / 1000.0;
    }
}
