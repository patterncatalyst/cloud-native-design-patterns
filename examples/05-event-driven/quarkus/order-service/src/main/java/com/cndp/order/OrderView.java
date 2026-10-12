package com.cndp.order;

import com.fasterxml.jackson.annotation.JsonProperty;

public record OrderView(String id, String sku, int quantity, String status,
                        @JsonProperty("created_at") String createdAt) {}
