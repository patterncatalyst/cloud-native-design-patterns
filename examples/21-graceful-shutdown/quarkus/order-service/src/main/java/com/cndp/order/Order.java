package com.cndp.order;

public record Order(String id, String sku, int quantity, String status) {}
