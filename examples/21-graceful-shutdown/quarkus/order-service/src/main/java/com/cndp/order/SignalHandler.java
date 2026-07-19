package com.cndp.order;

import io.quarkus.logging.Log;
import io.quarkus.runtime.StartupEvent;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.event.Observes;
import jakarta.inject.Inject;
import sun.misc.Signal;

@ApplicationScoped
public class SignalHandler {

    @Inject
    ShutdownState shutdownState;

    void onStart(@Observes StartupEvent ev) {
        Signal.handle(new Signal("TERM"), signal -> {
            shutdownState.markShuttingDown();
            Log.info("SIGTERM received — readiness flipped to 503, draining...");
        });
        Log.infof("order-service started (PID=%d)", ProcessHandle.current().pid());
    }
}
