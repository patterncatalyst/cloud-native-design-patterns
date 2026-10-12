package com.cndp.stream;

import java.math.BigDecimal;

import com.fasterxml.jackson.annotation.JsonProperty;

/** revenue.by-merchant value; field names and order are read by consumers in other languages. */
public record RevenueWindow(@JsonProperty("window_start") long windowStart,
                            @JsonProperty("window_end") long windowEnd,
                            @JsonProperty("merchant_id") String merchantId,
                            @JsonProperty("order_count") int orderCount,
                            BigDecimal revenue) {}
