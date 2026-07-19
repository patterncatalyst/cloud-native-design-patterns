package com.cndp.backend;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import io.quarkus.logging.Log;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.HeaderParam;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

@Path("/")
@ApplicationScoped
@Produces(MediaType.APPLICATION_JSON)
public class BackendResource {

    private final AtomicReference<String> mode = new AtomicReference<>("healthy");
    private final AtomicInteger callCount = new AtomicInteger(0);

    @POST
    @Path("mode")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response setMode(Map<String, String> body) {
        String newMode = body.get("mode");
        if (newMode == null || !newMode.matches("healthy|slow|failing")) {
            return Response.status(Response.Status.BAD_REQUEST)
                    .entity(Map.of("error", "mode must be healthy|slow|failing"))
                    .build();
        }
        mode.set(newMode);
        Log.infof("Mode set to: %s", newMode);
        return Response.ok(Map.of("mode", newMode)).build();
    }

    @GET
    @Path("mode")
    public Map<String, Object> getMode() {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("mode", mode.get());
        result.put("call_count", callCount.get());
        return result;
    }

    @GET
    @Path("call")
    public Response call(@HeaderParam("X-Deadline-Remaining") String deadlineRemaining) {
        callCount.incrementAndGet();
        String currentMode = mode.get();

        if (deadlineRemaining != null) {
            int remaining = Integer.parseInt(deadlineRemaining);
            if (remaining < 100) {
                Log.infof("Deadline too small (%dms), refusing", remaining);
                Map<String, Object> rejection = new LinkedHashMap<>();
                rejection.put("status", "rejected");
                rejection.put("reason", "deadline_too_small");
                rejection.put("remaining_ms", remaining);
                return Response.status(408).entity(rejection).build();
            }
        }

        switch (currentMode) {
            case "slow":
                try {
                    Thread.sleep(5000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                Map<String, Object> slowResult = new LinkedHashMap<>();
                slowResult.put("status", "ok");
                slowResult.put("mode", "slow");
                slowResult.put("delay", 5);
                return Response.ok(slowResult).build();

            case "failing":
                return Response.status(500)
                        .entity(Map.of("detail", "backend error"))
                        .build();

            default:
                try {
                    Thread.sleep(50);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                Map<String, Object> okResult = new LinkedHashMap<>();
                okResult.put("status", "ok");
                okResult.put("mode", "healthy");
                return Response.ok(okResult).build();
        }
    }

    @GET
    @Path("healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }
}
