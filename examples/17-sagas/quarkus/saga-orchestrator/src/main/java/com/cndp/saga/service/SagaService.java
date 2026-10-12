package com.cndp.saga.service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.cndp.saga.model.Saga;
import com.cndp.saga.model.SagaEntity;
import com.cndp.saga.model.SagaLogEntity;
import com.cndp.saga.model.SagaLogEntry;
import com.cndp.saga.model.SagaRequest;
import com.cndp.saga.model.SagaStep;
import io.quarkus.narayana.jta.QuarkusTransaction;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import jakarta.persistence.LockModeType;
import jakarta.transaction.Transactional;
import org.jboss.logging.Logger;

@ApplicationScoped
public class SagaService {
    private static final Logger LOG = Logger.getLogger(SagaService.class);

    private static final List<SagaStep> STEPS = List.of(
        new SagaStep("charge_payment", "refund_payment"),
        new SagaStep("reserve_stock", "release_stock"),
        new SagaStep("book_shipping", "cancel_shipping")
    );

    private enum Outcome { CONTINUE, DONE, COMPENSATE }

    @Inject
    StepExecutor stepExecutor;

    public Saga createAndRun(SagaRequest request) {
        var saga = new SagaEntity();
        saga.id = UUID.randomUUID().toString();
        saga.status = "RUNNING";
        saga.stepIndex = 0;
        saga.context = new HashMap<>();
        saga.context.put("order_id", request.orderId());
        saga.context.put("sku", request.sku());
        saga.context.put("total", request.total());
        if (request.failShipping() != null) {
            saga.context.put("fail_shipping", request.failShipping());
        }
        QuarkusTransaction.requiringNew().run(saga::persist);

        LOG.infof("Created saga: %s", saga.id);
        advance(saga.id);
        return getSaga(saga.id);
    }

    @Transactional
    public Saga getSaga(String id) {
        SagaEntity saga = SagaEntity.findById(id);
        return saga == null ? null : saga.toSaga();
    }

    @Transactional
    public List<SagaLogEntry> getSagaLog(String id) {
        return SagaLogEntity.<SagaLogEntity>list("sagaId = ?1 order by id", id)
                .stream().map(SagaLogEntity::toEntry).toList();
    }

    public void resumeRunningSagas() {
        try {
            List<String> runningIds = QuarkusTransaction.requiringNew().call(() ->
                SagaEntity.<SagaEntity>list("status", "RUNNING").stream().map(s -> s.id).toList());
            LOG.infof("Found %d running sagas to resume", runningIds.size());
            for (String id : runningIds) {
                try {
                    advance(id);
                } catch (Exception e) {
                    LOG.errorf(e, "Failed to resume saga: %s", id);
                }
            }
        } catch (Exception e) {
            LOG.error("Failed to resume running sagas", e);
        }
    }

    /** One transaction per step: the row lock and the step's effects commit together. */
    public void advance(String sagaId) {
        Outcome outcome;
        do {
            outcome = QuarkusTransaction.requiringNew().call(() -> advanceOneStep(sagaId));
        } while (outcome == Outcome.CONTINUE);

        if (outcome == Outcome.COMPENSATE) {
            compensate(sagaId);
        }
    }

    private Outcome advanceOneStep(String sagaId) {
        SagaEntity saga = SagaEntity.findById(sagaId, LockModeType.PESSIMISTIC_WRITE);
        if (saga == null) {
            return Outcome.DONE;
        }

        if (saga.stepIndex >= STEPS.size()) {
            saga.status = "COMPLETED";
            LOG.infof("Saga completed: %s", sagaId);
            return Outcome.DONE;
        }

        SagaStep step = STEPS.get(saga.stepIndex);
        Map<String, Object> context = new HashMap<>(saga.context);
        try {
            Map<String, Object> result = stepExecutor.execute(step.name(), context);
            SagaLogEntity.of(sagaId, step.name(), "execute", result).persist();
            context.put(step.name(), result);
            saga.context = context;
            saga.stepIndex++;
            return Outcome.CONTINUE;
        } catch (Exception e) {
            SagaLogEntity.of(sagaId, step.name(), "failed", Map.of("error", e.getMessage())).persist();
            saga.status = "COMPENSATING";
            return Outcome.COMPENSATE;
        }
    }

    public void compensate(String sagaId) {
        Saga saga = getSaga(sagaId);
        if (saga == null) {
            return;
        }

        for (int i = saga.stepIndex() - 1; i >= 0; i--) {
            SagaStep step = STEPS.get(i);
            try {
                Map<String, Object> result = stepExecutor.execute(step.compensate(), saga.context());
                logStep(sagaId, step.compensate(), "compensate", result);
            } catch (Exception e) {
                LOG.errorf(e, "Compensation failed for step: %s", step.compensate());
                logStep(sagaId, step.compensate(), "failed", Map.of("error", e.getMessage()));
            }
        }

        QuarkusTransaction.requiringNew().run(() -> {
            SagaEntity entity = SagaEntity.findById(sagaId);
            entity.status = "COMPENSATED";
        });
        LOG.infof("Saga compensated: %s", sagaId);
    }

    private void logStep(String sagaId, String step, String action, Map<String, Object> result) {
        QuarkusTransaction.requiringNew().run(() -> SagaLogEntity.of(sagaId, step, action, result).persist());
    }
}
