package com.cndp.order;

import java.time.Duration;
import java.util.Map;
import java.util.UUID;

import com.cndp.proto.InventoryService;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.opentelemetry.api.trace.Span;
import io.quarkus.grpc.GrpcClient;
import io.quarkus.narayana.jta.QuarkusTransaction;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.reactive.messaging.Channel;
import org.eclipse.microprofile.reactive.messaging.Emitter;
import org.jboss.logging.Logger;
import org.jboss.logging.MDC;

@Path("/orders")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class OrderResource {

    private static final Logger log = Logger.getLogger(OrderResource.class);

    @GrpcClient("inventory")
    InventoryService inventoryClient;

    @Inject
    @Channel("order-placed")
    Emitter<Order> orderPlacedEmitter;

    @Inject
    MeterRegistry meterRegistry;

    @POST
    public Response placeOrder(OrderRequest request) {
        String sku = request.sku() != null ? request.sku() : "";
        int quantity = request.quantity() != null ? request.quantity() : 0;

        if (sku.isEmpty() || sku.length() > 64) {
            return Response.status(422).entity(Map.of("error", "invalid sku")).build();
        }
        if (quantity <= 0 || quantity > 1000) {
            return Response.status(422).entity(Map.of("error", "invalid quantity")).build();
        }

        ReserveReply reply = inventoryClient.reserveStock(
                ReserveRequest.newBuilder().setSku(sku).setQuantity(quantity).build())
                .await().atMost(Duration.ofSeconds(5));

        var entity = new OrderEntity();
        entity.id = UUID.randomUUID().toString();
        entity.sku = sku;
        entity.quantity = quantity;
        entity.status = reply.getConfirmed() ? "confirmed" : "rejected";
        QuarkusTransaction.requiringNew().run(entity::persist);

        Counter.builder("orders.placed")
                .description("Number of orders placed")
                .tag("sku", sku)
                .tag("status", entity.status)
                .register(meterRegistry)
                .increment();

        var order = new Order(entity.id, sku, quantity, entity.status);
        orderPlacedEmitter.send(order);

        String traceId = Span.current().getSpanContext().getTraceId();
        MDC.put("trace_id", traceId);
        log.infof("order placed id=%s sku=%s status=%s trace_id=%s", entity.id, sku, entity.status, traceId);
        MDC.remove("trace_id");

        return Response.status(Response.Status.CREATED).entity(order).build();
    }
}
