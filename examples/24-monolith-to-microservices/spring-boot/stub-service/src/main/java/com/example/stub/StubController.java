package com.example.stub;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class StubController {

    @Value("${SERVICE_NAME:unknown}")
    private String serviceName;

    private final AtomicLong counter = new AtomicLong(0);
    private final Map<String, Map<String, Object>> orders = new ConcurrentHashMap<>();
    private final Map<String, AtomicLong> accessCounts = new ConcurrentHashMap<>();

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok", "source", serviceName);
    }

    @PostMapping("/orders")
    public ResponseEntity<Map<String, Object>> createOrder(@RequestBody Map<String, Object> body) {
        String id = String.valueOf(counter.incrementAndGet());
        Map<String, Object> order = new LinkedHashMap<>();
        order.put("id", id);
        order.put("sku", body.getOrDefault("sku", ""));
        order.put("quantity", body.getOrDefault("quantity", 0));
        order.put("tenant", body.getOrDefault("tenant", ""));
        order.put("source", serviceName);
        orders.put(id, order);
        return ResponseEntity.status(HttpStatus.CREATED).body(order);
    }

    @GetMapping("/orders/{orderId}")
    public Map<String, Object> getOrder(@PathVariable String orderId) {
        accessCounts.computeIfAbsent(orderId, k -> new AtomicLong(0)).incrementAndGet();
        Map<String, Object> order = orders.get(orderId);
        if (order != null) {
            return order;
        }
        Map<String, Object> stub = new LinkedHashMap<>();
        stub.put("id", orderId);
        stub.put("source", serviceName);
        stub.put("status", "stub");
        return stub;
    }

    @GetMapping("/access-count/{orderId}")
    public Map<String, Object> accessCount(@PathVariable String orderId) {
        long count = accessCounts.containsKey(orderId)
                ? accessCounts.get(orderId).get()
                : 0;
        return Map.of("order_id", orderId, "count", count);
    }
}
