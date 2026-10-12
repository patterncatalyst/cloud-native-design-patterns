package com.example.saga.entity;

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

/** JPA entity over the shared {@code saga_log} table. */
@Entity
@Table(name = "saga_log")
public class SagaLogEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "saga_id", nullable = false)
    private String sagaId;

    @Column(nullable = false)
    private String step;

    @Column(nullable = false)
    private String action;

    @JdbcTypeCode(SqlTypes.JSON)
    private Map<String, Object> result;

    @Column(name = "created_at", insertable = false, updatable = false)
    private Instant createdAt;

    protected SagaLogEntity() {
    }

    public SagaLogEntity(String sagaId, String step, String action, Map<String, Object> result) {
        this.sagaId = sagaId;
        this.step = step;
        this.action = action;
        this.result = result;
    }

    public String getStep() {
        return step;
    }

    public String getAction() {
        return action;
    }

    public Map<String, Object> getResult() {
        return result;
    }
}
