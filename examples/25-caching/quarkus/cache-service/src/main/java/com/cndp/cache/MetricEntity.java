package com.cndp.cache;

import java.time.Instant;
import java.util.Map;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/** Active-record entity over the shared {@code metrics} table (write-back target). */
@Entity
@Table(name = "metrics")
public class MetricEntity extends PanacheEntityBase {

    @Id
    public String id;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false)
    public Map<String, String> payload;

    @Column(nullable = false)
    public Instant ts;
}
