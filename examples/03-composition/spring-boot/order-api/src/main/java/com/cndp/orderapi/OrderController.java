package com.cndp.orderapi;

import java.util.List;
import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class OrderController {

    private final JdbcClient jdbc;

    public OrderController(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @GetMapping("/orders")
    public List<Map<String, Object>> listOrders(
            @RequestParam(defaultValue = "50") int limit) {
        return jdbc.sql("SELECT id, sku, quantity, status FROM orders ORDER BY id LIMIT ?")
                .param(Math.min(limit, 100))
                .query().listOfRows();
    }

    @GetMapping("/orders/{orderId}")
    public Map<String, Object> getOrder(@PathVariable String orderId) {
        var rows = jdbc.sql("SELECT id, sku, quantity, status FROM orders WHERE id = ?")
                .param(orderId)
                .query().listOfRows();
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "order not found");
        }
        return rows.getFirst();
    }
}
