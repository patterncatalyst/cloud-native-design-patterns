package com.cndp.order;

import java.time.Instant;
import java.util.Map;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/** JPA entity over the shared {@code outbox} table; Debezium tails this table's inserts. */
@Entity
@Table(name = "outbox")
public class OutboxEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "aggregate_id", nullable = false)
    private String aggregateId;

    @Column(name = "event_type", nullable = false)
    private String eventType;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false)
    private Map<String, Object> payload;

    /** Filled by the column default (now()). */
    @Column(name = "created_at", insertable = false, updatable = false)
    private Instant createdAt;

    protected OutboxEvent() {
    }

    public OutboxEvent(String aggregateId, String eventType, Map<String, Object> payload) {
        this.aggregateId = aggregateId;
        this.eventType = eventType;
        this.payload = payload;
    }

    public OutboxView toView() {
        return new OutboxView(id, aggregateId, eventType, payload, createdAt);
    }
}
