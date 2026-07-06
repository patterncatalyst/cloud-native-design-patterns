package com.cndp.order;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.fasterxml.jackson.databind.ObjectMapper;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);
    private final JdbcClient jdbc;
    private final ObjectMapper objectMapper;

    public OrderController(JdbcClient jdbc, ObjectMapper objectMapper) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
    }

    @PostMapping("/orders")
    @ResponseStatus(HttpStatus.CREATED)
    @Transactional
    public Map<String, Object> createOrder(@RequestBody Map<String, Object> body) {
        String orderId = UUID.randomUUID().toString();
        String sku = (String) body.get("sku");
        int quantity = ((Number) body.get("quantity")).intValue();
        String status = "confirmed";

        jdbc.sql("INSERT INTO orders (id, sku, quantity, status) VALUES (?, ?, ?, ?)")
                .param(orderId)
                .param(sku)
                .param(quantity)
                .param(status)
                .update();

        Map<String, Object> payload = Map.of(
                "id", orderId,
                "sku", sku,
                "quantity", quantity,
                "status", status
        );

        String payloadJson;
        try {
            payloadJson = objectMapper.writeValueAsString(payload);
        } catch (Exception e) {
            throw new RuntimeException("Failed to serialize outbox payload", e);
        }

        jdbc.sql("INSERT INTO outbox (aggregate_id, event_type, payload) VALUES (?, ?, ?::jsonb)")
                .param(orderId)
                .param("order.placed")
                .param(payloadJson)
                .update();

        log.info("order + outbox written in one transaction id={}", orderId);
        return Map.of("id", orderId, "sku", sku, "quantity", quantity, "status", status);
    }

    @GetMapping("/orders")
    public List<Map<String, Object>> listOrders(@RequestParam(defaultValue = "50") int limit) {
        return jdbc.sql("SELECT id, sku, quantity, status FROM orders ORDER BY created_at DESC LIMIT ?")
                .param(limit)
                .query().listOfRows();
    }

    @GetMapping("/outbox")
    public List<Map<String, Object>> listOutbox(@RequestParam(defaultValue = "50") int limit) {
        return jdbc.sql("SELECT id, aggregate_id, event_type, payload, created_at FROM outbox ORDER BY id DESC LIMIT ?")
                .param(limit)
                .query().listOfRows();
    }
}
