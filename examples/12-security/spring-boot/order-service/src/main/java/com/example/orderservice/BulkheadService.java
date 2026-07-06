package com.example.orderservice;

import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Semaphore;

/**
 * Per-tenant bulkhead using a ConcurrentHashMap of Semaphores.
 * Each tenant gets an independent pool of {@value CAPACITY} permits.
 */
@Service
public class BulkheadService {

    static final int CAPACITY = 5;

    private final ConcurrentHashMap<String, Semaphore> semaphores = new ConcurrentHashMap<>();

    /**
     * Returns (or creates) the semaphore for the given tenant.
     */
    public Semaphore forTenant(String tenant) {
        return semaphores.computeIfAbsent(tenant, k -> new Semaphore(CAPACITY));
    }

    /**
     * Returns a snapshot of every tenant's semaphore state.
     */
    public Map<String, Map<String, Integer>> state() {
        Map<String, Map<String, Integer>> result = new LinkedHashMap<>();
        semaphores.forEach((tenant, sem) -> {
            Map<String, Integer> entry = new LinkedHashMap<>();
            entry.put("available", sem.availablePermits());
            entry.put("capacity", CAPACITY);
            result.put(tenant, entry);
        });
        return result;
    }
}
