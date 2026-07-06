package com.example.order;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;

public record OrderEvent(
    String id,
    @JsonProperty("merchant_id") String merchantId,
    String sku,
    int quantity,
    BigDecimal total,
    String status
) {}
