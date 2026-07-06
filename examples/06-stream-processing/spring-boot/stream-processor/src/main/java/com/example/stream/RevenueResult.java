package com.example.stream;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.math.BigDecimal;

public record RevenueResult(
    @JsonProperty("window_start") long windowStart,
    @JsonProperty("window_end") long windowEnd,
    @JsonProperty("merchant_id") String merchantId,
    @JsonProperty("order_count") int orderCount,
    BigDecimal revenue
) {}
