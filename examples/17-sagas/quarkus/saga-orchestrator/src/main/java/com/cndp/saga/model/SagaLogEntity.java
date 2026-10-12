package com.cndp.saga.model;

import java.time.Instant;
import java.util.Map;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/** Active-record entity over the shared {@code saga_log} table. */
@Entity
@Table(name = "saga_log")
public class SagaLogEntity extends PanacheEntityBase {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    public Long id;

    @Column(name = "saga_id", nullable = false)
    public String sagaId;

    @Column(nullable = false)
    public String step;

    @Column(nullable = false)
    public String action;

    @JdbcTypeCode(SqlTypes.JSON)
    public Map<String, Object> result;

    @Column(name = "created_at", insertable = false, updatable = false)
    public Instant createdAt;

    public static SagaLogEntity of(String sagaId, String step, String action, Map<String, Object> result) {
        var entry = new SagaLogEntity();
        entry.sagaId = sagaId;
        entry.step = step;
        entry.action = action;
        entry.result = result;
        return entry;
    }

    public SagaLogEntry toEntry() {
        return new SagaLogEntry(step, action, result);
    }
}
