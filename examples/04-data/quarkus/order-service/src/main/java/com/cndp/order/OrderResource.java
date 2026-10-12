package com.cndp.order;

import java.util.List;
import java.util.UUID;

import io.quarkus.panache.common.Sort;
import jakarta.transaction.Transactional;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

@Path("/orders")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class OrderResource {

    public record CreateOrderRequest(String sku, int quantity) {}

    /** The order row and its outbox row commit or roll back together. */
    @POST
    @Transactional
    public Response createOrder(CreateOrderRequest request) {
        var order = new OrderEntity();
        order.id = UUID.randomUUID().toString();
        order.sku = request.sku();
        order.quantity = request.quantity();
        order.status = "confirmed";
        order.persistAndFlush();

        var event = new OutboxEvent();
        event.aggregateId = order.id;
        event.eventType = "order.placed";
        event.payload = new OrderPlacedPayload(order.id, order.sku, order.quantity, order.status);
        event.persist();

        return Response.status(Response.Status.CREATED).entity(order.toView()).build();
    }

    @GET
    @Transactional
    public List<OrderView> listOrders() {
        return OrderEntity.<OrderEntity>listAll(Sort.descending("createdAt"))
                .stream().map(OrderEntity::toView).toList();
    }
}
