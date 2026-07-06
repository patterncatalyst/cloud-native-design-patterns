package com.cndp.order;

import com.cndp.proto.ReserveReply;
import io.grpc.StatusRuntimeException;
import io.opentelemetry.api.trace.Span;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

@RestController
public class OrderController {

    private static final Logger log = LoggerFactory.getLogger(OrderController.class);
    private static final MediaType PROBLEM_JSON = MediaType.parseMediaType("application/problem+json");

    private final InventoryClient inventoryClient;

    public OrderController(InventoryClient inventoryClient) {
        this.inventoryClient = inventoryClient;
    }

    @GetMapping("/healthz")
    public Map<String, String> healthz() {
        return Map.of("status", "ok");
    }

    @PostMapping("/orders")
    public ResponseEntity<?> placeOrder(@RequestBody OrderRequest body) {
        // Validation
        if (body.getSku() == null || body.getSku().isBlank()) {
            return problemResponse(HttpStatus.UNPROCESSABLE_ENTITY,
                    "VALIDATION_ERROR", "request validation failed",
                    "sku must not be empty", false, null);
        }
        if (body.getQuantity() <= 0) {
            return problemResponse(HttpStatus.UNPROCESSABLE_ENTITY,
                    "VALIDATION_ERROR", "request validation failed",
                    "quantity must be greater than 0", false, null);
        }

        try {
            ReserveReply reply = inventoryClient.reserveStock(body.getSku(), body.getQuantity());

            if (!reply.getReserved()) {
                return problemResponse(HttpStatus.CONFLICT,
                        "STOCK_UNAVAILABLE",
                        "insufficient stock for " + body.getSku(),
                        "insufficient stock for " + body.getSku(),
                        false, null);
            }

            Map<String, Object> result = new LinkedHashMap<>();
            result.put("id", UUID.randomUUID().toString());
            result.put("sku", body.getSku());
            result.put("quantity", body.getQuantity());
            result.put("status", "confirmed");
            result.put("remaining_stock", reply.getRemaining());

            return ResponseEntity.status(HttpStatus.CREATED).body(result);

        } catch (StatusRuntimeException e) {
            return handleGrpcError(e, body.getSku());
        }
    }

    private ResponseEntity<?> handleGrpcError(StatusRuntimeException e, String sku) {
        switch (e.getStatus().getCode()) {
            case RESOURCE_EXHAUSTED:
                String detail = e.getStatus().getDescription();
                if (detail == null) {
                    detail = "insufficient stock for " + sku;
                }
                return problemResponse(HttpStatus.CONFLICT,
                        "STOCK_UNAVAILABLE",
                        "insufficient stock for " + sku,
                        detail, false, null);

            case DEADLINE_EXCEEDED:
            case UNAVAILABLE:
                return problemResponse(HttpStatus.SERVICE_UNAVAILABLE,
                        "INVENTORY_UNAVAILABLE",
                        "inventory service is temporarily unavailable",
                        "gRPC " + e.getStatus().getCode().name().toLowerCase(), true, 2);

            default:
                log.error("unexpected gRPC error from inventory: status={} desc={}",
                        e.getStatus().getCode(), e.getStatus().getDescription(), e);
                return problemResponse(HttpStatus.INTERNAL_SERVER_ERROR,
                        "INTERNAL_ERROR",
                        "unexpected error from inventory service",
                        e.getStatus().getDescription(), false, null);
        }
    }

    private ResponseEntity<?> problemResponse(HttpStatus status, String code, String message,
                                               String detail, boolean retryable, Integer retryAfter) {
        String traceId = getTraceId();

        ErrorResponse body = new ErrorResponse(code, message, traceId);
        body.setDetail(detail);
        body.setRetryable(retryable);
        if (retryAfter != null) {
            body.setRetryAfter(retryAfter);
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(PROBLEM_JSON);
        if (retryAfter != null) {
            headers.set("Retry-After", retryAfter.toString());
        }

        return new ResponseEntity<>(body, headers, status);
    }

    private String getTraceId() {
        Span span = Span.current();
        if (span != null && span.getSpanContext().isValid()) {
            return span.getSpanContext().getTraceId();
        }
        return UUID.randomUUID().toString().replace("-", "");
    }
}
