package com.example.orderservice;

import java.time.Instant;

import com.fasterxml.jackson.annotation.JsonProperty;

/** Order as listed by GET /orders. */
public record OrderView(String id, String sku, int quantity, String status,
                        @JsonProperty("created_at") Instant createdAt) {
}
