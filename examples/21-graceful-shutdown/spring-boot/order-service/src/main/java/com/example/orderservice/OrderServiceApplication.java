package com.example.orderservice;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import sun.misc.Signal;

@SpringBootApplication
public class OrderServiceApplication {

    private static final Logger log = LoggerFactory.getLogger(OrderServiceApplication.class);

    public static void main(String[] args) {
        // Register SIGTERM handler BEFORE Spring starts.
        // This replaces the JVM default handler (which would trigger shutdown hooks),
        // so Spring does NOT start shutting down the embedded server.
        // The service keeps running but flips the shutting_down flag.
        Signal.handle(new Signal("TERM"), signal -> {
            ShutdownState state = ShutdownState.getInstance();
            state.markShuttingDown();
            log.info("SIGTERM received — readiness flipped, draining in-flight requests");
        });

        SpringApplication.run(OrderServiceApplication.class, args);

        log.info("order-service started (PID={})", ProcessHandle.current().pid());
    }
}
