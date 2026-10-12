package com.example.shippingconsumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class ShippingListener {

    private static final Logger log = LoggerFactory.getLogger(ShippingListener.class);

    private final ShipmentRepository shipments;

    public ShippingListener(ShipmentRepository shipments) {
        this.shipments = shipments;
    }

    /**
     * Idempotent: a redelivered event is skipped by the existence check, and the unique constraint on
     * {@code order_id} catches the race between two deliveries. Neither case throws, so the listener
     * container never redelivers.
     */
    @KafkaListener(topics = "order.placed", groupId = "shipping-group")
    public void onOrderPlaced(OrderEvent event) {
        log.info("Received order.placed: orderId={}", event.id());
        if (shipments.existsByOrderId(event.id())) {
            log.info("Duplicate shipment for orderId={}, skipping (idempotent)", event.id());
            return;
        }
        try {
            shipments.save(new Shipment(event.id(), "scheduled"));
            log.info("Shipment scheduled for orderId={}", event.id());
        } catch (DataIntegrityViolationException e) {
            log.info("Duplicate shipment for orderId={}, skipping (idempotent)", event.id());
        }
    }
}
