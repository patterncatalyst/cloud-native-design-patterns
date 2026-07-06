package com.example.orderservice;

/**
 * Inbound order payload.
 */
public record OrderRequest(String sku, int quantity, String tenant) {
}
