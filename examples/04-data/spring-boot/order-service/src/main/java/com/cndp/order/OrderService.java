package com.cndp.order;

import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    private final OrderRepository orders;
    private final OutboxRepository outbox;

    public OrderService(OrderRepository orders, OutboxRepository outbox) {
        this.orders = orders;
        this.outbox = outbox;
    }

    /** The order row and its outbox row commit or roll back together; Debezium publishes the outbox row. */
    @Transactional
    public OrderView placeOrder(String sku, int quantity) {
        var order = orders.save(new Order(sku, quantity, "confirmed"));
        var view = order.toView();
        outbox.save(new OutboxEvent(order.getId(), "order.placed", Map.of(
                "id", view.id(),
                "sku", view.sku(),
                "quantity", view.quantity(),
                "status", view.status())));
        log.info("order + outbox written in one transaction id={}", view.id());
        return view;
    }
}
