package com.example.cache;

import com.fasterxml.jackson.annotation.JsonProperty;

/** A product plus where it came from: {@code "db"} or {@code "cache"}. */
public record ProductResponse(String id, String name, @JsonProperty("price_cents") int priceCents, String source) {
}
