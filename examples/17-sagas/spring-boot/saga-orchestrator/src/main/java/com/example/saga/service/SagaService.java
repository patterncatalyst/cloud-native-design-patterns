package com.example.saga.service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import com.example.saga.entity.SagaEntity;
import com.example.saga.model.Saga;
import com.example.saga.model.SagaLogEntry;
import com.example.saga.model.SagaRequest;
import com.example.saga.repository.SagaLogRepository;
import com.example.saga.repository.SagaRepository;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class SagaService {

    private static final Logger log = LoggerFactory.getLogger(SagaService.class);

    private final SagaRepository sagas;
    private final SagaLogRepository sagaLog;
    private final SagaEngine engine;

    public SagaService(SagaRepository sagas, SagaLogRepository sagaLog, SagaEngine engine) {
        this.sagas = sagas;
        this.sagaLog = sagaLog;
        this.engine = engine;
    }

    public Saga createAndRun(SagaRequest request) {
        Map<String, Object> context = new LinkedHashMap<>();
        context.put("order_id", request.orderId());
        context.put("sku", request.sku());
        context.put("total", request.total());
        if (request.shouldFailShipping()) {
            context.put("fail_shipping", true);
        }

        String sagaId = sagas.save(new SagaEntity("RUNNING", context)).getId();

        advance(sagaId);
        return getSaga(sagaId);
    }

    public Saga getSaga(String sagaId) {
        return sagas.findById(sagaId)
            .map(s -> new Saga(s.getId(), s.getStatus(), s.getStepIndex(), s.getContext()))
            .orElse(null);
    }

    public List<SagaLogEntry> getSagaLog(String sagaId) {
        return sagaLog.findBySagaIdOrderByIdAsc(sagaId).stream()
            .map(e -> new SagaLogEntry(e.getStep(), e.getAction(), e.getResult()))
            .toList();
    }

    public void resumeRunningSagas() {
        for (SagaEntity saga : sagas.findByStatus("RUNNING")) {
            log.info("Resuming saga {}", saga.getId());
            advance(saga.getId());
        }
    }

    /** Runs steps until the saga completes, then compensates if a step failed. */
    private void advance(String sagaId) {
        String status;
        do {
            status = engine.advanceOnce(sagaId);
        } while ("RUNNING".equals(status));

        if ("COMPENSATING".equals(status)) {
            engine.compensate(sagaId);
        }
    }
}
