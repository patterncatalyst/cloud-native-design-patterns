package com.cndp.order.adapter;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import com.cndp.order.domain.Order;
import com.cndp.order.domain.OrderRepository;
import com.cndp.order.domain.PlaceOrderCmd;
import com.cndp.order.domain.PlaceOrderUseCase;

/**
 * Driving adapter — REST controller that delegates to the domain use case.
 */
@RestController
public class RestAdapter {

    private final PlaceOrderUseCase placeOrder;
    private final OrderRepository repo;

    public RestAdapter(PlaceOrderUseCase placeOrder, OrderRepository repo) {
        this.placeOrder = placeOrder;
        this.repo = repo;
    }

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @PostMapping("/orders")
    public ResponseEntity<?> createOrder(@RequestBody Map<String, Object> body) {
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
            return ResponseEntity.status(HttpStatus.CREATED).body(toMap(order));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
                    .body(Map.of("detail", e.getMessage()));
        }
    }

    @GetMapping("/orders/{id}")
    public ResponseEntity<?> getOrder(@PathVariable String id) {
        return repo.findById(id)
                .map(order -> ResponseEntity.ok(toMap(order)))
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/orders")
    public List<Map<String, Object>> listOrders() {
        return repo.listAll().stream().map(this::toMap).collect(Collectors.toList());
    }

    private Map<String, Object> toMap(Order o) {
        return Map.of(
                "id", o.id(),
                "sku", o.sku(),
                "quantity", o.quantity(),
                "status", o.status()
        );
    }
}
