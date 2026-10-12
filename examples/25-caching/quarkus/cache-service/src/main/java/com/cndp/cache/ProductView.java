package com.cndp.cache;

import com.fasterxml.jackson.annotation.JsonProperty;

/** Response shape: the product plus where it was served from ("cache" or "db"). */
public record ProductView(String id, String name, @JsonProperty("price_cents") int priceCents, String source) {

    static ProductView of(Product product, String source) {
        return new ProductView(product.id(), product.name(), product.priceCents(), source);
    }
}
