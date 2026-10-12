package com.example.stub;

import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.stereotype.Component;

/** Reports which stub answered, so /healthz in the liveness group carries the {@code source}. */
@Component("source")
class SourceHealthIndicator implements HealthIndicator {

    private final ServiceProperties service;

    SourceHealthIndicator(ServiceProperties service) {
        this.service = service;
    }

    @Override
    public Health health() {
        return Health.up().withDetail("source", service.name()).build();
    }
}
