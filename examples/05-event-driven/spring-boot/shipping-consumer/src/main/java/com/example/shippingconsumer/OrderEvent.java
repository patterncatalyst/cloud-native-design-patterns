package com.example.shippingconsumer;

/** The {@code order.placed} fact as published by the order service. */
public record OrderEvent(String id, String sku, int quantity, String status) {
}
