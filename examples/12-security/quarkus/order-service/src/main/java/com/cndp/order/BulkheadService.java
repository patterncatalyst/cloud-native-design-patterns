package com.cndp.order;

import jakarta.enterprise.context.ApplicationScoped;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Semaphore;

@ApplicationScoped
public class BulkheadService {

    static final int CAPACITY = 5;

    private final ConcurrentHashMap<String, Semaphore> semaphores = new ConcurrentHashMap<>();

    public Semaphore forTenant(String tenant) {
        return semaphores.computeIfAbsent(tenant, k -> new Semaphore(CAPACITY));
    }

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
