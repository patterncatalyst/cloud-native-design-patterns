package com.cndp.order;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

import io.quarkus.logging.Log;
import io.quarkus.runtime.ShutdownDelayInitiatedEvent;
import io.quarkus.runtime.ShutdownEvent;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.event.Observes;

/**
 * Drain state. Quarkus runs the drain itself (quarkus.shutdown.delay-enabled, delay, timeout):
 * on SIGTERM it fires {@link ShutdownDelayInitiatedEvent}, keeps serving for the delay, then
 * stops HTTP and fires {@link ShutdownEvent}.
 */
@ApplicationScoped
public class ShutdownState {

    private final AtomicBoolean shuttingDown = new AtomicBoolean(false);
    private final AtomicInteger inFlight = new AtomicInteger(0);

    void onDelayInitiated(@Observes ShutdownDelayInitiatedEvent event) {
        shuttingDown.set(true);
        Log.info("SIGTERM received — readiness flipped to 503, draining...");
    }

    void onShutdown(@Observes ShutdownEvent event) {
        Log.infof("shutting down HTTP server (in_flight=%d)", inFlight.get());
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
