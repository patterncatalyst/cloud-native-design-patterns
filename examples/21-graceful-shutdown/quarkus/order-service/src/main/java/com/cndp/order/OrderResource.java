package com.cndp.order;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import javax.sql.DataSource;

import io.quarkus.logging.Log;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
public class OrderResource {

    @Inject
    DataSource dataSource;

    @Inject
    ShutdownState shutdownState;

    @GET
    @Path("healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @GET
    @Path("readyz")
    public Response readyz() {
        if (shutdownState.isShuttingDown()) {
            var body = new LinkedHashMap<String, Object>();
            body.put("ready", false);
            body.put("reason", "shutting down");
            return Response.status(503).entity(body).build();
        }
        try (var conn = dataSource.getConnection();
             var stmt = conn.createStatement();
             var rs = stmt.executeQuery("SELECT 1")) {
            return Response.ok(Map.of("ready", true)).build();
        } catch (Exception e) {
            var body = new LinkedHashMap<String, Object>();
            body.put("ready", false);
            body.put("reason", "db unreachable");
            return Response.status(503).entity(body).build();
        }
    }

    @POST
    @Path("orders")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response placeOrder(OrderRequest request) {
        shutdownState.incrementInFlight();
        try {
            if (shutdownState.isShuttingDown()) {
                return Response.status(503)
                        .entity(Map.of("error", "shutting down"))
                        .build();
            }

            String id = UUID.randomUUID().toString();
            try (var conn = dataSource.getConnection();
                 var stmt = conn.prepareStatement(
                         "INSERT INTO orders (id, sku, quantity, status) VALUES (?, ?, ?, 'confirmed')")) {
                stmt.setString(1, id);
                stmt.setString(2, request.sku());
                stmt.setInt(3, request.quantity());
                stmt.executeUpdate();
            }

            var order = new Order(id, request.sku(), request.quantity(), "confirmed");
            Log.infof("order_created id=%s sku=%s quantity=%d", id, request.sku(), request.quantity());
            return Response.status(201).entity(order).build();
        } catch (Exception e) {
            Log.errorf("order_failed: %s", e.getMessage());
            return Response.status(500)
                    .entity(Map.of("error", e.getMessage()))
                    .build();
        } finally {
            shutdownState.decrementInFlight();
        }
    }

    @GET
    @Path("orders")
    public List<Order> listOrders() throws Exception {
        var orders = new ArrayList<Order>();
        try (var conn = dataSource.getConnection();
             var stmt = conn.createStatement();
             var rs = stmt.executeQuery(
                     "SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT 50")) {
            while (rs.next()) {
                orders.add(new Order(
                        rs.getString("id"),
                        rs.getString("sku"),
                        rs.getInt("quantity"),
                        rs.getString("status")));
            }
        }
        return orders;
    }

    @GET
    @Path("debug/state")
    public Map<String, Object> debugState() {
        var state = new LinkedHashMap<String, Object>();
        state.put("shutting_down", shutdownState.isShuttingDown());
        state.put("in_flight", shutdownState.getInFlight());
        state.put("pid", ProcessHandle.current().pid());
        return state;
    }
}
