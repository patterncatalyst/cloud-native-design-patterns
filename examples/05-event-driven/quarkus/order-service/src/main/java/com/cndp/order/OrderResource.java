package com.cndp.order;

import java.util.List;
import java.util.UUID;

import io.quarkus.logging.Log;
import io.quarkus.narayana.jta.QuarkusTransaction;
import io.quarkus.panache.common.Sort;
import jakarta.inject.Inject;
import jakarta.transaction.Transactional;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.eclipse.microprofile.reactive.messaging.Channel;
import org.eclipse.microprofile.reactive.messaging.Emitter;

@Path("/orders")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class OrderResource {

    @Inject
    @Channel("order-placed")
    Emitter<OrderPlaced> orderPlacedEmitter;

    @POST
    public Response createOrder(OrderRequest request) {
        var entity = new OrderEntity();
        entity.id = UUID.randomUUID().toString();
        entity.sku = request.sku();
        entity.quantity = request.quantity();
        entity.status = "pending";
        QuarkusTransaction.requiringNew().run(entity::persist);
        Log.infof("Order created: id=%s, sku=%s, quantity=%d", entity.id, entity.sku, entity.quantity);

        orderPlacedEmitter.send(new OrderPlaced(entity.id, entity.sku, entity.quantity, entity.status));
        Log.infof("Event published to order.placed: orderId=%s", entity.id);

        return Response.status(Response.Status.CREATED)
                .entity(new Order(entity.id, entity.sku, entity.quantity, entity.status)).build();
    }

    @GET
    @Transactional
    public List<OrderView> listOrders() {
        return OrderEntity.<OrderEntity>listAll(Sort.descending("createdAt"))
                .stream().map(OrderEntity::toView).toList();
    }
}
