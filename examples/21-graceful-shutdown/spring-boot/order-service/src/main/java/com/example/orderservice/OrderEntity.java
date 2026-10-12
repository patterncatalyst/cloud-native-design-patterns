package com.example.orderservice;

import java.time.Instant;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import org.hibernate.annotations.UuidGenerator;

/** JPA entity over the shared {@code orders} table (schema owned by db/init). */
@Entity
@Table(name = "orders")
public class OrderEntity {

    @Id
    @UuidGenerator
    private String id;

    @Column(nullable = false)
    private String sku;

    @Column(nullable = false)
    private int quantity;

    @Column(nullable = false)
    private String status;

    /** Filled by the column default (now()). */
    @Column(name = "created_at", insertable = false, updatable = false)
    private Instant createdAt;

    protected OrderEntity() {
    }

    public OrderEntity(String sku, int quantity, String status) {
        this.sku = sku;
        this.quantity = quantity;
        this.status = status;
    }

    public Order toOrder() {
        return new Order(id, sku, quantity, status);
    }
}
