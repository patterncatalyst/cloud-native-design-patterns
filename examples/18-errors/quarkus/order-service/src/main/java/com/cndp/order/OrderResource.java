package com.cndp.order;

import java.util.UUID;

import com.cndp.proto.ReserveReply;
import io.smallrye.common.annotation.Blocking;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import org.jboss.resteasy.reactive.ResponseStatus;

@Path("/orders")
public class OrderResource {

    @Inject
    InventoryClient inventoryClient;

    /** Failures are thrown as ProblemException and rendered by ExceptionMappers. */
    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    @ResponseStatus(201)
    @Blocking
    public OrderResult placeOrder(OrderRequest body) {
        if (body == null || body.sku() == null || body.sku().isBlank()) {
            throw ProblemException.validation("sku must not be empty");
        }
        if (body.quantity() <= 0) {
            throw ProblemException.validation("quantity must be greater than 0");
        }

        ReserveReply reply = inventoryClient.reserveStock(body.sku(), body.quantity());
        if (!reply.getReserved()) {
            String message = "insufficient stock for " + body.sku();
            throw new ProblemException(409, "STOCK_UNAVAILABLE", message, message, false, null);
        }

        return new OrderResult(UUID.randomUUID().toString(), body.sku(), body.quantity(), "confirmed",
                reply.getRemaining());
    }
}
