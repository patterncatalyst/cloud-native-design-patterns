package com.example.orderservice;

import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);
    private static final String TOPIC = "order.placed";

    private final OrderRepository orders;
    private final KafkaTemplate<String, OrderEvent> kafka;

    public OrderController(OrderRepository orders, KafkaTemplate<String, OrderEvent> kafka) {
        this.orders = orders;
        this.kafka = kafka;
    }

    @PostMapping("/orders")
    public ResponseEntity<OrderEvent> createOrder(@RequestBody Map<String, Object> body) {
        String sku = (String) body.get("sku");
        int quantity = ((Number) body.get("quantity")).intValue();

        var order = orders.save(new Order(sku, quantity, "pending"));
        log.info("Order created: id={}, sku={}, quantity={}", order.getId(), sku, quantity);

        OrderEvent event = order.toEvent();
        kafka.send(TOPIC, event.id(), event);
        log.info("Event published to {}: orderId={}", TOPIC, event.id());

        return ResponseEntity.status(HttpStatus.CREATED).body(event);
    }

    @GetMapping("/orders")
    public List<OrderView> listOrders() {
        return orders.findAllByOrderByCreatedAtDesc().stream().map(Order::toView).toList();
    }
}
