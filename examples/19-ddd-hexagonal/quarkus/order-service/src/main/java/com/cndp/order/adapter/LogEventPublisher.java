package com.cndp.order.adapter;

import org.jboss.logging.Logger;

import jakarta.enterprise.context.ApplicationScoped;

import com.cndp.order.domain.EventPublisher;
import com.cndp.order.domain.OrderPlaced;

@ApplicationScoped
public class LogEventPublisher implements EventPublisher {

    private static final Logger log = Logger.getLogger("events");

    @Override
    public void publish(OrderPlaced event) {
        log.infof("EVENT OrderPlaced order_id=%s sku=%s", event.orderId(), event.sku());
    }
}
