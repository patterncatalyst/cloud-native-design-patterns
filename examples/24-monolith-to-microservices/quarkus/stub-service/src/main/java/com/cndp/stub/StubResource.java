package com.cndp.stub;

import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class StubResource {

    @ConfigProperty(name = "service.name", defaultValue = "unknown")
    String serviceName;

    AtomicLong counter = new AtomicLong(0);
    ConcurrentHashMap<String, Map<String, Object>> orders = new ConcurrentHashMap<>();
    ConcurrentHashMap<String, AtomicLong> accessCounts = new ConcurrentHashMap<>();

    @GET
    @Path("healthz")
    public Response healthz() {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("status", "ok");
        response.put("source", serviceName);
        return Response.ok(response).build();
    }

    @POST
    @Path("orders")
    public Response createOrder(Map<String, Object> body) {
        long id = counter.incrementAndGet();
        String orderId = String.valueOf(id);

        Map<String, Object> order = new LinkedHashMap<>();
        order.put("id", orderId);
        order.put("sku", body.get("sku"));
        order.put("quantity", body.get("quantity"));
        order.put("tenant", body.get("tenant"));
        order.put("source", serviceName);

        orders.put(orderId, order);

        return Response.status(201).entity(order).build();
    }

    @GET
    @Path("orders/{orderId}")
    public Response getOrder(@PathParam("orderId") String orderId) {
        accessCounts.computeIfAbsent(orderId, k -> new AtomicLong(0)).incrementAndGet();

        Map<String, Object> order = orders.get(orderId);
        if (order != null) {
            return Response.ok(order).build();
        }

        Map<String, Object> stubOrder = new LinkedHashMap<>();
        stubOrder.put("id", orderId);
        stubOrder.put("source", serviceName);
        stubOrder.put("status", "stub");

        return Response.ok(stubOrder).build();
    }

    @GET
    @Path("access-count/{orderId}")
    public Response getAccessCount(@PathParam("orderId") String orderId) {
        long count = accessCounts.getOrDefault(orderId, new AtomicLong(0)).get();

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("order_id", orderId);
        response.put("count", count);

        return Response.ok(response).build();
    }
}
