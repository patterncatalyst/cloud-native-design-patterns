package com.cndp.order;

import com.cndp.proto.InventoryService;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.agroal.api.AgroalDataSource;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.opentelemetry.api.trace.Span;
import io.quarkus.grpc.GrpcClient;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.reactive.messaging.Channel;
import org.eclipse.microprofile.reactive.messaging.Emitter;
import org.jboss.logging.Logger;
import org.jboss.logging.MDC;

import java.sql.*;
import java.time.Duration;
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

    @GrpcClient("inventory")
    InventoryService inventoryClient;

    @Inject
    @Channel("order-placed")
    Emitter<String> orderPlacedEmitter;

    @Inject
    MeterRegistry meterRegistry;

    @GET
    @Path("healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @POST
    @Path("orders")
    public Response placeOrder(Map<String, Object> body) throws Exception {
        String sku = body.get("sku") != null ? body.get("sku").toString() : "";
        int quantity = body.get("quantity") != null ? ((Number) body.get("quantity")).intValue() : 0;

        if (sku.isEmpty() || sku.length() > 64) {
            return Response.status(422).entity(Map.of("error", "invalid sku")).build();
        }
        if (quantity <= 0 || quantity > 1000) {
            return Response.status(422).entity(Map.of("error", "invalid quantity")).build();
        }

        ReserveReply reply = inventoryClient.reserveStock(
                ReserveRequest.newBuilder().setSku(sku).setQuantity(quantity).build())
                .await().atMost(Duration.ofSeconds(5));

        String status = reply.getConfirmed() ? "confirmed" : "rejected";
        String orderId = UUID.randomUUID().toString();

        try (Connection conn = dataSource.getConnection();
             PreparedStatement ps = conn.prepareStatement(
                 "INSERT INTO orders (id, sku, quantity, status) VALUES (?, ?, ?, ?)")) {
            ps.setString(1, orderId);
            ps.setString(2, sku);
            ps.setInt(3, quantity);
            ps.setString(4, status);
            ps.executeUpdate();
        }

        Counter.builder("orders.placed")
                .description("Number of orders placed")
                .tag("sku", sku)
                .tag("status", status)
                .register(meterRegistry)
                .increment();

        Map<String, Object> order = Map.of("id", orderId, "sku", sku, "quantity", quantity, "status", status);
        orderPlacedEmitter.send(objectMapper.writeValueAsString(order));

        String traceId = Span.current().getSpanContext().getTraceId();
        MDC.put("trace_id", traceId);
        log.infof("order placed id=%s sku=%s status=%s trace_id=%s", orderId, sku, status, traceId);
        MDC.remove("trace_id");

        return Response.status(Response.Status.CREATED).entity(order).build();
    }
}
