package com.cndp.order;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;

import com.cndp.order.domain.EventPublisher;
import com.cndp.order.domain.OrderRepository;
import com.cndp.order.domain.PlaceOrderUseCase;

/** Wires the framework-free use case to the adapters CDI finds. */
@ApplicationScoped
public class UseCaseConfig {

    @Produces
    @ApplicationScoped
    public PlaceOrderUseCase placeOrderUseCase(OrderRepository repo, EventPublisher events) {
        return new PlaceOrderUseCase(repo, events);
    }
}
