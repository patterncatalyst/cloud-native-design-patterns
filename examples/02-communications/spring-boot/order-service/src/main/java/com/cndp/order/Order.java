package com.cndp.order;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import org.hibernate.annotations.UuidGenerator;

/** JPA entity over the shared {@code orders} table (schema owned by db/init). */
@Entity
@Table(name = "orders")
public class Order {

    @Id
    @UuidGenerator
    private String id;

    @Column(nullable = false)
    private String sku;

    @Column(nullable = false)
    private int quantity;

    @Column(nullable = false)
    private String status;

    protected Order() {
    }

    public Order(String sku, int quantity, String status) {
        this.sku = sku;
        this.quantity = quantity;
        this.status = status;
    }

    public OrderView toView() {
        return new OrderView(id, sku, quantity, status);
    }
}
