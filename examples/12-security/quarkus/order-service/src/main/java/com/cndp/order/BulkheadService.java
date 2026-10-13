package com.cndp.order;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;

import io.smallrye.faulttolerance.api.Guard;
import jakarta.enterprise.context.ApplicationScoped;

/**
 * Per-tenant bulkhead: one SmallRye Fault Tolerance guard per tenant (the programmatic API, since an annotation
 * cannot be keyed by tenant). Each allows 5 concurrent calls with no queue, so the sixth fails at once with
 * BulkheadException.
 */
@ApplicationScoped
public class BulkheadService {

    static final int CAPACITY = 5;

    private record Pool(Guard guard, AtomicInteger inFlight) {}

    private final ConcurrentHashMap<String, Pool> pools = new ConcurrentHashMap<>();

    public <T> T run(String tenant, Supplier<T> work, Class<T> type) {
        return pools.computeIfAbsent(tenant, t -> newPool()).guard().get(work, type);
    }

    private static Pool newPool() {
        var inFlight = new AtomicInteger();
        var guard = Guard.create()
                .withBulkhead().limit(CAPACITY)
                    .onAccepted(inFlight::incrementAndGet)
                    .onFinished(inFlight::decrementAndGet)
                    .done()
                .build();
        return new Pool(guard, inFlight);
    }

    /** Every tenant's pool: permits still available and capacity. */
    public Map<String, Map<String, Integer>> state() {
        Map<String, Map<String, Integer>> result = new LinkedHashMap<>();
        pools.forEach((tenant, pool) -> result.put(tenant,
                Map.of("available", CAPACITY - pool.inFlight().get(), "capacity", CAPACITY)));
        return result;
    }
}
