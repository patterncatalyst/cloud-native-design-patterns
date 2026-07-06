package com.example.order;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;

public record OrderRequest(
    @JsonProperty("merchant_id") String merchantId,
    String sku,
    int quantity,
    BigDecimal total
) {}
