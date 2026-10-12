package com.example.saga.service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import com.example.saga.entity.SagaEntity;
import com.example.saga.entity.SagaLogEntity;
import com.example.saga.model.SagaStep;
import com.example.saga.repository.SagaLogRepository;
import com.example.saga.repository.SagaRepository;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** The transactional units of the saga: one forward step, or the whole compensation. */
@Service
public class SagaEngine {

    private static final Logger log = LoggerFactory.getLogger(SagaEngine.class);

    static final List<SagaStep> STEPS = List.of(
        new SagaStep("charge_payment", "refund_payment"),
        new SagaStep("reserve_stock", "release_stock"),
        new SagaStep("book_shipping", "cancel_shipping")
    );

    private final SagaRepository sagas;
    private final SagaLogRepository sagaLog;
    private final StepExecutor stepExecutor;

    public SagaEngine(SagaRepository sagas, SagaLogRepository sagaLog, StepExecutor stepExecutor) {
        this.sagas = sagas;
        this.sagaLog = sagaLog;
        this.stepExecutor = stepExecutor;
    }

    /**
     * Executes the next step under a row lock. On success increments step_index; on failure marks the
     * saga COMPENSATING. Returns the saga status afterwards (NOT_FOUND when there is no such saga).
     */
    @Transactional
    public String advanceOnce(String sagaId) {
        SagaEntity saga = sagas.lockById(sagaId).orElse(null);
        if (saga == null) {
            return "NOT_FOUND";
        }
        if (!"RUNNING".equals(saga.getStatus())) {
            return saga.getStatus();
        }

        int stepIndex = saga.getStepIndex();
        if (stepIndex >= STEPS.size()) {
            saga.setStatus("COMPLETED");
            return "COMPLETED";
        }

        SagaStep step = STEPS.get(stepIndex);
        try {
            Map<String, Object> result = stepExecutor.execute(step.name(), saga.getContext());
            Map<String, Object> context = new LinkedHashMap<>(saga.getContext());
            context.put(step.name(), result);

            sagaLog.save(new SagaLogEntity(sagaId, step.name(), "execute", result));
            saga.setStepIndex(stepIndex + 1);
            saga.setContext(context);
            return "RUNNING";
        } catch (Exception e) {
            log.error("Step {} failed: {} -- starting compensation", step.name(), e.getMessage());
            sagaLog.save(new SagaLogEntity(sagaId, step.name(), "failed", Map.of("error", e.getMessage())));
            saga.setStatus("COMPENSATING");
            return "COMPENSATING";
        }
    }

    /** Compensates completed steps in reverse order, from step_index-1 down to 0. */
    @Transactional
    public void compensate(String sagaId) {
        SagaEntity saga = sagas.findById(sagaId).orElseThrow();
        for (int i = saga.getStepIndex() - 1; i >= 0; i--) {
            String compName = STEPS.get(i).compensate();
            Map<String, Object> result = stepExecutor.execute(compName, saga.getContext());
            sagaLog.save(new SagaLogEntity(sagaId, compName, "compensate", result));
        }
        saga.setStatus("COMPENSATED");
        log.info("Saga {} fully compensated", sagaId);
    }
}
