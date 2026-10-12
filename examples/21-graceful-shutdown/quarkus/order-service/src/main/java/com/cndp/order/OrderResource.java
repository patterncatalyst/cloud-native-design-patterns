package com.cndp.order;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import io.quarkus.logging.Log;
import io.quarkus.panache.common.Page;
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

@Path("/")
@Produces(MediaType.APPLICATION_JSON)
public class OrderResource {

    @Inject
    ShutdownState shutdownState;

    @POST
    @Path("orders")
    @Consumes(MediaType.APPLICATION_JSON)
    @Transactional
    public Response placeOrder(OrderRequest request) {
        shutdownState.incrementInFlight();
        try {
            if (shutdownState.isShuttingDown()) {
                return Response.status(503).entity(Map.of("error", "shutting down")).build();
            }
            var entity = new OrderEntity();
            entity.sku = request.sku();
            entity.quantity = request.quantity();
            entity.status = "confirmed";
            entity.persist();
            Log.infof("order_created id=%s sku=%s quantity=%d", entity.id, entity.sku, entity.quantity);
            return Response.status(201).entity(entity.toDto()).build();
        } finally {
            shutdownState.decrementInFlight();
        }
    }

    @GET
    @Path("orders")
    public List<Order> listOrders() {
        return OrderEntity.<OrderEntity>findAll(Sort.descending("createdAt"))
                .page(Page.ofSize(50)).list().stream().map(OrderEntity::toDto).toList();
    }

    @GET
    @Path("debug/state")
    public Map<String, Object> debugState() {
        var state = new LinkedHashMap<String, Object>();
        state.put("shutting_down", shutdownState.isShuttingDown());
        state.put("in_flight", shutdownState.getInFlight());
        state.put("pid", ProcessHandle.current().pid());
        return state;
    }
}
