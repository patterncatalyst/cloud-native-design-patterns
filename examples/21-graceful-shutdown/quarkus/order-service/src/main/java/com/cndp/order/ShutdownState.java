package com.cndp.order;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

import jakarta.enterprise.context.ApplicationScoped;

@ApplicationScoped
public class ShutdownState {

    private final AtomicBoolean shuttingDown = new AtomicBoolean(false);
    private final AtomicInteger inFlight = new AtomicInteger(0);

    /** Returns true only for the call that flips the flag. */
    public boolean markShuttingDown() {
        return shuttingDown.compareAndSet(false, true);
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
