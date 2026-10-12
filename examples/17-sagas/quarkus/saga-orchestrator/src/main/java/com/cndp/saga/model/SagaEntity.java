package com.cndp.saga.model;

import java.time.Instant;
import java.util.Map;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;

/** Active-record entity over the shared {@code sagas} table (schema owned by db/init). */
@Entity
@Table(name = "sagas")
public class SagaEntity extends PanacheEntityBase {

    @Id
    public String id;

    @Column(nullable = false)
    public String status;

    @Column(name = "step_index", nullable = false)
    public int stepIndex;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false)
    public Map<String, Object> context;

    @Column(name = "created_at", insertable = false, updatable = false)
    public Instant createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    public Instant updatedAt;

    public Saga toSaga() {
        return new Saga(id, status, stepIndex, context);
    }
}
