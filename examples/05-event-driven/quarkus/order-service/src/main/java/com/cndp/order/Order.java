package com.cndp.order;

/** Response of POST /orders. */
public record Order(String id, String sku, int quantity, String status) {}
