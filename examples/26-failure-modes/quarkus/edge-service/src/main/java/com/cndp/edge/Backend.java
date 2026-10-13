package com.cndp.edge;

import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import io.smallrye.faulttolerance.api.CircuitBreakerMaintenance;
import io.smallrye.faulttolerance.api.CircuitBreakerName;
import io.smallrye.faulttolerance.api.ExponentialBackoff;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.ws.rs.ProcessingException;
import jakarta.ws.rs.WebApplicationException;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.faulttolerance.Bulkhead;
import org.eclipse.microprofile.faulttolerance.CircuitBreaker;
import org.eclipse.microprofile.faulttolerance.Fallback;
import org.eclipse.microprofile.faulttolerance.Retry;
import org.eclipse.microprofile.faulttolerance.exceptions.CircuitBreakerOpenException;
import org.eclipse.microprofile.rest.client.inject.RestClient;

/**
 * Calls to the backend, each guarded by SmallRye Fault Tolerance. The annotations are CDI interceptors, so they sit
 * on this bean and the resource calls through it.
 */
@ApplicationScoped
public class Backend {

    static final int BULKHEAD = 5;

    private final BackendClient client;
    private final CircuitBreakerMaintenance breakers;

    public Backend(@RestClient BackendClient client, CircuitBreakerMaintenance breakers) {
        this.client = client;
        this.breakers = breakers;
    }

    public Response process() {
        return client.process();
    }

    /** Retried on a 5xx or a timeout: 3 attempts, 100 ms doubling to 2 s, with up to 50 ms of jitter. */
    @Retry(maxRetries = 2, delay = 100, jitter = 50,
            retryOn = {WebApplicationException.class, ProcessingException.class})
    @ExponentialBackoff(factor = 2, maxDelay = 2000)
    public Response processWithRetry(AtomicInteger attempts) {
        attempts.incrementAndGet();
        return client.process();
    }

    /** 5 failed calls open the breaker for 10 s; 2 successful trial calls close it. */
    @CircuitBreaker(requestVolumeThreshold = 5, failureRatio = 1.0, delay = 10, delayUnit = ChronoUnit.SECONDS,
            successThreshold = 2)
    @CircuitBreakerName("backend")
    @Fallback(fallbackMethod = "fallback")
    public Map<String, Object> processWithBreaker() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("source", "live");
        result.put("body", client.process().readEntity(Map.class));
        result.put("breaker", breakerState());
        return result;
    }

    Map<String, Object> fallback(Throwable cause) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("source", "fallback");
        result.put("reason", switch (cause) {
            case CircuitBreakerOpenException ignored -> "circuit_open";
            case WebApplicationException e -> "upstream_" + e.getResponse().getStatus();
            default -> "upstream_unreachable";
        });
        result.put("breaker", breakerState());
        return result;
    }

    /** At most 5 calls in flight; the sixth fails at once with BulkheadException (429 in the resource). */
    @Bulkhead(BULKHEAD)
    public Response processInBulkhead() {
        return client.process();
    }

    /** closed, open or half-open. */
    public String breakerState() {
        return breakers.currentState("backend").name().toLowerCase().replace('_', '-');
    }
}
