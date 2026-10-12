package com.cndp.edge;

import java.net.URI;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.quarkus.rest.client.reactive.QuarkusRestClientBuilder;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.ws.rs.DefaultValue;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.WebApplicationException;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.eclipse.microprofile.rest.client.inject.RestClient;
import org.jboss.resteasy.reactive.RestQuery;

@Path("/")
@ApplicationScoped
@Produces(MediaType.APPLICATION_JSON)
public class EdgeResource {

    private static final Random random = new Random();

    private final BackendClient backend;
    private final String backendUrl;
    private final ObjectMapper mapper;
    private final CircuitBreaker breaker = new CircuitBreaker("backend", 5, 10);
    private final Semaphore bulkheadSemaphore = new Semaphore(5);
    private final AtomicInteger bulkheadActive = new AtomicInteger(0);
    private final AtomicInteger bulkheadRejected = new AtomicInteger(0);

    public EdgeResource(
            @RestClient BackendClient backend,
            @ConfigProperty(name = "quarkus.rest-client.backend.url") String backendUrl,
            ObjectMapper mapper) {
        this.backend = backend;
        this.backendUrl = backendUrl;
        this.mapper = mapper;
    }

    @GET
    @Path("with-timeout")
    public Map<String, Object> withTimeout() {
        long start = System.nanoTime();
        try {
            Response response = call(backend::call);

            double elapsed = elapsedSeconds(start);
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("status", response.getStatus());
            result.put("elapsed_s", elapsed);
            result.put("body", parseBody(response.readEntity(String.class)));
            return result;
        } catch (Exception e) {
            double elapsed = elapsedSeconds(start);
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("error", "timeout");
            result.put("elapsed_s", elapsed);
            result.put("pattern", "timeout");
            return result;
        }
    }

    @GET
    @Path("with-retry")
    public Map<String, Object> withRetry() {
        long start = System.nanoTime();
        int attempts = 0;
        String lastError = null;
        double wait = 0.1;

        for (int attempt = 1; attempt <= 3; attempt++) {
            attempts = attempt;
            try {
                Response response = call(backend::call);

                int statusCode = response.getStatus();
                if (statusCode < 500) {
                    double elapsed = elapsedSeconds(start);
                    Map<String, Object> result = new LinkedHashMap<>();
                    result.put("status", statusCode);
                    result.put("attempts", attempts);
                    result.put("elapsed_s", elapsed);
                    result.put("body", parseBody(response.readEntity(String.class)));
                    return result;
                }
                lastError = "HTTP " + statusCode;
            } catch (Exception e) {
                lastError = isTimeout(e) ? "timeout" : "error: " + e.getMessage();
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

    @GET
    @Path("with-breaker")
    public Map<String, Object> withBreaker() {
        if (!breaker.allow()) {
            breaker.incrementRejected();
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("source", "fallback");
            result.put("reason", "circuit_open");
            result.put("breaker", breaker.getState());
            return result;
        }

        try {
            Response response = call(backend::call);

            int statusCode = response.getStatus();
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
            result.put("body", parseBody(response.readEntity(String.class)));
            result.put("breaker", breaker.getState());
            return result;
        } catch (Exception e) {
            breaker.recordFailure();
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("source", "fallback");
            result.put("reason", "upstream_unreachable");
            result.put("breaker", breaker.getState());
            return result;
        }
    }

    @GET
    @Path("with-deadline")
    public Map<String, Object> withDeadline(
            @RestQuery("budget_ms") @DefaultValue("1000") int budgetMs) {

        long start = System.nanoTime();
        int edgeOverhead = 50;
        int remaining = budgetMs - edgeOverhead;

        if (budgetMs < 100) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("error", "deadline_exceeded");
            result.put("reason", "insufficient budget at edge");
            result.put("budget_ms", budgetMs);
            result.put("remaining_ms", remaining);
            return result;
        }

        try {
            // The budget is per request, so this client gets its own read timeout.
            BackendClient budgeted = QuarkusRestClientBuilder.newBuilder()
                    .baseUri(URI.create(backendUrl))
                    .readTimeout(remaining, TimeUnit.MILLISECONDS)
                    .build(BackendClient.class);
            Response response = call(() -> budgeted.call(String.valueOf(remaining)));

            double elapsed = elapsedSeconds(start);
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("status", response.getStatus());
            result.put("budget_ms", budgetMs);
            result.put("remaining_ms", remaining);
            result.put("elapsed_s", elapsed);
            result.put("body", parseBody(response.readEntity(String.class)));
            return result;
        } catch (Exception e) {
            double elapsed = elapsedSeconds(start);
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("error", "deadline_exceeded");
            result.put("reason", "timed out waiting for backend");
            result.put("budget_ms", budgetMs);
            result.put("elapsed_s", elapsed);
            return result;
        }
    }

    @GET
    @Path("with-bulkhead")
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
            Response response = call(backend::call);

            int statusCode = response.getStatus();
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("status", statusCode);
            result.put("body", parseBody(response.readEntity(String.class)));
            result.put("active_slots", bulkheadActive.get());
            return result;
        } catch (Exception e) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("error", isTimeout(e) ? "timeout" : "error");
            result.put("active_slots", bulkheadActive.get());
            return result;
        } finally {
            bulkheadActive.decrementAndGet();
            bulkheadSemaphore.release();
        }
    }

    @GET
    @Path("breaker-state")
    public Map<String, Object> breakerState() {
        return breaker.info();
    }

    @GET
    @Path("bulkhead-state")
    public Map<String, Object> bulkheadState() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("max_concurrent", 5);
        result.put("active", bulkheadActive.get());
        result.put("rejected", bulkheadRejected.get());
        return result;
    }

    /** Runs a backend call; a 4xx/5xx comes back as a Response so its body can be reported. */
    private Response call(Supplier<Response> invocation) {
        try {
            return invocation.get();
        } catch (WebApplicationException e) {
            return e.getResponse();
        }
    }

    private boolean isTimeout(Throwable e) {
        for (Throwable t = e; t != null; t = t.getCause()) {
            if (t instanceof TimeoutException || t.getClass().getSimpleName().contains("Timeout")) {
                return true;
            }
        }
        return false;
    }

    private Map<String, Object> parseBody(String body) {
        try {
            return mapper.readValue(body, new TypeReference<Map<String, Object>>() {});
        } catch (Exception e) {
            return Map.of("raw", body);
        }
    }

    private double elapsedSeconds(long startNanos) {
        return Math.round((System.nanoTime() - startNanos) / 1_000_000.0) / 1000.0;
    }
}
