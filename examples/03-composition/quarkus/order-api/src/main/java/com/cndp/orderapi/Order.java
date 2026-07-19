package com.cndp.orderapi;

public record Order(
    String id,
    String sku,
    int quantity,
    String status
) {}
