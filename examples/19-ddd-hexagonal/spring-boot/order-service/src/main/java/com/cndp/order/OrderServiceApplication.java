package com.cndp.order;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import com.cndp.order.domain.EventPublisher;
import com.cndp.order.domain.OrderRepository;
import com.cndp.order.domain.PlaceOrderUseCase;

@SpringBootApplication
public class OrderServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(OrderServiceApplication.class, args);
    }

    /** Wire the domain use case from its ports — no framework leaks into the domain. */
    @Bean
    public PlaceOrderUseCase placeOrderUseCase(OrderRepository repo, EventPublisher events) {
        return new PlaceOrderUseCase(repo, events);
    }
}
