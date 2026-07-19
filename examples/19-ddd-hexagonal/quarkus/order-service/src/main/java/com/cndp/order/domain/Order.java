package com.cndp.order.domain;

import java.time.Instant;
import java.util.UUID;

public final class Order {

    private final String id;
    private final String sku;
    private final int quantity;
    private final String status;
    private final Instant createdAt;

    public Order(String id, String sku, int quantity, String status, Instant createdAt) {
        this.id = id;
        this.sku = sku;
        this.quantity = quantity;
        this.status = status;
        this.createdAt = createdAt;
    }

    public static Order create(PlaceOrderCmd cmd) {
        return new Order(
                UUID.randomUUID().toString(),
                cmd.sku(),
                cmd.quantity(),
                "placed",
                Instant.now()
        );
    }

    public String id() { return id; }
    public String sku() { return sku; }
    public int quantity() { return quantity; }
    public String status() { return status; }
    public Instant createdAt() { return createdAt; }
}
