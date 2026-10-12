package com.cndp.order;

import java.math.BigDecimal;

import com.fasterxml.jackson.annotation.JsonProperty;

public record OrderRequest(@JsonProperty("merchant_id") String merchantId, String sku, int quantity,
                           BigDecimal total) {}
