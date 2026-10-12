package com.cndp.ws;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.stereotype.Component;

/** Reports which pod answered, so the pod name appears in the liveness group at /healthz. */
@Component("pod")
class PodHealthIndicator implements HealthIndicator {

    private final String podName;

    PodHealthIndicator(@Value("${POD_NAME:ws-pod-unknown}") String podName) {
        this.podName = podName;
    }

    @Override
    public Health health() {
        return Health.up().withDetail("pod", podName).build();
    }
}
