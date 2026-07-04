package com.cndp.order;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);
    private final JdbcClient jdbc;

    public OrderController(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/orders")
    public List<Map<String, Object>> listOrders() {
        return jdbc.sql("SELECT id, customer, total FROM orders ORDER BY id")
                .query().listOfRows();
    }

    @PostMapping("/orders")
    public Map<String, Object> createOrder(@RequestParam String customer,
                                           @RequestParam BigDecimal total) {
        var row = jdbc.sql("INSERT INTO orders (customer, total) VALUES (?, ?) RETURNING id, customer, total")
                .param(customer)
                .param(total)
                .query().singleRow();
        log.info("order_created id={} customer={} total={}", row.get("id"), customer, total);
        return row;
    }
}
