package com.cndp.order;

/** Response shape for REST and GraphQL; the entity never leaves the service. */
public record Order(String id, String sku, int quantity, String status) {}
