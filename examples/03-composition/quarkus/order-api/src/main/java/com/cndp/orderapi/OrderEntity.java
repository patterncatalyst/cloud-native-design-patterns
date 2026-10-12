package com.cndp.orderapi;

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

    @Column(nullable = false)
    public String sku;

    @Column(nullable = false)
    public int quantity;

    @Column(nullable = false)
    public String status;

    Order toDto() {
        return new Order(id, sku, quantity, status);
    }
}
