package com.cndp.order;

import java.util.Map;
import java.util.UUID;

import com.cndp.proto.InventoryServiceGrpc;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.opentelemetry.api.common.AttributeKey;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.metrics.LongCounter;
import io.opentelemetry.api.trace.Span;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
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
    private final InventoryServiceGrpc.InventoryServiceBlockingStub inventoryStub;
    private final KafkaTemplate<String, Object> kafka;
    private final LongCounter ordersPlacedCounter;

    public OrderController(JdbcClient jdbc,
                           InventoryServiceGrpc.InventoryServiceBlockingStub inventoryStub,
                           KafkaTemplate<String, Object> kafka,
                           LongCounter ordersPlacedCounter) {
        this.jdbc = jdbc;
        this.inventoryStub = inventoryStub;
        this.kafka = kafka;
        this.ordersPlacedCounter = ordersPlacedCounter;
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

        String status = reply.getConfirmed() ? "confirmed" : "rejected";
        String orderId = UUID.randomUUID().toString();

        jdbc.sql("INSERT INTO orders (id, sku, quantity, status) VALUES (?, ?, ?, ?)")
                .param(orderId).param(sku).param(quantity).param(status)
                .update();

        // Record custom metric
        ordersPlacedCounter.add(1, Attributes.of(
                AttributeKey.stringKey("sku"), sku,
                AttributeKey.stringKey("status"), status));

        Map<String, Object> order = Map.of("id", orderId, "sku", sku, "quantity", quantity, "status", status);
        kafka.send("order.placed", order);

        // Correlated log line with trace_id from MDC (set by OTel logback integration)
        String traceId = Span.current().getSpanContext().getTraceId();
        MDC.put("trace_id", traceId);
        log.info("order placed id={} sku={} status={} trace_id={}", orderId, sku, status, traceId);
        MDC.remove("trace_id");

        return ResponseEntity.status(HttpStatus.CREATED).body(order);
    }
}
