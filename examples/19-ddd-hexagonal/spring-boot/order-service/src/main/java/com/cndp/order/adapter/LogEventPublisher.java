package com.cndp.order.adapter;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import com.cndp.order.domain.EventPublisher;
import com.cndp.order.domain.OrderPlaced;

/**
 * Driven adapter — publishes domain events to the application log.
 * In production this would be Kafka, AMQP, etc.
 */
@Component
public class LogEventPublisher implements EventPublisher {

    private static final Logger log = LoggerFactory.getLogger("events");

    @Override
    public void publish(OrderPlaced event) {
        log.info("EVENT OrderPlaced order_id={} sku={}", event.orderId(), event.sku());
    }
}
