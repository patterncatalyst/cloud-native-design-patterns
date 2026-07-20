package com.cndp.order;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.agroal.api.AgroalDataSource;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.reactive.messaging.Channel;
import org.eclipse.microprofile.reactive.messaging.Emitter;
import org.jboss.logging.Logger;

import java.sql.*;
import java.util.*;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class OrderResource {

    private static final Logger log = Logger.getLogger(OrderResource.class);

    @Inject
    AgroalDataSource dataSource;

    @Inject
    ObjectMapper objectMapper;

    @Inject
    @Channel("order-placed")
    Emitter<String> orderPlacedEmitter;

    @GET
    @Path("healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @POST
    @Path("orders")
    public Response createOrder(Map<String, Object> body) throws Exception {
        String id = UUID.randomUUID().toString();
        String sku = (String) body.get("sku");
        int quantity = ((Number) body.get("quantity")).intValue();

        try (Connection conn = dataSource.getConnection();
             PreparedStatement ps = conn.prepareStatement(
                 "INSERT INTO orders (id, sku, quantity, status) VALUES (?, ?, ?, 'pending')")) {
            ps.setString(1, id);
            ps.setString(2, sku);
            ps.setInt(3, quantity);
            ps.executeUpdate();
        }
        log.infof("Order created: id=%s, sku=%s, quantity=%d", id, sku, quantity);

        Map<String, Object> event = Map.of(
            "id", id,
            "sku", sku,
            "quantity", quantity,
            "status", "pending"
        );
        orderPlacedEmitter.send(objectMapper.writeValueAsString(event));
        log.infof("Event published to order.placed: orderId=%s", id);

        Map<String, Object> response = Map.of(
            "id", id,
            "sku", sku,
            "quantity", quantity,
            "status", "pending"
        );
        return Response.status(Response.Status.CREATED).entity(response).build();
    }

    @GET
    @Path("orders")
    public List<Map<String, Object>> listOrders() throws Exception {
        List<Map<String, Object>> orders = new ArrayList<>();
        try (Connection conn = dataSource.getConnection();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT id, sku, quantity, status, created_at FROM orders ORDER BY created_at DESC")) {
            while (rs.next()) {
                Map<String, Object> order = new LinkedHashMap<>();
                order.put("id", rs.getString("id"));
                order.put("sku", rs.getString("sku"));
                order.put("quantity", rs.getInt("quantity"));
                order.put("status", rs.getString("status"));
                order.put("created_at", rs.getString("created_at"));
                orders.add(order);
            }
        }
        return orders;
    }
}
