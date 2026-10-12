package com.cndp.order;

import java.util.List;
import java.util.Map;

import com.cndp.proto.InventoryGrpc;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.data.domain.PageRequest;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);

    private final OrderRepository orders;
    private final InventoryGrpc.InventoryBlockingStub inventoryStub;
    private final KafkaTemplate<String, OrderView> kafka;

    public OrderController(OrderRepository orders,
                           InventoryGrpc.InventoryBlockingStub inventoryStub,
                           KafkaTemplate<String, OrderView> kafka) {
        this.orders = orders;
        this.inventoryStub = inventoryStub;
        this.kafka = kafka;
    }

    @PostMapping("/orders")
    public ResponseEntity<OrderView> placeOrder(@RequestBody Map<String, Object> body) {
        String sku = body.get("sku") != null ? body.get("sku").toString() : "";
        int quantity = body.get("quantity") != null ? ((Number) body.get("quantity")).intValue() : 0;

        if (sku.isEmpty() || sku.length() > 64) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "invalid sku");
        }
        if (quantity <= 0 || quantity > 1000) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "invalid quantity");
        }

        ReserveReply reply = inventoryStub.reserveStock(
                ReserveRequest.newBuilder().setSku(sku).setQuantity(quantity).build());

        String status = reply.getReserved() ? "confirmed" : "rejected";
        OrderView order = orders.save(new Order(sku, quantity, status)).toView();
        kafka.send("order.placed", order);
        log.info("order created id={} status={}", order.id(), status);

        return ResponseEntity.status(HttpStatus.CREATED).body(order);
    }

    @GetMapping("/orders")
    public OrderPage listOrders(
            @RequestParam(required = false) String after,
            @RequestParam(defaultValue = "50") int limit) {
        limit = Math.min(limit, 100);

        var page = PageRequest.ofSize(limit);
        List<OrderView> items = (after != null
                ? orders.findByIdGreaterThanOrderByIdAsc(after, page)
                : orders.findAllByOrderByIdAsc(page)).stream().map(Order::toView).toList();

        String nextCursor = items.size() == limit ? items.getLast().id() : null;
        return new OrderPage(items, nextCursor);
    }
}
