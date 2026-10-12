package com.cndp.order.adapter;

import java.util.List;
import java.util.Map;

import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.NotFoundException;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import org.jboss.resteasy.reactive.ResponseStatus;
import org.jboss.resteasy.reactive.RestPath;
import org.jboss.resteasy.reactive.RestResponse;
import org.jboss.resteasy.reactive.server.ServerExceptionMapper;

import com.cndp.order.domain.OrderRepository;
import com.cndp.order.domain.PlaceOrderCmd;
import com.cndp.order.domain.PlaceOrderUseCase;

@Path("/orders")
@Produces(MediaType.APPLICATION_JSON)
public class OrderResource {

    @Inject
    PlaceOrderUseCase placeOrder;

    @Inject
    OrderRepository repo;

    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    @ResponseStatus(201)
    public OrderResponse createOrder(OrderRequest body) {
        String sku = body.sku() != null ? body.sku() : "";
        int quantity = body.quantity() != null ? body.quantity() : 0;
        return OrderResponse.of(placeOrder.execute(new PlaceOrderCmd(sku, quantity)));
    }

    @GET
    @Path("{id}")
    public OrderResponse getOrder(@RestPath String id) {
        return repo.findById(id).map(OrderResponse::of).orElseThrow(NotFoundException::new);
    }

    @GET
    public List<OrderResponse> listOrders() {
        return repo.listAll().stream().map(OrderResponse::of).toList();
    }

    /** The command's invariants reject bad input with IllegalArgumentException. */
    @ServerExceptionMapper
    public RestResponse<Map<String, String>> invalidCommand(IllegalArgumentException e) {
        return RestResponse.status(RestResponse.Status.fromStatusCode(422), Map.of("detail", e.getMessage()));
    }
}
