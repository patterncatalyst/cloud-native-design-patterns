package com.cndp.notification;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class NotificationListener {

    private static final Logger log = LoggerFactory.getLogger(NotificationListener.class);

    private final NotificationRepository notifications;

    public NotificationListener(NotificationRepository notifications) {
        this.notifications = notifications;
    }

    /**
     * Idempotent: a redelivered event is skipped by the existence check, and the unique constraint on
     * {@code order_id} catches the race between two deliveries. Neither case throws, so the listener
     * container never redelivers.
     */
    @KafkaListener(topics = "order.placed", groupId = "notification-group")
    public void onOrderPlaced(OrderEvent event) {
        log.info("Received order.placed: orderId={}", event.id());
        if (notifications.existsByOrderId(event.id())) {
            log.info("Duplicate notification for orderId={}, skipping (idempotent)", event.id());
            return;
        }
        try {
            notifications.save(new Notification(event.id(), "email"));
            log.info("Notification recorded for orderId={}", event.id());
        } catch (DataIntegrityViolationException e) {
            log.info("Duplicate notification for orderId={}, skipping (idempotent)", event.id());
        }
    }
}
