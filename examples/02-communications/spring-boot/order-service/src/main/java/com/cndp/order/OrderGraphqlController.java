package com.cndp.order;

import java.util.List;

import org.springframework.data.domain.PageRequest;
import org.springframework.graphql.data.method.annotation.Argument;
import org.springframework.graphql.data.method.annotation.QueryMapping;
import org.springframework.stereotype.Controller;

@Controller
public class OrderGraphqlController {

    private final OrderRepository orders;

    public OrderGraphqlController(OrderRepository orders) {
        this.orders = orders;
    }

    @QueryMapping
    public List<OrderView> orders(@Argument int limit) {
        return orders.findAllByOrderByIdAsc(PageRequest.ofSize(limit)).stream().map(Order::toView).toList();
    }

    @QueryMapping
    public OrderView order(@Argument String id) {
        return orders.findById(id).map(Order::toView).orElse(null);
    }
}
