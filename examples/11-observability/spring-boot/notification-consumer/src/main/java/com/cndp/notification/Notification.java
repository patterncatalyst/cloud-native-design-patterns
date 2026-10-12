package com.cndp.notification;

import java.time.Instant;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** JPA entity over the shared {@code notifications} table; {@code order_id} is unique, the idempotency backstop. */
@Entity
@Table(name = "notifications")
public class Notification {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "order_id", nullable = false, unique = true)
    private String orderId;

    @Column(nullable = false)
    private String channel;

    /** Filled by the column default (now()). */
    @Column(name = "created_at", insertable = false, updatable = false)
    private Instant createdAt;

    protected Notification() {
    }

    public Notification(String orderId, String channel) {
        this.orderId = orderId;
        this.channel = channel;
    }
}
