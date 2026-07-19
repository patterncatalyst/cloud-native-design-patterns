package com.cndp.orderapi;

import io.agroal.api.AgroalDataSource;
import jakarta.inject.Inject;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.QueryParam;
import jakarta.ws.rs.core.Response;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.logging.Logger;

@Path("/")
public class OrderResource {

    private static final Logger log = Logger.getLogger(OrderResource.class.getName());

    @Inject
    AgroalDataSource dataSource;

    @GET
    @Path("/healthz")
    public Map<String, String> health() {
        return Map.of("status", "ok");
    }

    @GET
    @Path("/orders")
    public List<Order> getOrders(@QueryParam("limit") Integer limit) {
        int maxResults = limit != null ? limit : 10;
        List<Order> orders = new ArrayList<>();

        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(
                 "SELECT id, sku, quantity, status FROM orders LIMIT ?")) {

            stmt.setInt(1, maxResults);
            ResultSet rs = stmt.executeQuery();

            while (rs.next()) {
                orders.add(new Order(
                    rs.getString("id"),
                    rs.getString("sku"),
                    rs.getInt("quantity"),
                    rs.getString("status")
                ));
            }

            log.info("Fetched " + orders.size() + " orders");

        } catch (Exception e) {
            log.severe("Error fetching orders: " + e.getMessage());
            throw new RuntimeException("Database error", e);
        }

        return orders;
    }

    @GET
    @Path("/orders/{orderId}")
    public Response getOrder(@PathParam("orderId") String orderId) {
        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(
                 "SELECT id, sku, quantity, status FROM orders WHERE id = ?")) {

            stmt.setString(1, orderId);
            ResultSet rs = stmt.executeQuery();

            if (rs.next()) {
                Order order = new Order(
                    rs.getString("id"),
                    rs.getString("sku"),
                    rs.getInt("quantity"),
                    rs.getString("status")
                );
                log.info("Fetched order: " + orderId);
                return Response.ok(order).build();
            } else {
                log.warning("Order not found: " + orderId);
                return Response.status(404).build();
            }

        } catch (Exception e) {
            log.severe("Error fetching order: " + e.getMessage());
            throw new RuntimeException("Database error", e);
        }
    }
}
