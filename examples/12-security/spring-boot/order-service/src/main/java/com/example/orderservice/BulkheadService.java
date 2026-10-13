package com.example.orderservice;

import java.util.LinkedHashMap;
import java.util.Map;

import io.github.resilience4j.bulkhead.Bulkhead;
import io.github.resilience4j.bulkhead.BulkheadRegistry;
import org.springframework.stereotype.Service;

/**
 * Per-tenant bulkhead: one Resilience4j bulkhead per tenant, created on first use from the "tenant" configuration
 * (resilience4j.bulkhead.configs.tenant: 5 concurrent calls, no waiting).
 */
@Service
public class BulkheadService {

    private final BulkheadRegistry registry;

    public BulkheadService(BulkheadRegistry registry) {
        this.registry = registry;
    }

    public Bulkhead forTenant(String tenant) {
        return registry.bulkhead(tenant, "tenant");
    }

    /** Every tenant's pool: permits still available and capacity. */
    public Map<String, Map<String, Integer>> state() {
        Map<String, Map<String, Integer>> result = new LinkedHashMap<>();
        registry.getAllBulkheads().forEach(b -> result.put(b.getName(), Map.of(
                "available", b.getMetrics().getAvailableConcurrentCalls(),
                "capacity", b.getMetrics().getMaxAllowedConcurrentCalls())));
        return result;
    }
}
