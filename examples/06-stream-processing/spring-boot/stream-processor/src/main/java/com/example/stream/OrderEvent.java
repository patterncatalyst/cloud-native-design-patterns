package com.example.stream;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;

@JsonIgnoreProperties(ignoreUnknown = true)
public record OrderEvent(
    String id,
    @JsonProperty("merchant_id") String merchantId,
    String sku,
    int quantity,
    BigDecimal total,
    String status
) {}
