package com.cndp.order.adapter;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;

import com.cndp.order.domain.Order;
import com.cndp.order.domain.OrderRepository;
import com.cndp.order.domain.PlaceOrderCmd;
import com.cndp.order.domain.PlaceOrderUseCase;

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
public class OrderResource {

    @Inject
    PlaceOrderUseCase placeOrder;

    @Inject
    OrderRepository repo;

    @GET
    @Path("healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @POST
    @Path("orders")
    @Consumes(MediaType.APPLICATION_JSON)
    public Response createOrder(Map<String, Object> body) {
        String sku = body.get("sku") != null ? body.get("sku").toString() : "";
        int quantity = 0;
        if (body.get("quantity") != null) {
            try {
                quantity = ((Number) body.get("quantity")).intValue();
            } catch (ClassCastException e) {
                // leave at 0
            }
        }

        try {
            PlaceOrderCmd cmd = new PlaceOrderCmd(sku, quantity);
            Order order = placeOrder.execute(cmd);
            return Response.status(Response.Status.CREATED).entity(toMap(order)).build();
        } catch (IllegalArgumentException e) {
            return Response.status(422).entity(Map.of("detail", e.getMessage())).build();
        }
    }

    @GET
    @Path("orders/{id}")
    public Response getOrder(@PathParam("id") String id) {
        return repo.findById(id)
                .map(order -> Response.ok(toMap(order)).build())
                .orElse(Response.status(Response.Status.NOT_FOUND).build());
    }

    @GET
    @Path("orders")
    public List<Map<String, Object>> listOrders() {
        return repo.listAll().stream().map(this::toMap).collect(Collectors.toList());
    }

    private Map<String, Object> toMap(Order o) {
        var map = new LinkedHashMap<String, Object>();
        map.put("id", o.id());
        map.put("sku", o.sku());
        map.put("quantity", o.quantity());
        map.put("status", o.status());
        return map;
    }
}
