package com.cndp.order.adapter;

import java.time.Instant;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PostLoad;
import jakarta.persistence.PostPersist;
import jakarta.persistence.Table;
import jakarta.persistence.Transient;

import org.springframework.data.domain.Persistable;

import com.cndp.order.domain.Order;

/**
 * Persistence model of the {@code orders} table. It lives in the adapter, so the domain
 * {@link Order} stays free of JPA annotations. The id is assigned by the domain, so the
 * entity says when it is new and Spring Data inserts without a prior SELECT.
 */
@Entity
@Table(name = "orders")
class OrderJpaEntity implements Persistable<String> {

    @Id
    private String id;

    @Column(nullable = false)
    private String sku;

    @Column(nullable = false)
    private int quantity;

    @Column(nullable = false)
    private String status;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Transient
    private boolean isNew = true;

    protected OrderJpaEntity() {
    }

    OrderJpaEntity(Order order) {
        this.id = order.id();
        this.sku = order.sku();
        this.quantity = order.quantity();
        this.status = order.status();
        this.createdAt = order.createdAt();
    }

    Order toDomain() {
        return new Order(id, sku, quantity, status, createdAt);
    }

    @Override
    public String getId() {
        return id;
    }

    @Override
    public boolean isNew() {
        return isNew;
    }

    @PostLoad
    @PostPersist
    void markNotNew() {
        this.isNew = false;
    }
}
