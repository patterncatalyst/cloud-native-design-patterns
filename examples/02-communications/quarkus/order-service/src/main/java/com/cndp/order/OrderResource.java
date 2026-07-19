package com.cndp.order;

import com.cndp.proto.Inventory;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.agroal.api.AgroalDataSource;
import io.quarkus.grpc.GrpcClient;
import io.smallrye.mutiny.Uni;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.reactive.messaging.Channel;
import org.eclipse.microprofile.reactive.messaging.Emitter;
import org.jboss.logging.Logger;

import java.sql.*;
import java.time.Duration;
import java.util.*;

@Path("/orders")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class OrderResource {

    private static final Logger LOG = Logger.getLogger(OrderResource.class);

    @Inject
    AgroalDataSource dataSource;

    @GrpcClient("inventory")
    Inventory inventoryClient;

    @Inject
    @Channel("order-placed")
    Emitter<String> orderPlacedEmitter;

    @Inject
    ObjectMapper objectMapper;

    @POST
    public Response createOrder(Map<String, Object> request) {
        String sku = (String) request.get("sku");
        Integer quantity = (Integer) request.get("quantity");

        // Validation
        if (sku == null || sku.trim().isEmpty()) {
            return Response.status(422)
                    .entity(Map.of("error", "sku cannot be empty"))
                    .build();
        }

        if (quantity == null || quantity <= 0 || quantity > 1000) {
            return Response.status(422)
                    .entity(Map.of("error", "quantity must be between 1 and 1000"))
                    .build();
        }

        try {
            // Call gRPC inventory service
            ReserveRequest reserveRequest = ReserveRequest.newBuilder()
                    .setSku(sku)
                    .setQuantity(quantity)
                    .build();

            ReserveReply reserveReply = inventoryClient.reserveStock(reserveRequest)
                    .await()
                    .atMost(Duration.ofSeconds(5));

            String status = reserveReply.getReserved() ? "confirmed" : "rejected";
            String orderId = UUID.randomUUID().toString();

            // Insert into database
            try (Connection conn = dataSource.getConnection();
                 PreparedStatement stmt = conn.prepareStatement(
                         "INSERT INTO orders (id, sku, quantity, status) VALUES (?, ?, ?, ?)")) {
                stmt.setString(1, orderId);
                stmt.setString(2, sku);
                stmt.setInt(3, quantity);
                stmt.setString(4, status);
                stmt.executeUpdate();
            }

            Order order = new Order(orderId, sku, quantity, status);

            // Publish to Kafka
            Map<String, Object> event = Map.of(
                    "id", orderId,
                    "sku", sku,
                    "quantity", quantity,
                    "status", status
            );
            String eventJson = objectMapper.writeValueAsString(event);
            orderPlacedEmitter.send(eventJson);

            LOG.infof("Created order: %s", orderId);
            return Response.status(201).entity(order).build();

        } catch (Exception e) {
            LOG.error("Error creating order", e);
            return Response.serverError()
                    .entity(Map.of("error", e.getMessage()))
                    .build();
        }
    }

    @GET
    public Response listOrders(
            @QueryParam("after") String after,
            @QueryParam("limit") @DefaultValue("10") int limit) {

        try (Connection conn = dataSource.getConnection()) {
            String sql;
            PreparedStatement stmt;

            if (after != null && !after.isEmpty()) {
                sql = "SELECT id, sku, quantity, status FROM orders WHERE id > ? ORDER BY id LIMIT ?";
                stmt = conn.prepareStatement(sql);
                stmt.setString(1, after);
                stmt.setInt(2, limit + 1);
            } else {
                sql = "SELECT id, sku, quantity, status FROM orders ORDER BY id LIMIT ?";
                stmt = conn.prepareStatement(sql);
                stmt.setInt(1, limit + 1);
            }

            List<Order> orders = new ArrayList<>();
            try (ResultSet rs = stmt.executeQuery()) {
                while (rs.next()) {
                    orders.add(new Order(
                            rs.getString("id"),
                            rs.getString("sku"),
                            rs.getInt("quantity"),
                            rs.getString("status")
                    ));
                }
            }
            stmt.close();

            String nextCursor = null;
            if (orders.size() > limit) {
                nextCursor = orders.get(limit - 1).id;
                orders = orders.subList(0, limit);
            }

            Map<String, Object> response = new HashMap<>();
            response.put("items", orders);
            response.put("next_cursor", nextCursor);

            return Response.ok(response).build();

        } catch (SQLException e) {
            LOG.error("Error listing orders", e);
            return Response.serverError()
                    .entity(Map.of("error", e.getMessage()))
                    .build();
        }
    }
}
