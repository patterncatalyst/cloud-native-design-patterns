package com.example.cache;

import com.fasterxml.jackson.annotation.JsonProperty;

public record ProductUpdate(String name, @JsonProperty("price_cents") int priceCents) {
}
