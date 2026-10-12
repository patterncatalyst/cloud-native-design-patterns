package com.cndp.notification;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** Active-record entity over the shared {@code notifications} table (schema owned by db/init). */
@Entity
@Table(name = "notifications")
public class NotificationEntity extends PanacheEntityBase {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    public Long id;

    @Column(name = "order_id", nullable = false, unique = true)
    public String orderId;

    @Column(nullable = false)
    public String channel;
}
