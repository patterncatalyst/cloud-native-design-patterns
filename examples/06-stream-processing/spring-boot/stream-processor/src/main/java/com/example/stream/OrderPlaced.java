package com.example.stream;

import java.math.BigDecimal;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/** The fields of an {@code order.placed} event this processor reads; the rest are ignored. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record OrderPlaced(@JsonProperty("merchant_id") String merchantId, BigDecimal total) {
}
