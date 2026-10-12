package com.example.orderservice;

import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.stereotype.Component;

/** Readiness contributor "drain": DOWN with a reason once the shutdown drain has started. */
@Component("drain")
class DrainHealthIndicator implements HealthIndicator {

    private final ShutdownState state;

    DrainHealthIndicator(ShutdownState state) {
        this.state = state;
    }

    @Override
    public Health health() {
        return state.isShuttingDown()
                ? Health.down().withDetail("reason", "shutting down").build()
                : Health.up().build();
    }
}
