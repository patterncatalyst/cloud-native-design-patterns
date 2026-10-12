package com.example.stream;

import java.math.BigDecimal;

import com.fasterxml.jackson.annotation.JsonProperty;

/** One (merchant, window) row of {@code revenue.by-merchant}; epoch seconds for the window bounds. */
public record MerchantRevenue(
        @JsonProperty("window_start") long windowStart,
        @JsonProperty("window_end") long windowEnd,
        @JsonProperty("merchant_id") String merchantId,
        @JsonProperty("order_count") int orderCount,
        BigDecimal revenue) {
}
