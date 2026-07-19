package com.cndp.order.domain;

public interface EventPublisher {

    void publish(OrderPlaced event);
}
