package com.cndp.saga;

import com.cndp.saga.service.SagaService;
import io.quarkus.runtime.StartupEvent;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.event.Observes;
import jakarta.inject.Inject;
import org.jboss.logging.Logger;

@ApplicationScoped
public class StartupResumer {
    private static final Logger LOG = Logger.getLogger(StartupResumer.class);

    @Inject
    SagaService sagaService;

    void onStart(@Observes StartupEvent ev) {
        LOG.info("Checking for sagas to resume...");
        sagaService.resumeRunningSagas();
        LOG.info("saga-orchestrator started");
    }
}
