package com.example.saga.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record SagaRequest(
    @JsonProperty("order_id") String orderId,
    String sku,
    double total,
    @JsonProperty("fail_shipping") Boolean failShipping
) {
    public boolean shouldFailShipping() {
        return failShipping != null && failShipping;
    }
}
