package com.cndp.order;

import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.DefaultValue;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.container.ContainerRequestContext;
import jakarta.ws.rs.core.Context;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

import org.eclipse.microprofile.faulttolerance.exceptions.BulkheadException;
import org.jboss.resteasy.reactive.RestQuery;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
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

    @POST
    @Path("orders")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response createOrder(OrderRequest body, @Context ContainerRequestContext ctx) {
        String identity = (String) ctx.getProperty(SidecarTrustFilter.IDENTITY_PROPERTY);
        String subject = (String) ctx.getProperty(SidecarTrustFilter.SUBJECT_PROPERTY);

        try {
            return bulkhead.run(body.tenant(), () -> placeOrder(body, identity, subject), Response.class);
        } catch (BulkheadException e) {   // the tenant's 5 permits are taken: refuse at once
            return Response.status(429).entity(Map.of("detail", "tenant bulkhead full")).build();
        }
    }

    private Response placeOrder(OrderRequest body, String identity, String subject) {
        try {
            Thread.sleep(body.processingTimeMs());   // simulated processing time
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
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
    }

    @POST
    @Path("valet-key")
    public Map<String, Object> mintValetKey(
            @RestQuery String resource,
            @RestQuery @DefaultValue("GET") String operation) {
        return valetKeyService.mint(resource, operation);
    }

    @GET
    @Path("verify-valet")
    public Response verifyValetKey(
            @RestQuery String resource,
            @RestQuery String operation,
            @RestQuery long expires,
            @RestQuery String token) {
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
