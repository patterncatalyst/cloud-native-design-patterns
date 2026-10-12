package com.cndp.cache;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** Active-record entity over the shared {@code products} table (schema owned by db/init). */
@Entity
@Table(name = "products")
public class ProductEntity extends PanacheEntityBase {

    @Id
    public String id;

    @Column(nullable = false)
    public String name;

    @Column(name = "price_cents", nullable = false)
    public int priceCents;

    Product toProduct() {
        return new Product(id, name, priceCents);
    }
}
