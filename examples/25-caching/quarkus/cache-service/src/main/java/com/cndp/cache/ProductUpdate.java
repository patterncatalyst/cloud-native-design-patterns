package com.cndp.cache;

import com.fasterxml.jackson.annotation.JsonProperty;

public record ProductUpdate(String name, @JsonProperty("price_cents") Integer priceCents) {}
