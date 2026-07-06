package com.cndp.gateway;

public record Order(String id, String sku, int quantity, String status) {
}
