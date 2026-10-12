package com.example.cache;

import java.time.Instant;
import java.util.Map;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/** JPA entity over the shared {@code metrics} table; rows are written by {@link MetricRepository#upsert}. */
@Entity
@Table(name = "metrics")
public class Metric {

    @Id
    private String id;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false)
    private Map<String, Object> payload;

    @Column(insertable = false, updatable = false)
    private Instant ts;

    protected Metric() {
    }

    public String getId() {
        return id;
    }

    public Map<String, Object> getPayload() {
        return payload;
    }
}
