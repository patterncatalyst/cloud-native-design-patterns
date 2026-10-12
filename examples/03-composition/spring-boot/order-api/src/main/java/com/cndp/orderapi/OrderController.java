package com.cndp.orderapi;

import java.util.List;

import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class OrderController {

    private final OrderRepository orders;

    public OrderController(OrderRepository orders) {
        this.orders = orders;
    }

    @GetMapping("/orders")
    public List<OrderView> listOrders(@RequestParam(defaultValue = "50") int limit) {
        return orders.findAllByOrderByIdAsc(PageRequest.ofSize(Math.min(limit, 100)))
                .stream().map(Order::toView).toList();
    }

    @GetMapping("/orders/{orderId}")
    public OrderView getOrder(@PathVariable String orderId) {
        return orders.findById(orderId).map(Order::toView)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "order not found"));
    }
}
