package com.example.saga.config;

import com.example.saga.service.SagaService;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

/**
 * On startup, resume any sagas that were left in RUNNING state
 * (e.g., due to a crash mid-execution).
 */
@Component
public class StartupRunner implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(StartupRunner.class);

    private final SagaService sagaService;

    public StartupRunner(SagaService sagaService) {
        this.sagaService = sagaService;
    }

    @Override
    public void run(ApplicationArguments args) {
        log.info("Checking for sagas to resume...");
        sagaService.resumeRunningSagas();
        log.info("saga-orchestrator started");
    }
}
