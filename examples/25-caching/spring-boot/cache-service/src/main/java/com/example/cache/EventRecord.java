package com.example.cache;

import java.time.Instant;
import java.util.Map;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PostLoad;
import jakarta.persistence.PostPersist;
import jakarta.persistence.Table;
import jakarta.persistence.Transient;

import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import org.springframework.data.domain.Persistable;

/** JPA entity over the shared {@code events} table. The caller assigns the id, so a duplicate id fails the insert. */
@Entity
@Table(name = "events")
public class EventRecord implements Persistable<String> {

    @Id
    private String id;

    @Column(nullable = false)
    private String type;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false)
    private Map<String, Object> payload;

    @Column(insertable = false, updatable = false)
    private Instant ts;

    @Transient
    private boolean isNew = true;

    protected EventRecord() {
    }

    public EventRecord(String id, String type, Map<String, Object> payload) {
        this.id = id;
        this.type = type;
        this.payload = payload;
    }

    public EventView toView() {
        return new EventView(id, type, payload);
    }

    @Override
    public String getId() {
        return id;
    }

    @Override
    public boolean isNew() {
        return isNew;
    }

    @PostLoad
    @PostPersist
    void markNotNew() {
        this.isNew = false;
    }
}
