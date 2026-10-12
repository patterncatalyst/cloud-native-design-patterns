package com.cndp.ws;

import jakarta.enterprise.context.ApplicationScoped;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.eclipse.microprofile.health.HealthCheck;
import org.eclipse.microprofile.health.HealthCheckResponse;
import org.eclipse.microprofile.health.Liveness;

/** Liveness reports which pod answered, so the two-pod demo can tell them apart. */
@Liveness
@ApplicationScoped
public class PodLivenessCheck implements HealthCheck {

    @ConfigProperty(name = "pod.name", defaultValue = "ws-pod-unknown")
    String podName;

    @Override
    public HealthCheckResponse call() {
        return HealthCheckResponse.named("pod").up().withData("pod", podName).build();
    }
}
