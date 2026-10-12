package com.cndp.order;

import java.math.BigDecimal;
import java.time.Instant;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** Active-record entity over the shared {@code orders} table (schema owned by db/init). */
@Entity
@Table(name = "orders")
public class OrderEntity extends PanacheEntityBase {

    @Id
    public String id;

    @Column(name = "merchant_id", nullable = false)
    public String merchantId;

    @Column(nullable = false)
    public String sku;

    @Column(nullable = false)
    public int quantity;

    @Column(nullable = false, precision = 12, scale = 2)
    public BigDecimal total;

    @Column(nullable = false)
    public String status;

    /** Filled by the column default (now()); only used for ordering. */
    @Column(name = "created_at", insertable = false, updatable = false)
    public Instant createdAt;

    OrderResponse toResponse() {
        return new OrderResponse(id, merchantId, sku, quantity, total, status);
    }
}
