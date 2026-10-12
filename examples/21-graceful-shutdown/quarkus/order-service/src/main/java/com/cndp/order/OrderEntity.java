package com.cndp.order;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;

import org.hibernate.annotations.UuidGenerator;

/** Active-record entity over the shared {@code orders} table (schema owned by db/init). */
@Entity
@Table(name = "orders")
public class OrderEntity extends PanacheEntityBase {

    @Id
    @UuidGenerator
    public String id;

    @Column(nullable = false)
    public String sku;

    @Column(nullable = false)
    public int quantity;

    @Column(nullable = false)
    public String status;

    /** Filled by the column default (now()). */
    @Column(name = "created_at", insertable = false, updatable = false)
    public Instant createdAt;

    Order toDto() {
        return new Order(id, sku, quantity, status);
    }
}
