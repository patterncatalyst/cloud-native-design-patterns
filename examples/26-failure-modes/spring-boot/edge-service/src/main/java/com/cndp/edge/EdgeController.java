package com.cndp.edge;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.Semaphore;
import java.util.concurrent.atomic.AtomicInteger;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

@RestController
public class EdgeController {

    private static final Logger log = LoggerFactory.getLogger(EdgeController.class);
    private static final Random random = new Random();

    private final String backendUrl;
    private final CircuitBreaker breaker = new CircuitBreaker("backend", 5, 10);
    private final Semaphore bulkheadSemaphore = new Semaphore(5);
    private final AtomicInteger bulkheadActive = new AtomicInteger(0);
    private final AtomicInteger bulkheadRejected = new AtomicInteger(0);

    public EdgeController(@Value("${BACKEND_URL:http://backend:8081}") String backendUrl) {
        this.backendUrl = backendUrl;
    }

    // -----------------------------------------------------------------------
    // 1. Timeout
    // -----------------------------------------------------------------------
    @GetMapping("/with-timeout")
    public Map<String, Object> withTimeout() {
        long start = System.nanoTime();
        RestClient client = buildClient(2000, 2000);

        try {
            var response = client.get()
                    .uri(backendUrl + "/process")
                    .retrieve()
                    .toEntity(Map.class);

            double elapsed = elapsedSeconds(start);
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("status", response.getStatusCode().value());
            result.put("elapsed_s", elapsed);
            result.put("body", response.getBody());
            return result;
        } catch (ResourceAccessException e) {
            double elapsed = elapsedSeconds(start);
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("error", "timeout");
            result.put("elapsed_s", elapsed);
            result.put("pattern", "timeout");
            return result;
        }
    }

    // -----------------------------------------------------------------------
    // 2. Retry with exponential backoff + jitter
    // -----------------------------------------------------------------------
    @GetMapping("/with-retry")
    public Map<String, Object> withRetry() {
        long start = System.nanoTime();
        int attempts = 0;
        String lastError = null;
        double wait = 0.1;
        RestClient client = buildClient(2000, 2000);

        for (int attempt = 1; attempt <= 3; attempt++) {
            attempts = attempt;
            try {
                var response = client.get()
                        .uri(backendUrl + "/process")
                        .retrieve()
                        .toEntity(Map.class);

                int statusCode = response.getStatusCode().value();
                if (statusCode < 500) {
                    double elapsed = elapsedSeconds(start);
                    Map<String, Object> result = new LinkedHashMap<>();
                    result.put("status", statusCode);
                    result.put("attempts", attempts);
                    result.put("elapsed_s", elapsed);
                    result.put("body", response.getBody());
                    return result;
                }
                lastError = "HTTP " + statusCode;
            } catch (ResourceAccessException e) {
                lastError = "timeout";
            } catch (org.springframework.web.client.HttpServerErrorException e) {
                lastError = "HTTP " + e.getStatusCode().value();
            }

            if (attempt < 3) {
                double jitter = random.nextDouble() * wait * 0.5;
                try {
                    Thread.sleep((long) ((wait + jitter) * 1000));
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                }
                wait = Math.min(wait * 2, 2.0);
            }
        }

        double elapsed = elapsedSeconds(start);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("error", lastError);
        result.put("attempts", attempts);
        result.put("elapsed_s", elapsed);
        result.put("pattern", "retry-exhausted");
        return result;
    }

    // -----------------------------------------------------------------------
    // 3. Circuit breaker + fallback
    // -----------------------------------------------------------------------
    @GetMapping("/with-breaker")
    public Map<String, Object> withBreaker() {
        if (!breaker.allow()) {
            breaker.incrementRejected();
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("source", "fallback");
            result.put("reason", "circuit_open");
            result.put("breaker", breaker.getState());
            return result;
        }

        RestClient client = buildClient(2000, 2000);
        try {
            var response = client.get()
                    .uri(backendUrl + "/process")
                    .retrieve()
                    .toEntity(Map.class);

            int statusCode = response.getStatusCode().value();
            if (statusCode >= 500) {
                breaker.recordFailure();
                Map<String, Object> result = new LinkedHashMap<>();
                result.put("source", "fallback");
                result.put("reason", "upstream_" + statusCode);
                result.put("breaker", breaker.getState());
                return result;
            }
            breaker.recordSuccess();
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("source", "live");
            result.put("body", response.getBody());
            result.put("breaker", breaker.getState());
            return result;
        } catch (org.springframework.web.client.HttpServerErrorException e) {
            breaker.recordFailure();
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("source", "fallback");
            result.put("reason", "upstream_" + e.getStatusCode().value());
            result.put("breaker", breaker.getState());
            return result;
        } catch (ResourceAccessException e) {
            breaker.recordFailure();
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("source", "fallback");
            result.put("reason", "upstream_unreachable");
            result.put("breaker", breaker.getState());
            return result;
        }
    }

