package com.cndp.order;

import java.util.List;
import java.util.Map;

import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {

    private final OrderService service;
    private final OrderRepository orders;
    private final OutboxRepository outbox;

    public OrderController(OrderService service, OrderRepository orders, OutboxRepository outbox) {
        this.service = service;
        this.orders = orders;
        this.outbox = outbox;
    }

    @PostMapping("/orders")
    @ResponseStatus(HttpStatus.CREATED)
    public OrderView createOrder(@RequestBody Map<String, Object> body) {
        return service.placeOrder((String) body.get("sku"), ((Number) body.get("quantity")).intValue());
    }

    @GetMapping("/orders")
    public List<OrderView> listOrders(@RequestParam(defaultValue = "50") int limit) {
        return orders.findAllByOrderByCreatedAtDesc(PageRequest.ofSize(limit)).stream().map(Order::toView).toList();
    }

    @GetMapping("/outbox")
    public List<OutboxView> listOutbox(@RequestParam(defaultValue = "50") int limit) {
        return outbox.findAllByOrderByIdDesc(PageRequest.ofSize(limit)).stream().map(OutboxEvent::toView).toList();
    }
}
