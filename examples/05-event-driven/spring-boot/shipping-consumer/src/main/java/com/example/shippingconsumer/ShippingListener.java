package com.example.shippingconsumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class ShippingListener {

    private static final Logger log = LoggerFactory.getLogger(ShippingListener.class);

    private final JdbcTemplate jdbc;

    public ShippingListener(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @KafkaListener(topics = "order.placed", groupId = "shipping-group")
    public void onOrderPlaced(OrderEvent event) {
        log.info("Received order.placed: orderId={}", event.getId());
        try {
            jdbc.update(
                "INSERT INTO shipments (order_id, status) VALUES (?, 'scheduled')",
                event.getId()
            );
            log.info("Shipment scheduled for orderId={}", event.getId());
        } catch (DataIntegrityViolationException e) {
            log.info("Duplicate shipment for orderId={}, skipping (idempotent)", event.getId());
        }
    }
}
