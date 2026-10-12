package com.example.cache;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** JPA entity over the shared {@code products} table (schema and seed rows owned by db/init). */
@Entity
@Table(name = "products")
public class Product {

    @Id
    private String id;

    @Column(nullable = false)
    private String name;

    @Column(name = "price_cents", nullable = false)
    private int priceCents;

    protected Product() {
    }

    public void update(String name, int priceCents) {
        this.name = name;
        this.priceCents = priceCents;
    }

    public ProductView toView() {
        return new ProductView(id, name, priceCents);
    }
}
