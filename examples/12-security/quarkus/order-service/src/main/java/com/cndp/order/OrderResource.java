package com.cndp.order;

import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.DefaultValue;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.QueryParam;
import jakarta.ws.rs.container.ContainerRequestContext;
import jakarta.ws.rs.core.Context;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
public class OrderResource {

    @Inject
    BulkheadService bulkhead;

    @Inject
    ValetKeyService valetKeyService;

    private final ConcurrentHashMap<String, Map<String, Object>> orders = new ConcurrentHashMap<>();
    private final AtomicInteger counter = new AtomicInteger(0);

    @GET
    @Path("healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @POST
    @Path("orders")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response createOrder(OrderRequest body, @Context ContainerRequestContext ctx) {
        String identity = (String) ctx.getProperty(SidecarTrustFilter.IDENTITY_PROPERTY);
        String subject = (String) ctx.getProperty(SidecarTrustFilter.SUBJECT_PROPERTY);

        Semaphore sem = bulkhead.forTenant(body.tenant());
        try {
            if (!sem.tryAcquire(5, TimeUnit.SECONDS)) {
                return Response.status(429)
                        .entity(Map.of("detail", "tenant bulkhead full"))
                        .build();
            }
            try {
                Thread.sleep(10);

                String id = String.valueOf(counter.incrementAndGet());
                Map<String, Object> order = new LinkedHashMap<>();
                order.put("id", id);
                order.put("sku", body.sku());
                order.put("quantity", body.quantity());
                order.put("tenant", body.tenant());
                order.put("identity", identity);
                order.put("jwt_sub", subject);

                orders.put(id, order);
                return Response.status(Response.Status.CREATED).entity(order).build();
            } finally {
                sem.release();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return Response.status(Response.Status.SERVICE_UNAVAILABLE)
                    .entity(Map.of("detail", "interrupted"))
                    .build();
        }
    }

    @POST
    @Path("valet-key")
    public Map<String, Object> mintValetKey(
            @QueryParam("resource") String resource,
            @QueryParam("operation") @DefaultValue("GET") String operation) {
        return valetKeyService.mint(resource, operation);
    }

    @GET
    @Path("verify-valet")
    public Response verifyValetKey(
            @QueryParam("resource") String resource,
            @QueryParam("operation") String operation,
            @QueryParam("expires") long expires,
            @QueryParam("token") String token) {
        if (valetKeyService.verify(resource, operation, expires, token)) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("valid", true);
            result.put("resource", resource);
            result.put("operation", operation);
            return Response.ok(result).build();
        }
        return Response.status(Response.Status.FORBIDDEN)
                .entity(Map.of("detail", "invalid or expired valet key"))
                .build();
    }

    @GET
    @Path("bulkhead-state")
    public Map<String, Map<String, Integer>> bulkheadState() {
        return bulkhead.state();
    }
}
