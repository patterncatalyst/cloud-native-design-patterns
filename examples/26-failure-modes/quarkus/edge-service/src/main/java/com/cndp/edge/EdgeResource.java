package com.cndp.edge;

import java.net.URI;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import io.quarkus.rest.client.reactive.QuarkusRestClientBuilder;
import jakarta.ws.rs.DefaultValue;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.ProcessingException;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.WebApplicationException;
import jakarta.ws.rs.core.MediaType;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.eclipse.microprofile.faulttolerance.exceptions.BulkheadException;
import org.jboss.resteasy.reactive.RestQuery;
import org.jboss.resteasy.reactive.RestResponse;
import org.jboss.resteasy.reactive.server.ServerExceptionMapper;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
public class EdgeResource {

    private final Backend backend;
    private final String backendUrl;

    public EdgeResource(Backend backend, @ConfigProperty(name = "quarkus.rest-client.backend.url") String backendUrl) {
        this.backend = backend;
        this.backendUrl = backendUrl;
    }

    // 1. Timeout: quarkus.rest-client.backend.read-timeout gives up after 2 s.
    @GET
    @Path("with-timeout")
    public Map<String, Object> withTimeout() {
        long start = System.nanoTime();
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            var response = backend.process();
            result.put("status", response.getStatus());
            result.put("elapsed_s", elapsedSeconds(start));
            result.put("body", response.readEntity(Map.class));
        } catch (ProcessingException e) {
            result.put("error", "timeout");
            result.put("elapsed_s", elapsedSeconds(start));
            result.put("pattern", "timeout");
        }
        return result;
    }

    // 2. Retry with exponential backoff and jitter (@Retry on Backend).
    @GET
    @Path("with-retry")
    public Map<String, Object> withRetry() {
        long start = System.nanoTime();
        var attempts = new AtomicInteger();
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            var response = backend.processWithRetry(attempts);
            result.put("status", response.getStatus());
            result.put("attempts", attempts.get());
            result.put("elapsed_s", elapsedSeconds(start));
            result.put("body", response.readEntity(Map.class));
        } catch (WebApplicationException | ProcessingException e) {
            result.put("error", e instanceof WebApplicationException http
                    ? "HTTP " + http.getResponse().getStatus() : "timeout");
            result.put("attempts", attempts.get());
            result.put("elapsed_s", elapsedSeconds(start));
            result.put("pattern", "retry-exhausted");
        }
        return result;
    }

    // 3. Circuit breaker with a fallback (@CircuitBreaker and @Fallback on Backend).
    @GET
    @Path("with-breaker")
    public Map<String, Object> withBreaker() {
        return backend.processWithBreaker();
    }

    // 4. Deadline propagation: the backend gets what is left of the caller's budget.
    @GET
    @Path("with-deadline")
    public Map<String, Object> withDeadline(@RestQuery("budget_ms") @DefaultValue("1000") int budgetMs) {
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
        try {
            // The budget is per request, so this client gets its own read timeout.
            BackendClient budgeted = QuarkusRestClientBuilder.newBuilder()
                    .baseUri(URI.create(backendUrl))
                    .readTimeout(remaining, TimeUnit.MILLISECONDS)
                    .build(BackendClient.class);
            var response = budgeted.process(String.valueOf(remaining));
            result.put("status", response.getStatus());
            result.put("budget_ms", budgetMs);
            result.put("remaining_ms", remaining);
            result.put("elapsed_s", elapsedSeconds(start));
            result.put("body", response.readEntity(Map.class));
        } catch (ProcessingException e) {
            result.put("error", "deadline_exceeded");
            result.put("reason", "timed out waiting for backend");
            result.put("budget_ms", budgetMs);
            result.put("elapsed_s", elapsedSeconds(start));
        }
        return result;
    }

    // 5. Bulkhead: at most 5 calls in flight (@Bulkhead on Backend).
    @GET
    @Path("with-bulkhead")
    public Map<String, Object> withBulkhead() {
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            var response = backend.processInBulkhead();
            result.put("status", response.getStatus());
            result.put("body", response.readEntity(Map.class));
        } catch (WebApplicationException e) {
            result.put("status", e.getResponse().getStatus());
        } catch (ProcessingException e) {
            result.put("error", "timeout");
        }
        return result;
    }

    @ServerExceptionMapper
    public RestResponse<Map<String, Object>> bulkheadFull(BulkheadException e) {
        return RestResponse.status(RestResponse.Status.TOO_MANY_REQUESTS,
                Map.of("error", "bulkhead_full", "pattern", "bulkhead"));
    }

    // State endpoints.
    @GET
    @Path("breaker-state")
    public Map<String, Object> breakerState() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("name", "backend");
        result.put("state", backend.breakerState());
        return result;
    }

    @GET
    @Path("bulkhead-state")
    public Map<String, Object> bulkheadState() {
        return Map.of("max_concurrent", Backend.BULKHEAD);
    }

    private static double elapsedSeconds(long startNanos) {
        return Math.round((System.nanoTime() - startNanos) / 1_000_000.0) / 1000.0;
    }
}
