package com.cndp.order;

import java.math.BigDecimal;

import com.fasterxml.jackson.annotation.JsonProperty;

public record OrderResponse(String id, @JsonProperty("merchant_id") String merchantId, String sku, int quantity,
                            BigDecimal total, String status) {}
