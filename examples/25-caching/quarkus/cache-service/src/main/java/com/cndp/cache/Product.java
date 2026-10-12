package com.cndp.cache;

import com.fasterxml.jackson.annotation.JsonProperty;

/** Cached shape of a product: {"id","name","price_cents"}. Also the value type of the read-through cache. */
public record Product(String id, String name, @JsonProperty("price_cents") int priceCents) {}
