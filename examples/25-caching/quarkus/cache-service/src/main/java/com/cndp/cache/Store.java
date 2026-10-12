package com.cndp.cache;

import java.time.Instant;
import java.util.Map;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import jakarta.transaction.Transactional;
import org.hibernate.StatelessSession;

/** The system of record: each method is one transaction over the Panache entities. */
@ApplicationScoped
@Transactional
public class Store {

    @Inject
    StatelessSession statelessSession;

    /** Returns null when the product does not exist. */
    public Product findProduct(String id) {
        ProductEntity entity = ProductEntity.findById(id);
        return entity == null ? null : entity.toProduct();
    }

    public void updateProduct(String id, String name, int priceCents) {
        ProductEntity entity = ProductEntity.findById(id);
        if (entity != null) {
            entity.name = name;
            entity.priceCents = priceCents;
        }
    }

    public void insertEvent(String id, String type, Map<String, Object> payload) {
        var event = new EventEntity();
        event.id = id;
        event.type = type;
        event.payload = payload == null ? Map.of() : payload;
        event.persist();
    }

    /** Returns null when the event does not exist. */
    public EventEntity findEvent(String id) {
        return EventEntity.findById(id);
    }

    /** Returns null when the metric has not been flushed yet. */
    public MetricEntity findMetric(String id) {
        return MetricEntity.findById(id);
    }

    public long countMetrics() {
        return MetricEntity.count();
    }

    /** INSERT ... ON CONFLICT (id) DO UPDATE through Hibernate's StatelessSession.upsert. */
    public void upsertMetric(String id, Map<String, String> payload) {
        var metric = new MetricEntity();
        metric.id = id;
        metric.payload = payload;
        metric.ts = Instant.now();
        statelessSession.upsert(metric);
    }
}
