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

/** Active-record entity over the shared {@code events} table (write-around target). */
@Entity
@Table(name = "events")
public class EventEntity extends PanacheEntityBase {

    @Id
    public String id;

    @Column(nullable = false)
    public String type;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false)
    public Map<String, Object> payload;

    @Column(insertable = false, updatable = false)
    public Instant ts;
}
