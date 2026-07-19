package com.cndp.order;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.agroal.api.AgroalDataSource;
import jakarta.inject.Inject;
import jakarta.transaction.Transactional;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

import java.sql.*;
import java.util.*;

@Path("/orders")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class OrderResource {

    @Inject
    AgroalDataSource dataSource;

    @Inject
    ObjectMapper objectMapper;

    public static class CreateOrderRequest {
        public String sku;
        public int quantity;
    }

    public static class Order {
        public String id;
        public String sku;
        public int quantity;
        public String status;
        public String created_at;
    }

    @POST
    @Transactional
    public Response createOrder(CreateOrderRequest request) throws Exception {
        String orderId = UUID.randomUUID().toString();
        String status = "confirmed";

        // 1. Insert order
        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(
                 "INSERT INTO orders (id, sku, quantity, status) VALUES (?, ?, ?, ?) RETURNING created_at")) {

            stmt.setString(1, orderId);
            stmt.setString(2, request.sku);
            stmt.setInt(3, request.quantity);
            stmt.setString(4, status);

            ResultSet rs = stmt.executeQuery();
            String createdAt = null;
            if (rs.next()) {
                createdAt = rs.getString(1);
            }

            // 2. Insert outbox event in same transaction
            Map<String, Object> payload = new HashMap<>();
            payload.put("order_id", orderId);
            payload.put("sku", request.sku);
            payload.put("quantity", request.quantity);
            payload.put("status", status);

            String payloadJson = objectMapper.writeValueAsString(payload);

            try (PreparedStatement outboxStmt = conn.prepareStatement(
                "INSERT INTO outbox (aggregate_id, event_type, payload) VALUES (?, ?, ?::jsonb)")) {

                outboxStmt.setString(1, orderId);
                outboxStmt.setString(2, "order.placed");
                outboxStmt.setString(3, payloadJson);
                outboxStmt.executeUpdate();
            }

            Order order = new Order();
            order.id = orderId;
            order.sku = request.sku;
            order.quantity = request.quantity;
            order.status = status;
            order.created_at = createdAt;

            return Response.status(Response.Status.CREATED).entity(order).build();
        }
    }

    @GET
    public List<Order> listOrders() throws Exception {
        List<Order> orders = new ArrayList<>();

        try (Connection conn = dataSource.getConnection();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT id, sku, quantity, status, created_at FROM orders ORDER BY created_at DESC")) {

            while (rs.next()) {
                Order order = new Order();
                order.id = rs.getString("id");
                order.sku = rs.getString("sku");
                order.quantity = rs.getInt("quantity");
                order.status = rs.getString("status");
                order.created_at = rs.getString("created_at");
                orders.add(order);
            }
        }

        return orders;
    }

}
