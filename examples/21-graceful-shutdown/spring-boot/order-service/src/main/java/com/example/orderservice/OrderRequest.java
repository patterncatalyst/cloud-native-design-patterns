package com.example.orderservice;

/**
 * Inbound request body for POST /orders.
 */
public record OrderRequest(String sku, int quantity) {}
