package com.cndp.order;

import java.math.BigDecimal;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** Active-record entity over the shared {@code orders} table (schema owned by db/init). */
@Entity
@Table(name = "orders")
public class Order extends PanacheEntityBase {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    public Integer id;

    @Column(nullable = false)
    public String customer;

    @Column(nullable = false, precision = 10, scale = 2)
    public BigDecimal total;
}
