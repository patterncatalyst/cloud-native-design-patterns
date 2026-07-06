package com.cndp.order.domain;

/**
 * Domain event — emitted after an order is successfully created and persisted.
 */
public final class OrderPlaced {

    private final String orderId;
    private final String sku;
    private final int quantity;

    public OrderPlaced(String orderId, String sku, int quantity) {
        this.orderId = orderId;
        this.sku = sku;
        this.quantity = quantity;
    }

    public String orderId() { return orderId; }
    public String sku() { return sku; }
    public int quantity() { return quantity; }
}
