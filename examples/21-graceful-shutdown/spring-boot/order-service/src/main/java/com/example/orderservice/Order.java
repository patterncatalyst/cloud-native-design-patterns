package com.example.orderservice;

/**
 * Order record returned from the API.
 */
public record Order(String id, String sku, int quantity, String status) {}
