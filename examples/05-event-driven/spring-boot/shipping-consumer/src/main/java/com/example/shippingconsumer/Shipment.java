package com.example.shippingconsumer;

import java.time.Instant;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** JPA entity over the shared {@code shipments} table; {@code order_id} is unique, the idempotency backstop. */
@Entity
@Table(name = "shipments")
public class Shipment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "order_id", nullable = false, unique = true)
    private String orderId;

    @Column(nullable = false)
    private String status;

    /** Filled by the column default (now()). */
    @Column(name = "created_at", insertable = false, updatable = false)
    private Instant createdAt;

    protected Shipment() {
    }

    public Shipment(String orderId, String status) {
        this.orderId = orderId;
        this.status = status;
    }
}
