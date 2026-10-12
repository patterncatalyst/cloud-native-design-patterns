package com.cndp.stub;

import jakarta.enterprise.context.ApplicationScoped;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.eclipse.microprofile.health.HealthCheck;
import org.eclipse.microprofile.health.HealthCheckResponse;
import org.eclipse.microprofile.health.Liveness;

/** Liveness names the stand-in this instance plays (legacy, monolith, new-service). */
@Liveness
@ApplicationScoped
public class SourceLivenessCheck implements HealthCheck {

    @ConfigProperty(name = "service.name", defaultValue = "unknown")
    String serviceName;

    @Override
    public HealthCheckResponse call() {
        return HealthCheckResponse.named("stub").up().withData("source", serviceName).build();
    }
}
