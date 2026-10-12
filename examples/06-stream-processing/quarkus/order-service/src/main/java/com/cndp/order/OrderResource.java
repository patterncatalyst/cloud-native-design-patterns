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
    public Response placeOrder(OrderRequest request) {
        var entity = new OrderEntity();
        entity.id = UUID.randomUUID().toString();
        entity.merchantId = request.merchantId();
        entity.sku = request.sku();
        entity.quantity = request.quantity();
        entity.total = request.total();
        entity.status = "confirmed";
        QuarkusTransaction.requiringNew().run(entity::persist);

        orderPlacedEmitter.send(new OrderPlaced(entity.id, entity.merchantId, entity.sku, entity.quantity,
                entity.total, entity.status));
        Log.infof("published order.placed id=%s merchant=%s total=%s", entity.id, entity.merchantId, entity.total);

        return Response.status(Response.Status.CREATED).entity(entity.toResponse()).build();
    }

    @GET
    @Transactional
    public List<OrderResponse> listOrders() {
        return OrderEntity.<OrderEntity>findAll(Sort.descending("createdAt")).page(0, 50).list()
                .stream().map(OrderEntity::toResponse).toList();
    }
}