    // -----------------------------------------------------------------------
    // 4. Deadline propagation
    // -----------------------------------------------------------------------
    @GetMapping("/with-deadline")
    public Map<String, Object> withDeadline(
            @RequestParam(value = "budget_ms", defaultValue = "1000") int budgetMs) {

        long start = System.nanoTime();
        int edgeOverhead = 50;
        int remaining = budgetMs - edgeOverhead;

        if (remaining < 50) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("error", "deadline_exceeded");
            result.put("reason", "insufficient budget at edge");
            result.put("budget_ms", budgetMs);
            result.put("remaining_ms", remaining);
            return result;
        }

        RestClient client = buildClient(remaining, remaining);
        try {
            var response = client.get()
                    .uri(backendUrl + "/process")
                    .header("X-Deadline-Ms", String.valueOf(remaining))
                    .retrieve()
                    .toEntity(Map.class);

            double elapsed = elapsedSeconds(start);
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("status", response.getStatusCode().value());
            result.put("budget_ms", budgetMs);
            result.put("remaining_ms", remaining);
            result.put("elapsed_s", elapsed);
            result.put("body", response.getBody());
            return result;
        } catch (ResourceAccessException e) {
            double elapsed = elapsedSeconds(start);
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("error", "deadline_exceeded");
            result.put("reason", "timed out waiting for backend");
            result.put("budget_ms", budgetMs);
            result.put("elapsed_s", elapsed);
            return result;
        }
    }

    // -----------------------------------------------------------------------
    // 5. Bulkhead — bounded concurrency via semaphore
    // -----------------------------------------------------------------------
    @GetMapping("/with-bulkhead")
    public Map<String, Object> withBulkhead() {
        if (!bulkheadSemaphore.tryAcquire()) {
            bulkheadRejected.incrementAndGet();
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("error", "bulkhead_full");
            result.put("pattern", "bulkhead");
            result.put("active", bulkheadActive.get());
            return result;
        }

        bulkheadActive.incrementAndGet();
        try {
            RestClient client = buildClient(2000, 2000);
            var response = client.get()
                    .uri(backendUrl + "/process")
                    .retrieve()
                    .toEntity(Map.class);

            Map<String, Object> result = new LinkedHashMap<>();
            result.put("status", response.getStatusCode().value());
            result.put("body", response.getBody());
            result.put("active_slots", bulkheadActive.get());
            return result;
        } catch (org.springframework.web.client.HttpServerErrorException e) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("status", e.getStatusCode().value());
            result.put("active_slots", bulkheadActive.get());
            return result;
        } catch (ResourceAccessException e) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("error", "timeout");
            result.put("active_slots", bulkheadActive.get());
            return result;
        } finally {
            bulkheadActive.decrementAndGet();
            bulkheadSemaphore.release();
        }
    }

    // -----------------------------------------------------------------------
    // State endpoints
    // -----------------------------------------------------------------------
    @GetMapping("/breaker-state")
    public Map<String, Object> breakerState() {
        return breaker.info();
    }

    @GetMapping("/bulkhead-state")
    public Map<String, Object> bulkheadState() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("max_concurrent", 5);
        result.put("active", bulkheadActive.get());
        result.put("rejected", bulkheadRejected.get());
        return result;
    }

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------
    private RestClient buildClient(int connectTimeoutMs, int readTimeoutMs) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofMillis(connectTimeoutMs));
        factory.setReadTimeout(Duration.ofMillis(readTimeoutMs));
        return RestClient.builder().requestFactory(factory).build();
    }

    private double elapsedSeconds(long startNanos) {
        return Math.round((System.nanoTime() - startNanos) / 1_000_000.0) / 1000.0;
    }
}
