package com.example.cache;

import com.fasterxml.jackson.annotation.JsonProperty;

/** A product as stored in the cache and returned by the API (without the {@code source} marker). */
public record ProductView(String id, String name, @JsonProperty("price_cents") int priceCents) {

    ProductResponse from(String source) {
        return new ProductResponse(id, name, priceCents, source);
    }
}
