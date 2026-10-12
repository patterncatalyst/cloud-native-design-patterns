package com.example.orderservice;

/** The {@code order.placed} fact; Spring Kafka's JSON serializer writes it as {id, sku, quantity, status}. */
public record OrderEvent(String id, String sku, int quantity, String status) {
}
