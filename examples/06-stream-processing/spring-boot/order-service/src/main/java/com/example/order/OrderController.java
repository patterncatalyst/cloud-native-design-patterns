package com.example.order;

import com.fasterxml.jackson.annotation.JsonProperty;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);

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
    @ResponseStatus(HttpStatus.CREATED)
    public OrderResponse placeOrder(@RequestBody OrderRequest request) {
        String orderId = UUID.randomUUID().toString();

        jdbc.update(
            "INSERT INTO orders (id, merchant_id, sku, quantity, total, status) VALUES (?, ?, ?, ?, ?, 'confirmed')",
            orderId, request.merchantId(), request.sku(), request.quantity(), request.total()
        );

        OrderEvent event = new OrderEvent(
            orderId, request.merchantId(), request.sku(),
            request.quantity(), request.total(), "confirmed"
        );
        kafka.send("order.placed", orderId, event);
        log.info("published order.placed id={} merchant={} total={}",
                orderId, request.merchantId(), request.total());

        return new OrderResponse(
            orderId, request.merchantId(), request.sku(),
            request.quantity(), request.total(), "confirmed"
        );
    }

    @GetMapping("/orders")
    public List<OrderResponse> listOrders() {
        return jdbc.query(
            "SELECT id, merchant_id, sku, quantity, total, status FROM orders ORDER BY created_at DESC LIMIT 50",
            (rs, rowNum) -> new OrderResponse(
                rs.getString("id"),
                rs.getString("merchant_id"),
                rs.getString("sku"),
                rs.getInt("quantity"),
                rs.getBigDecimal("total"),
                rs.getString("status")
            )
        );
    }

    public record OrderResponse(
        String id,
        @JsonProperty("merchant_id") String merchantId,
        String sku,
        int quantity,
        BigDecimal total,
        String status
    ) {}
}
