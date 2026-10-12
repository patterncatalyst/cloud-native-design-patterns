package com.cndp.order;

import java.util.Map;

import com.cndp.proto.InventoryServiceGrpc;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.opentelemetry.api.common.AttributeKey;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.metrics.LongCounter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);

    private final OrderRepository orders;
    private final InventoryServiceGrpc.InventoryServiceBlockingStub inventoryStub;
    private final KafkaTemplate<String, OrderView> kafka;
    private final LongCounter ordersPlacedCounter;

    public OrderController(OrderRepository orders,
                           InventoryServiceGrpc.InventoryServiceBlockingStub inventoryStub,
                           KafkaTemplate<String, OrderView> kafka,
                           LongCounter ordersPlacedCounter) {
        this.orders = orders;
        this.inventoryStub = inventoryStub;
        this.kafka = kafka;
        this.ordersPlacedCounter = ordersPlacedCounter;
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

        String status = reply.getConfirmed() ? "confirmed" : "rejected";

        OrderView order = orders.save(new Order(sku, quantity, status)).toView();

        // Record custom metric
        ordersPlacedCounter.add(1, Attributes.of(
                AttributeKey.stringKey("sku"), sku,
                AttributeKey.stringKey("status"), status));

        kafka.send("order.placed", order);

        // The OpenTelemetry Java agent puts trace_id and span_id in the logback MDC; the log
        // pattern in application.yaml (%X{trace_id:-}) prints it, so the message carries no id.
        log.info("order placed id={} sku={} status={}", order.id(), sku, status);

        return ResponseEntity.status(HttpStatus.CREATED).body(order);
    }
}
