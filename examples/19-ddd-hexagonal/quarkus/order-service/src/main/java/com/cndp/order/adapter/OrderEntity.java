package com.cndp.order.adapter;

import java.time.Instant;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import com.cndp.order.domain.Order;

/** Persistence model of the {@code orders} table; the domain Order stays free of JPA. */
@Entity
@Table(name = "orders")
public class OrderEntity extends PanacheEntityBase {

    @Id
    public String id;

    @Column(nullable = false)
    public String sku;

    @Column(nullable = false)
    public int quantity;

    @Column(nullable = false)
    public String status;

    @Column(name = "created_at", nullable = false)
    public Instant createdAt;

    static OrderEntity from(Order order) {
        var entity = new OrderEntity();
        entity.id = order.id();
        entity.sku = order.sku();
        entity.quantity = order.quantity();
        entity.status = order.status();
        entity.createdAt = order.createdAt();
        return entity;
    }

    Order toDomain() {
        return new Order(id, sku, quantity, status, createdAt);
    }
}
