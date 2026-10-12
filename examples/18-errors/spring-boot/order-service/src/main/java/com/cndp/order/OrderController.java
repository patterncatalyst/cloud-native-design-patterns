package com.cndp.order;

import java.util.UUID;

import com.cndp.proto.ReserveReply;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {

    private final InventoryClient inventoryClient;

    public OrderController(InventoryClient inventoryClient) {
        this.inventoryClient = inventoryClient;
    }

    @PostMapping("/orders")
    @ResponseStatus(HttpStatus.CREATED)
    public OrderResponse placeOrder(@Valid @RequestBody OrderRequest body) {
        ReserveReply reply = inventoryClient.reserveStock(body.sku(), body.quantity());

        if (!reply.getReserved()) {
            String message = "insufficient stock for " + body.sku();
            throw new ApiException(HttpStatus.CONFLICT, "STOCK_UNAVAILABLE", message, message, false, null);
        }

        return new OrderResponse(UUID.randomUUID().toString(), body.sku(), body.quantity(),
                "confirmed", reply.getRemaining());
    }
}
