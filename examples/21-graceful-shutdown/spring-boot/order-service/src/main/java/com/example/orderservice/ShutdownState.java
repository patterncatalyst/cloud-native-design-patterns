package com.example.orderservice;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Singleton that tracks shutdown state and in-flight request count.
 * Shared between the SIGTERM signal handler (registered before Spring starts)
 * and the Spring-managed beans.
 */
public final class ShutdownState {

    private static final ShutdownState INSTANCE = new ShutdownState();

    private final AtomicBoolean shuttingDown = new AtomicBoolean(false);
    private final AtomicInteger inFlight = new AtomicInteger(0);

    private ShutdownState() {}

    public static ShutdownState getInstance() {
        return INSTANCE;
    }

    public void markShuttingDown() {
        shuttingDown.set(true);
    }

    public boolean isShuttingDown() {
        return shuttingDown.get();
    }

    public int incrementInFlight() {
        return inFlight.incrementAndGet();
    }

    public int decrementInFlight() {
        return inFlight.decrementAndGet();
    }

    public int getInFlight() {
        return inFlight.get();
    }
}
