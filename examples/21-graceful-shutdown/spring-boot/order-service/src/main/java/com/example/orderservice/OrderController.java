package com.example.orderservice;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {

    private final JdbcTemplate jdbc;
    private final ShutdownState shutdownState;

    public OrderController(JdbcTemplate jdbc, ShutdownState shutdownState) {
        this.jdbc = jdbc;
        this.shutdownState = shutdownState;
    }

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @GetMapping("/readyz")
    public ResponseEntity<Map<String, Object>> readyz() {
        if (shutdownState.isShuttingDown()) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                    .body(Map.of("ready", false, "reason", "shutting down"));
        }
        try {
            jdbc.queryForObject("SELECT 1", Integer.class);
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                    .body(Map.of("ready", false, "reason", "db unreachable"));
        }
        return ResponseEntity.ok(Map.of("ready", true));
    }

    @PostMapping("/orders")
    public ResponseEntity<Object> placeOrder(@RequestBody OrderRequest request) {
        shutdownState.incrementInFlight();
        try {
            if (shutdownState.isShuttingDown()) {
                return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                        .body(Map.of("error", "shutting down"));
            }

            String id = UUID.randomUUID().toString();
            jdbc.update(
                    "INSERT INTO orders (id, sku, quantity, status) VALUES (?, ?, ?, 'confirmed')",
                    id, request.sku(), request.quantity());

            return ResponseEntity.status(HttpStatus.CREATED)
                    .body(new Order(id, request.sku(), request.quantity(), "confirmed"));
        } finally {
            shutdownState.decrementInFlight();
        }
    }

    @GetMapping("/orders")
    public List<Order> listOrders() {
        return jdbc.query(
                "SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT 50",
                (rs, rowNum) -> new Order(
                        rs.getString("id"),
                        rs.getString("sku"),
                        rs.getInt("quantity"),
                        rs.getString("status")));
    }

    @GetMapping("/debug/state")
    public Map<String, Object> debugState() {
        return Map.of(
                "shutting_down", shutdownState.isShuttingDown(),
                "in_flight", shutdownState.getInFlight(),
                "pid", ProcessHandle.current().pid());
    }
}
