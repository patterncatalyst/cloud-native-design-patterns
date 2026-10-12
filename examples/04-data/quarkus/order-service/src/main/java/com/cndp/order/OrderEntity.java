package com.cndp.order;

import java.time.Instant;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Generated;
import org.hibernate.generator.EventType;

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

    /** Filled by the column default (now()) and read back on insert. */
    @Generated(event = EventType.INSERT)
    @Column(name = "created_at", insertable = false, updatable = false)
    public Instant createdAt;

    OrderView toView() {
        return new OrderView(id, sku, quantity, status, PgTimestamps.format(createdAt));
    }
}
