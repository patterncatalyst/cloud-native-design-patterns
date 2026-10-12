package com.example.orderservice;

import java.util.List;
import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {

    private final OrderRepository orders;
    private final ShutdownState shutdownState;

    public OrderController(OrderRepository orders, ShutdownState shutdownState) {
        this.orders = orders;
        this.shutdownState = shutdownState;
    }

    @PostMapping("/orders")
    public ResponseEntity<Object> placeOrder(@RequestBody OrderRequest request) {
        shutdownState.incrementInFlight();
        try {
            if (shutdownState.isShuttingDown()) {
                return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                        .body(Map.of("error", "shutting down"));
            }
            var saved = orders.save(new OrderEntity(request.sku(), request.quantity(), "confirmed"));
            return ResponseEntity.status(HttpStatus.CREATED).body(saved.toOrder());
        } finally {
            shutdownState.decrementInFlight();
        }
    }

    @GetMapping("/orders")
    public List<Order> listOrders() {
        return orders.findTop50ByOrderByCreatedAtDesc().stream().map(OrderEntity::toOrder).toList();
    }

    @GetMapping("/debug/state")
    public Map<String, Object> debugState() {
        return Map.of(
                "shutting_down", shutdownState.isShuttingDown(),
                "in_flight", shutdownState.getInFlight(),
                "pid", ProcessHandle.current().pid());
    }
}
