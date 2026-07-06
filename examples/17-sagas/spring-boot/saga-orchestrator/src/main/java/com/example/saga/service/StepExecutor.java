package com.example.saga.service;

import java.util.Map;
import java.util.UUID;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/**
 * Simulates saga step execution. Each step returns a result map;
 * book_shipping throws if fail_shipping is set in the context.
 */
@Component
public class StepExecutor {

    private static final Logger log = LoggerFactory.getLogger(StepExecutor.class);

    @SuppressWarnings("unchecked")
    public Map<String, Object> execute(String stepName, Map<String, Object> context) {
        return switch (stepName) {
            case "charge_payment" -> {
                String paymentId = "pay-" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);
                Object total = context.getOrDefault("total", 0);
                log.info("Charged payment {} for order {}", paymentId, context.get("order_id"));
                yield Map.of("payment_id", paymentId, "amount", total);
            }
            case "reserve_stock" -> {
                String reservationId = "rsv-" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);
                Object sku = context.getOrDefault("sku", "");
                log.info("Reserved stock {} for sku {}", reservationId, sku);
                yield Map.of("reservation_id", reservationId, "sku", sku);
            }
            case "book_shipping" -> {
                Object failFlag = context.get("fail_shipping");
                boolean shouldFail = Boolean.TRUE.equals(failFlag);
                if (failFlag instanceof String s) {
                    shouldFail = "true".equalsIgnoreCase(s);
                }
                if (shouldFail) {
                    throw new RuntimeException("shipping service unavailable");
                }
                String shipmentId = "shp-" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);
                log.info("Booked shipping {}", shipmentId);
                yield Map.of("shipment_id", shipmentId);
            }
            case "refund_payment" -> {
                Map<String, Object> chargeResult = (Map<String, Object>) context.getOrDefault("charge_payment", Map.of());
                log.info("Refunded payment {}", chargeResult.get("payment_id"));
                yield Map.of("refunded", true);
            }
            case "release_stock" -> {
                Map<String, Object> stockResult = (Map<String, Object>) context.getOrDefault("reserve_stock", Map.of());
                log.info("Released stock {}", stockResult.get("reservation_id"));
                yield Map.of("released", true);
            }
            case "cancel_shipping" -> {
                Map<String, Object> shipResult = (Map<String, Object>) context.getOrDefault("book_shipping", Map.of());
                log.info("Cancelled shipping {}", shipResult.get("shipment_id"));
                yield Map.of("cancelled", true);
            }
            default -> Map.of();
        };
    }
}
