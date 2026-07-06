package com.cndp.order.domain;

/**
 * Port — the event-publishing contract the domain depends on.
 * Driven adapters (log-based, Kafka, etc.) implement this interface.
 */
public interface EventPublisher {

    void publish(OrderPlaced event);
}
