package com.cndp.order;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Sort;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);

    private final OrderRepository orders;
    private final String serviceVersion;

    public OrderController(OrderRepository orders, @Value("${service.version}") String serviceVersion) {
        this.orders = orders;
        this.serviceVersion = serviceVersion;
    }

    @GetMapping("/")
    public Map<String, String> root() {
        return Map.of(
                "service", "order-service",
                "version", serviceVersion,
                "config_source", "environment");
    }

    @GetMapping("/orders")
    public List<OrderResponse> listOrders() {
        return orders.findAll(Sort.by("id")).stream().map(OrderResponse::of).toList();
    }

    @PostMapping("/orders")
    public OrderResponse createOrder(@RequestParam String customer, @RequestParam BigDecimal total) {
        var saved = orders.save(new Order(customer, total.setScale(2, RoundingMode.HALF_UP)));
        log.info("order_created id={} customer={} total={}", saved.getId(), customer, saved.getTotal());
        return OrderResponse.of(saved);
    }
}
