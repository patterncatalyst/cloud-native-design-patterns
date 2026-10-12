package com.cndp.order;

import jakarta.enterprise.context.ApplicationScoped;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.eclipse.microprofile.health.HealthCheck;
import org.eclipse.microprofile.health.HealthCheckResponse;
import org.eclipse.microprofile.health.Liveness;

/** Liveness reports the deployed version, so the Envoy traffic split is visible on /healthz. */
@Liveness
@ApplicationScoped
public class VersionLivenessCheck implements HealthCheck {

    @ConfigProperty(name = "app.version", defaultValue = "v1")
    String version;

    @Override
    public HealthCheckResponse call() {
        return HealthCheckResponse.named("version").up().withData("version", version).build();
    }
}
