package com.cndp.order.domain;

public class PlaceOrderUseCase {

    private final OrderRepository repo;
    private final EventPublisher events;

    public PlaceOrderUseCase(OrderRepository repo, EventPublisher events) {
        this.repo = repo;
        this.events = events;
    }

    public Order execute(PlaceOrderCmd cmd) {
        Order order = Order.create(cmd);
        repo.save(order);
        events.publish(new OrderPlaced(order.id(), order.sku(), order.quantity()));
        return order;
    }
}
