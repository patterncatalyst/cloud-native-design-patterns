package com.cndp.edge;

import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

import io.quarkus.logging.Log;

public class CircuitBreaker {

    public static final String CLOSED = "closed";
    public static final String OPEN = "open";
    public static final String HALF_OPEN = "half_open";

    private final String name;
    private final int threshold;
    private final long resetTimeoutMs;

    private final AtomicReference<String> state = new AtomicReference<>(CLOSED);
    private final AtomicInteger failureCount = new AtomicInteger(0);
    private final AtomicInteger successCount = new AtomicInteger(0);
    private final AtomicLong openedAt = new AtomicLong(0);
    private final AtomicInteger totalCalls = new AtomicInteger(0);
    private final AtomicInteger totalRejected = new AtomicInteger(0);

    public CircuitBreaker(String name, int threshold, int resetTimeoutSeconds) {
        this.name = name;
        this.threshold = threshold;
        this.resetTimeoutMs = resetTimeoutSeconds * 1000L;
    }

    public synchronized boolean allow() {
        String current = state.get();
        if (CLOSED.equals(current)) {
            return true;
        }
        if (OPEN.equals(current)) {
            long elapsed = System.nanoTime() / 1_000_000 - openedAt.get();
            if (elapsed >= resetTimeoutMs) {
                state.set(HALF_OPEN);
                successCount.set(0);
                Log.infof("breaker [%s] -> half_open", name);
                return true;
            }
            return false;
        }
        return true;
    }

    public synchronized void recordSuccess() {
        totalCalls.incrementAndGet();
        if (HALF_OPEN.equals(state.get())) {
            int sc = successCount.incrementAndGet();
            if (sc >= 2) {
                state.set(CLOSED);
                failureCount.set(0);
                Log.infof("breaker [%s] -> closed (recovered)", name);
            }
        } else {
            failureCount.set(0);
        }
    }

    public synchronized void recordFailure() {
        totalCalls.incrementAndGet();
        failureCount.incrementAndGet();
        if (HALF_OPEN.equals(state.get())) {
            state.set(OPEN);
            openedAt.set(System.nanoTime() / 1_000_000);
            Log.infof("breaker [%s] -> open (half_open trial failed)", name);
        } else if (failureCount.get() >= threshold) {
            state.set(OPEN);
            openedAt.set(System.nanoTime() / 1_000_000);
            Log.infof("breaker [%s] -> open (threshold reached)", name);
        }
    }

    public synchronized void incrementRejected() {
        totalRejected.incrementAndGet();
    }

    public String getState() {
        return state.get();
    }

    public Map<String, Object> info() {
        return Map.of(
                "name", name,
                "state", state.get(),
                "failure_count", failureCount.get(),
                "threshold", threshold,
                "total_calls", totalCalls.get(),
                "total_rejected", totalRejected.get());
    }
}
