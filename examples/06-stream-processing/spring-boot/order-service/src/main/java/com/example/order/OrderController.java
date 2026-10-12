package com.example.order;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.*;

import java.math.RoundingMode;
import java.util.List;

@RestController
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);

    private final OrderRepository orders;
    private final KafkaTemplate<String, OrderEvent> kafka;

    public OrderController(OrderRepository orders, KafkaTemplate<String, OrderEvent> kafka) {
        this.orders = orders;
        this.kafka = kafka;
    }

    @PostMapping("/orders")
    @ResponseStatus(HttpStatus.CREATED)
    public OrderEvent placeOrder(@RequestBody OrderRequest request) {
        var saved = orders.save(new OrderEntity(request.merchantId(), request.sku(), request.quantity(),
                request.total().setScale(2, RoundingMode.HALF_UP), "confirmed"));
        OrderEvent event = saved.toEvent();
        kafka.send("order.placed", event.id(), event);
        log.info("published order.placed id={} merchant={} total={}",
                event.id(), event.merchantId(), event.total());
        return event;
    }

    @GetMapping("/orders")
    public List<OrderEvent> listOrders() {
        return orders.findTop50ByOrderByCreatedAtDesc().stream().map(OrderEntity::toEvent).toList();
    }
}
