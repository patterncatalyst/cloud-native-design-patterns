package com.example.orderservice;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.availability.AvailabilityChangeEvent;
import org.springframework.boot.availability.ReadinessState;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.context.SmartLifecycle;
import org.springframework.stereotype.Component;

/**
 * Pre-stop drain. Spring stops SmartLifecycle beans from the highest phase down, and the web
 * server's graceful-shutdown step sits at DEFAULT_PHASE - 1024, so this bean stops first: it
 * flips readiness, keeps the server answering for the drain delay so endpoints update, then
 * lets the graceful shutdown (server.shutdown=graceful) finish the in-flight requests.
 */
@Component
class DrainLifecycle implements SmartLifecycle {

    private static final Logger log = LoggerFactory.getLogger(DrainLifecycle.class);

    private final ShutdownState state;
    private final ApplicationEventPublisher events;
    private final long drainDelayMillis;
    private volatile boolean running;

    DrainLifecycle(ShutdownState state, ApplicationEventPublisher events,
                   @Value("${drain.delay-seconds:5}") long drainDelaySeconds) {
        this.state = state;
        this.events = events;
        this.drainDelayMillis = Math.max(0, drainDelaySeconds) * 1000;
    }

    @Override
    public void start() {
        running = true;
    }

    @Override
    public void stop() {
        running = false;
        if (!state.markShuttingDown()) {
            return;
        }
        log.info("SIGTERM received — readiness flipped, draining in-flight requests");
        AvailabilityChangeEvent.publish(events, this, ReadinessState.REFUSING_TRAFFIC);
        log.info("waiting {}ms for endpoints to update", drainDelayMillis);
        try {
            Thread.sleep(drainDelayMillis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        log.info("shutting down HTTP server (in_flight={})", state.getInFlight());
    }

    @Override
    public boolean isRunning() {
        return running;
    }

    @Override
    public int getPhase() {
        return DEFAULT_PHASE - 512;
    }
}
