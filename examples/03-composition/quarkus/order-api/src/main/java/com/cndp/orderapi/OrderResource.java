package com.cndp.orderapi;

import java.util.List;

import io.quarkus.logging.Log;
import jakarta.transaction.Transactional;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.NotFoundException;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import org.jboss.resteasy.reactive.RestPath;
import org.jboss.resteasy.reactive.RestQuery;

@Path("/orders")
@Produces(MediaType.APPLICATION_JSON)
public class OrderResource {

    @GET
    @Transactional
    public List<Order> getOrders(@RestQuery Integer limit) {
        int maxResults = limit != null ? limit : 10;
        List<Order> orders = OrderEntity.<OrderEntity>findAll().page(0, maxResults).list()
                .stream().map(OrderEntity::toDto).toList();
        Log.infof("Fetched %d orders", orders.size());
        return orders;
    }

    @GET
    @Path("{orderId}")
    @Transactional
    public Order getOrder(@RestPath String orderId) {
        OrderEntity entity = OrderEntity.findById(orderId);
        if (entity == null) {
            Log.warnf("Order not found: %s", orderId);
            throw new NotFoundException();
        }
        Log.infof("Fetched order: %s", orderId);
        return entity.toDto();
    }
}
