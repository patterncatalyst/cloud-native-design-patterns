package com.cndp.saga.service;

import jakarta.enterprise.context.ApplicationScoped;
import org.jboss.logging.Logger;

import java.util.Map;
import java.util.UUID;

@ApplicationScoped
public class StepExecutor {
    private static final Logger LOG = Logger.getLogger(StepExecutor.class);

    public Map<String, Object> execute(String stepName, Map<String, Object> context) {
        LOG.infof("Executing step: %s", stepName);

        return switch (stepName) {
            case "charge_payment" -> {
                String paymentId = "pmt_" + UUID.randomUUID().toString().substring(0, 8);
                double amount = getDouble(context, "total");
                LOG.infof("Charged payment: %s for amount: %.2f", paymentId, amount);
                yield Map.of("payment_id", paymentId, "amount", amount);
            }
            case "reserve_stock" -> {
                String reservationId = "rsv_" + UUID.randomUUID().toString().substring(0, 8);
                String sku = (String) context.get("sku");
                LOG.infof("Reserved stock: %s for sku: %s", reservationId, sku);
                yield Map.of("reservation_id", reservationId, "sku", sku);
            }
            case "book_shipping" -> {
                // Check if we should fail (handle both Boolean and String "true")
                Object failFlag = context.get("fail_shipping");
                boolean shouldFail = false;
                if (failFlag instanceof Boolean b) {
                    shouldFail = b;
                } else if (failFlag instanceof String s) {
                    shouldFail = "true".equalsIgnoreCase(s);
                }

                if (shouldFail) {
                    LOG.error("Shipping service unavailable");
                    throw new RuntimeException("shipping service unavailable");
                }
                String shipmentId = "shp_" + UUID.randomUUID().toString().substring(0, 8);
                LOG.infof("Booked shipping: %s", shipmentId);
                yield Map.of("shipment_id", shipmentId);
            }
            case "refund_payment" -> {
                @SuppressWarnings("unchecked")
                Map<String, Object> chargeResult = (Map<String, Object>) context.get("charge_payment");
                String paymentId = (String) chargeResult.get("payment_id");
                LOG.infof("Refunded payment: %s", paymentId);
                yield Map.of("refunded", true);
            }
            case "release_stock" -> {
                @SuppressWarnings("unchecked")
                Map<String, Object> reserveResult = (Map<String, Object>) context.get("reserve_stock");
                String reservationId = (String) reserveResult.get("reservation_id");
                LOG.infof("Released stock: %s", reservationId);
                yield Map.of("released", true);
            }
            case "cancel_shipping" -> {
                @SuppressWarnings("unchecked")
                Map<String, Object> bookResult = (Map<String, Object>) context.get("book_shipping");
                String shipmentId = (String) bookResult.get("shipment_id");
                LOG.infof("Cancelled shipping: %s", shipmentId);
                yield Map.of("cancelled", true);
            }
            default -> throw new IllegalArgumentException("Unknown step: " + stepName);
        };
    }

    private double getDouble(Map<String, Object> map, String key) {
        Object val = map.get(key);
        if (val instanceof Number n) {
            return n.doubleValue();
        }
        throw new IllegalArgumentException("Expected number for key: " + key);
    }
}
