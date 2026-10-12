package com.cndp.order;

import java.math.BigDecimal;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** JPA entity over the shared {@code orders} table (schema owned by db/init). */
@Entity
@Table(name = "orders")
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(nullable = false)
    private String customer;

    @Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal total;

    protected Order() {
    }

    public Order(String customer, BigDecimal total) {
        this.customer = customer;
        this.total = total;
    }

    public Integer getId() {
        return id;
    }

    public String getCustomer() {
        return customer;
    }

    public BigDecimal getTotal() {
        return total;
    }
}
