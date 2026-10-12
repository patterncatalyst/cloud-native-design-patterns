package com.cndp.orderapi;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** JPA entity over the shared {@code orders} table (schema owned by db/init). */
@Entity
@Table(name = "orders")
public class Order {

    @Id
    private String id;

    @Column(nullable = false)
    private String sku;

    @Column(nullable = false)
    private int quantity;

    @Column(nullable = false)
    private String status;

    protected Order() {
    }

    public OrderView toView() {
        return new OrderView(id, sku, quantity, status);
    }
}
