package com.example.order;

import java.math.BigDecimal;
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

    @Column(name = "merchant_id", nullable = false)
    private String merchantId;

    @Column(nullable = false)
    private String sku;

    @Column(nullable = false)
    private int quantity;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal total;

    @Column(nullable = false)
    private String status;

    /** Filled by the column default (now()). */
    @Column(name = "created_at", insertable = false, updatable = false)
    private Instant createdAt;

    protected OrderEntity() {
    }

    public OrderEntity(String merchantId, String sku, int quantity, BigDecimal total, String status) {
        this.merchantId = merchantId;
        this.sku = sku;
        this.quantity = quantity;
        this.total = total;
        this.status = status;
    }

    public OrderEvent toEvent() {
        return new OrderEvent(id, merchantId, sku, quantity, total, status);
    }
}
