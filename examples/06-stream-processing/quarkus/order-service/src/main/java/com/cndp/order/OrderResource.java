package com.cndp.order;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.agroal.api.AgroalDataSource;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.reactive.messaging.Channel;
import org.eclipse.microprofile.reactive.messaging.Emitter;
import org.jboss.logging.Logger;

import java.math.BigDecimal;
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
    public Response placeOrder(OrderRequest request) throws Exception {
        String orderId = UUID.randomUUID().toString();

        try (Connection conn = dataSource.getConnection();
             PreparedStatement ps = conn.prepareStatement(
                 "INSERT INTO orders (id, merchant_id, sku, quantity, total, status) VALUES (?, ?, ?, ?, ?, 'confirmed')")) {
            ps.setString(1, orderId);
            ps.setString(2, request.merchantId);
            ps.setString(3, request.sku);
            ps.setInt(4, request.quantity);
            ps.setBigDecimal(5, request.total);
            ps.executeUpdate();
        }

        Map<String, Object> event = new LinkedHashMap<>();
        event.put("id", orderId);
        event.put("merchant_id", request.merchantId);
        event.put("sku", request.sku);
        event.put("quantity", request.quantity);
        event.put("total", request.total);
        event.put("status", "confirmed");
        orderPlacedEmitter.send(objectMapper.writeValueAsString(event));
        log.infof("published order.placed id=%s merchant=%s total=%s",
                orderId, request.merchantId, request.total);

        OrderResponse response = new OrderResponse(
            orderId, request.merchantId, request.sku,
            request.quantity, request.total, "confirmed"
        );
        return Response.status(Response.Status.CREATED).entity(response).build();
    }

    @GET
    @Path("orders")
    public List<OrderResponse> listOrders() throws Exception {
        List<OrderResponse> orders = new ArrayList<>();
        try (Connection conn = dataSource.getConnection();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(
                 "SELECT id, merchant_id, sku, quantity, total, status FROM orders ORDER BY created_at DESC LIMIT 50")) {
            while (rs.next()) {
                orders.add(new OrderResponse(
                    rs.getString("id"),
                    rs.getString("merchant_id"),
                    rs.getString("sku"),
                    rs.getInt("quantity"),
                    rs.getBigDecimal("total"),
                    rs.getString("status")
                ));
            }
        }
        return orders;
    }

    public static class OrderRequest {
        @JsonProperty("merchant_id")
        public String merchantId;
        public String sku;
        public int quantity;
        public BigDecimal total;
    }

    public static class OrderResponse {
        public String id;
        @JsonProperty("merchant_id")
        public String merchantId;
        public String sku;
        public int quantity;
        public BigDecimal total;
        public String status;

        public OrderResponse(String id, String merchantId, String sku,
                             int quantity, BigDecimal total, String status) {
            this.id = id;
            this.merchantId = merchantId;
            this.sku = sku;
            this.quantity = quantity;
            this.total = total;
            this.status = status;
        }
    }
}
