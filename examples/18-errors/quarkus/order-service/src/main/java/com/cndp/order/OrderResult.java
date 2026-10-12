package com.cndp.order;

import com.fasterxml.jackson.annotation.JsonProperty;

public record OrderResult(String id, String sku, int quantity, String status,
                          @JsonProperty("remaining_stock") int remainingStock) {}
