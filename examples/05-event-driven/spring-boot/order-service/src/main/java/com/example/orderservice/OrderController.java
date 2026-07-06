package com.example.orderservice;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);
    private static final String TOPIC = "order.placed";

    private final JdbcTemplate jdbc;
    private final KafkaTemplate<String, OrderEvent> kafka;

    public OrderController(JdbcTemplate jdbc, KafkaTemplate<String, OrderEvent> kafka) {
        this.jdbc = jdbc;
        this.kafka = kafka;
    }

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @PostMapping("/orders")
    public ResponseEntity<Map<String, Object>> createOrder(@RequestBody Map<String, Object> body) {
        String id = UUID.randomUUID().toString();
        String sku = (String) body.get("sku");
        int quantity = ((Number) body.get("quantity")).intValue();

        jdbc.update(
            "INSERT INTO orders (id, sku, quantity, status) VALUES (?, ?, ?, 'pending')",
            id, sku, quantity
        );
        log.info("Order created: id={}, sku={}, quantity={}", id, sku, quantity);

        OrderEvent event = new OrderEvent(id, sku, quantity, "pending");
        kafka.send(TOPIC, id, event);
        log.info("Event published to {}: orderId={}", TOPIC, id);

        Map<String, Object> response = Map.of(
            "id", id,
            "sku", sku,
            "quantity", quantity,
            "status", "pending"
        );
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping("/orders")
    public List<Map<String, Object>> listOrders() {
        return jdbc.queryForList("SELECT id, sku, quantity, status, created_at FROM orders ORDER BY created_at DESC");
    }
}
