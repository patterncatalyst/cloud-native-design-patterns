package com.cndp.order;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.cndp.proto.InventoryGrpc;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);

    private final JdbcClient jdbc;
    private final InventoryGrpc.InventoryBlockingStub inventoryStub;
    private final KafkaTemplate<String, Object> kafka;

    public OrderController(JdbcClient jdbc,
                           InventoryGrpc.InventoryBlockingStub inventoryStub,
                           KafkaTemplate<String, Object> kafka) {
        this.jdbc = jdbc;
        this.inventoryStub = inventoryStub;
        this.kafka = kafka;
    }

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @PostMapping("/orders")
    public ResponseEntity<Map<String, Object>> placeOrder(@RequestBody Map<String, Object> body) {
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
        String orderId = UUID.randomUUID().toString();

        jdbc.sql("INSERT INTO orders (id, sku, quantity, status) VALUES (?, ?, ?, ?)")
                .param(orderId).param(sku).param(quantity).param(status)
                .update();

        Map<String, Object> order = Map.of("id", orderId, "sku", sku, "quantity", quantity, "status", status);
        kafka.send("order.placed", order);
        log.info("order created id={} status={}", orderId, status);

        return ResponseEntity.status(HttpStatus.CREATED).body(order);
    }

    @GetMapping("/orders")
    public Map<String, Object> listOrders(
            @RequestParam(required = false) String after,
            @RequestParam(defaultValue = "50") int limit) {
        limit = Math.min(limit, 100);

        List<Map<String, Object>> items;
        if (after != null) {
            items = jdbc.sql("SELECT id, sku, quantity, status FROM orders WHERE id > ? ORDER BY id LIMIT ?")
                    .param(after).param(limit)
                    .query().listOfRows();
        } else {
            items = jdbc.sql("SELECT id, sku, quantity, status FROM orders ORDER BY id LIMIT ?")
                    .param(limit)
                    .query().listOfRows();
        }

        String nextCursor = items.size() == limit ? items.getLast().get("id").toString() : null;
        var result = new java.util.HashMap<String, Object>();
        result.put("items", items);
        result.put("next_cursor", nextCursor);
        return result;
    }
}
