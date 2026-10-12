package com.cndp.order;

import java.math.BigDecimal;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Kafka payload for order.placed. Field names and order are read by the stream processor and by
 * consumers in other languages: id, merchant_id, sku, quantity, total, status.
 */
public record OrderPlaced(String id, @JsonProperty("merchant_id") String merchantId, String sku, int quantity,
                          BigDecimal total, String status) {}
