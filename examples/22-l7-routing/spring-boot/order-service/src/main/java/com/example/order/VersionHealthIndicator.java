package com.example.order;

import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.stereotype.Component;

/** Reports the replica's version in the liveness group, so /healthz shows which backend answered. */
@Component("version")
class VersionHealthIndicator implements HealthIndicator {

    private final AppProperties app;

    VersionHealthIndicator(AppProperties app) {
        this.app = app;
    }

    @Override
    public Health health() {
        return Health.up().withDetail("version", app.version()).build();
    }
}
