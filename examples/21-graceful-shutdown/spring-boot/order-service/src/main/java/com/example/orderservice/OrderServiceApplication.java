package com.example.orderservice;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import sun.misc.Signal;

@SpringBootApplication
public class OrderServiceApplication {

    private static final Logger log = LoggerFactory.getLogger(OrderServiceApplication.class);

    private static long drainDelaySeconds() {
        try {
            return Math.max(0, Long.parseLong(System.getenv().getOrDefault("DRAIN_DELAY_SECONDS", "5")));
        } catch (NumberFormatException e) {
            return 5;
        }
    }

    public static void main(String[] args) {
        // Register SIGTERM handler BEFORE Spring starts. One SIGTERM drives the whole drain:
        // flip readiness now, keep serving for the pre-stop delay so endpoints update, then
        // System.exit(0) runs Spring's shutdown hook: stop accepting connections, finish in-flight
        // requests (spring.lifecycle.timeout-per-shutdown-phase), close the pool.
        Signal.handle(new Signal("TERM"), signal -> {
            ShutdownState state = ShutdownState.getInstance();
            if (!state.markShuttingDown()) {
                return; // already draining
            }
            log.info("SIGTERM received — readiness flipped, draining in-flight requests");
            long delay = drainDelaySeconds();
            log.info("waiting {}s for endpoints to update", delay);
            Thread drain = new Thread(() -> {
                try {
                    Thread.sleep(delay * 1000);
                } catch (InterruptedException ignored) {
                    Thread.currentThread().interrupt();
                }
                log.info("shutting down HTTP server (in_flight={})", state.getInFlight());
                System.exit(0);
            }, "drain");
            drain.start();
        });

        SpringApplication.run(OrderServiceApplication.class, args);

        log.info("order-service started (PID={})", ProcessHandle.current().pid());
    }
}
