package com.cndp.order;

import io.quarkus.logging.Log;
import io.quarkus.runtime.Quarkus;
import io.quarkus.runtime.StartupEvent;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.event.Observes;
import jakarta.inject.Inject;
import sun.misc.Signal;

@ApplicationScoped
public class SignalHandler {

    @Inject
    ShutdownState shutdownState;

    private static long drainDelaySeconds() {
        try {
            return Math.max(0, Long.parseLong(System.getenv().getOrDefault("DRAIN_DELAY_SECONDS", "5")));
        } catch (NumberFormatException e) {
            return 5;
        }
    }

    void onStart(@Observes StartupEvent ev) {
        // One SIGTERM drives the whole drain: flip readiness now, keep serving for the pre-stop
        // delay so endpoints update, then ask Quarkus to exit. Its shutdown stops accepting
        // connections, waits for in-flight requests (quarkus.shutdown.timeout) and closes the pool.
        Signal.handle(new Signal("TERM"), signal -> {
            if (!shutdownState.markShuttingDown()) {
                return; // already draining
            }
            Log.info("SIGTERM received — readiness flipped to 503, draining...");
            long delay = drainDelaySeconds();
            Log.infof("waiting %ds for endpoints to update", delay);
            Thread drain = new Thread(() -> {
                try {
                    Thread.sleep(delay * 1000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                Log.infof("shutting down HTTP server (in_flight=%d)", shutdownState.getInFlight());
                Quarkus.asyncExit(0);
            }, "drain");
            drain.start();
        });
        Log.infof("order-service started (PID=%d)", ProcessHandle.current().pid());
    }
}
