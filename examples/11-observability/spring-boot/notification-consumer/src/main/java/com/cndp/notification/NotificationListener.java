package com.cndp.notification;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class NotificationListener {

    private static final Logger log = LoggerFactory.getLogger(NotificationListener.class);

    private final JdbcTemplate jdbc;

    public NotificationListener(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @KafkaListener(topics = "order.placed", groupId = "notification-group")
    public void onOrderPlaced(OrderEvent event) {
        log.info("Received order.placed: orderId={}", event.getId());
        try {
            jdbc.update(
                "INSERT INTO notifications (order_id, channel) VALUES (?, 'email')",
                event.getId()
            );
            log.info("Notification recorded for orderId={}", event.getId());
        } catch (DataIntegrityViolationException e) {
            log.info("Duplicate notification for orderId={}, skipping (idempotent)", event.getId());
        }
    }
}
