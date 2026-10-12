package com.cndp.order;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.cndp.proto.Inventory;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import com.fasterxml.jackson.annotation.JsonProperty;
import io.quarkus.grpc.GrpcClient;
import io.quarkus.narayana.jta.QuarkusTransaction;
import io.quarkus.panache.common.Sort;
import jakarta.inject.Inject;
import jakarta.transaction.Transactional;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.DefaultValue;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.reactive.messaging.Channel;
import org.eclipse.microprofile.reactive.messaging.Emitter;
import org.jboss.logging.Logger;
import org.jboss.resteasy.reactive.RestQuery;

@Path("/orders")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class OrderResource {

    private static final Logger LOG = Logger.getLogger(OrderResource.class);

    public record OrderPage(List<Order> items, @JsonProperty("next_cursor") String nextCursor) {}

    @GrpcClient("inventory")
    Inventory inventoryClient;

    @Inject
    @Channel("order-placed")
    Emitter<OrderPlaced> orderPlacedEmitter;

    @POST
    public Response createOrder(OrderRequest request) {
        String sku = request.sku();
        Integer quantity = request.quantity();

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
            ReserveReply reserveReply = inventoryClient.reserveStock(
                            ReserveRequest.newBuilder().setSku(sku).setQuantity(quantity).build())
                    .await()
                    .atMost(Duration.ofSeconds(5));

            var entity = new OrderEntity();
            entity.id = UUID.randomUUID().toString();
            entity.sku = sku;
            entity.quantity = quantity;
            entity.status = reserveReply.getReserved() ? "confirmed" : "rejected";
            QuarkusTransaction.requiringNew().run(entity::persist);

            orderPlacedEmitter.send(new OrderPlaced(entity.id, sku, quantity, entity.status));

            LOG.infof("Created order: %s", entity.id);
            return Response.status(201).entity(entity.toDto()).build();

        } catch (Exception e) {
            LOG.error("Error creating order", e);
            return Response.serverError()
                    .entity(Map.of("error", e.getMessage()))
                    .build();
        }
    }

    @GET
    @Transactional
    public OrderPage listOrders(@RestQuery String after, @RestQuery @DefaultValue("10") int limit) {
        var query = after == null || after.isEmpty()
                ? OrderEntity.<OrderEntity>findAll(Sort.by("id"))
                : OrderEntity.<OrderEntity>find("id > ?1", Sort.by("id"), after);
        List<Order> orders = query.page(0, limit + 1).list().stream().map(OrderEntity::toDto).toList();

        String nextCursor = null;
        if (orders.size() > limit) {
            nextCursor = orders.get(limit - 1).id();
            orders = orders.subList(0, limit);
        }
        return new OrderPage(orders, nextCursor);
    }
}
