package com.cndp.order;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import org.eclipse.microprofile.health.HealthCheck;
import org.eclipse.microprofile.health.HealthCheckResponse;
import org.eclipse.microprofile.health.Readiness;

/** Readiness goes DOWN as soon as the shutdown delay starts; the datasource check covers the DB. */
@Readiness
@ApplicationScoped
public class DrainReadinessCheck implements HealthCheck {

    @Inject
    ShutdownState shutdownState;

    @Override
    public HealthCheckResponse call() {
        var builder = HealthCheckResponse.named("drain");
        return shutdownState.isShuttingDown()
                ? builder.down().withData("reason", "shutting down").build()
                : builder.up().build();
    }
}
