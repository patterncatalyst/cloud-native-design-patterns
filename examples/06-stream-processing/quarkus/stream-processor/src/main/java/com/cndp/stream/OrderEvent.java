package com.cndp.stream;

import java.math.BigDecimal;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/** order.placed as the topology reads it; producers in other languages may add fields. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record OrderEvent(@JsonProperty("merchant_id") String merchantId, BigDecimal total) {}
