package com.cndp.order.domain;

/**
 * Value object — the command to place an order.
 * Validates on construction: sku must be non-empty, quantity must be positive.
 */
public final class PlaceOrderCmd {

    private final String sku;
    private final int quantity;

    public PlaceOrderCmd(String sku, int quantity) {
        if (sku == null || sku.isBlank()) {
            throw new IllegalArgumentException("sku is required");
        }
        if (quantity <= 0) {
            throw new IllegalArgumentException("quantity must be positive");
        }
        this.sku = sku;
        this.quantity = quantity;
    }

    public String sku() {
        return sku;
    }

    public int quantity() {
        return quantity;
    }
}
