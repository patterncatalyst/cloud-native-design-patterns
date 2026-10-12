package com.cndp.order;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.Map;

import io.quarkus.logging.Log;
import io.quarkus.panache.common.Sort;
import jakarta.transaction.Transactional;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.jboss.resteasy.reactive.RestQuery;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
public class OrderResource {

    @ConfigProperty(name = "service.version")
    String serviceVersion;

    @GET
    public Map<String, String> root() {
        return Map.of(
                "service", "order-service",
                "version", serviceVersion,
                "config_source", "environment");
    }

    @GET
    @Path("orders")
    public List<OrderDto> listOrders() {
        return Order.<Order>listAll(Sort.by("id")).stream().map(OrderDto::of).toList();
    }

    @POST
    @Path("orders")
    @Transactional
    public OrderDto createOrder(@RestQuery String customer, @RestQuery BigDecimal total) {
        var order = new Order();
        order.customer = customer;
        order.total = total.setScale(2, RoundingMode.HALF_UP);
        order.persist();
        Log.infof("order_created id=%s customer=%s total=%s", order.id, order.customer, order.total);
        return OrderDto.of(order);
    }
}
