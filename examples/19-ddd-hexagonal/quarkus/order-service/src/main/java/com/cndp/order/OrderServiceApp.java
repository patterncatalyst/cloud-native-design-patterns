package com.cndp.order;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;

import com.cndp.order.domain.EventPublisher;
import com.cndp.order.domain.OrderRepository;
import com.cndp.order.domain.PlaceOrderUseCase;

@ApplicationScoped
public class OrderServiceApp {

    @Produces
    @ApplicationScoped
    public PlaceOrderUseCase placeOrderUseCase(OrderRepository repo, EventPublisher events) {
        return new PlaceOrderUseCase(repo, events);
    }
}
