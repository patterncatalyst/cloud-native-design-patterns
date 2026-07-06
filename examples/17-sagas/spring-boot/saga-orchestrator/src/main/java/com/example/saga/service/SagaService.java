package com.example.saga.service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.example.saga.model.Saga;
import com.example.saga.model.SagaLogEntry;
import com.example.saga.model.SagaRequest;
import com.example.saga.model.SagaStep;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

@Service
public class SagaService {

    private static final Logger log = LoggerFactory.getLogger(SagaService.class);
    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};

    private static final List<SagaStep> STEPS = List.of(
        new SagaStep("charge_payment", "refund_payment"),
        new SagaStep("reserve_stock", "release_stock"),
        new SagaStep("book_shipping", "cancel_shipping")
    );

    private final JdbcClient jdbc;
    private final ObjectMapper mapper;
    private final StepExecutor stepExecutor;
    private final TransactionTemplate txTemplate;

    public SagaService(JdbcClient jdbc, ObjectMapper mapper, StepExecutor stepExecutor,
                       PlatformTransactionManager txManager) {
        this.jdbc = jdbc;
        this.mapper = mapper;
        this.stepExecutor = stepExecutor;
        this.txTemplate = new TransactionTemplate(txManager);
    }

    public Saga createAndRun(SagaRequest request) {
        String sagaId = UUID.randomUUID().toString();
        Map<String, Object> context = new LinkedHashMap<>();
        context.put("order_id", request.orderId());
        context.put("sku", request.sku());
        context.put("total", request.total());
        if (request.shouldFailShipping()) {
            context.put("fail_shipping", true);
        }

        jdbc.sql("INSERT INTO sagas (id, status, step_index, context) VALUES (:id, 'RUNNING', 0, :context::jsonb)")
            .param("id", sagaId)
            .param("context", toJson(context))
            .update();

        advance(sagaId);
        return getSaga(sagaId);
    }

    public Saga getSaga(String sagaId) {
        return jdbc.sql("SELECT id, status, step_index, context FROM sagas WHERE id = :id")
            .param("id", sagaId)
            .query((rs, rowNum) -> new Saga(
                rs.getString("id"),
                rs.getString("status"),
                rs.getInt("step_index"),
                fromJson(rs.getString("context"))
            ))
            .optional()
            .orElse(null);
    }

    public List<SagaLogEntry> getSagaLog(String sagaId) {
        return jdbc.sql("SELECT step, action, result FROM saga_log WHERE saga_id = :sagaId ORDER BY id")
            .param("sagaId", sagaId)
            .query((rs, rowNum) -> new SagaLogEntry(
                rs.getString("step"),
                rs.getString("action"),
                fromJson(rs.getString("result"))
            ))
            .list();
    }

    public void resumeRunningSagas() {
        List<String> runningIds = jdbc.sql("SELECT id FROM sagas WHERE status = 'RUNNING'")
            .query((rs, rowNum) -> rs.getString("id"))
            .list();
        for (String id : runningIds) {
            log.info("Resuming saga {}", id);
            advance(id);
        }
    }

    /**
     * Advance the saga forward. Executes steps within a transaction using FOR UPDATE
     * to lock the saga row. On success, increments step_index and recurses. On failure,
     * marks COMPENSATING and runs compensation.
     */
    private void advance(String sagaId) {
        String[] statusHolder = new String[1];

        txTemplate.executeWithoutResult(status -> {
            var row = jdbc.sql("SELECT id, status, step_index, context FROM sagas WHERE id = :id FOR UPDATE")
                .param("id", sagaId)
                .query((rs, rowNum) -> new Object[]{
                    rs.getString("status"),
                    rs.getInt("step_index"),
                    rs.getString("context")
                })
                .optional()
                .orElse(null);

            if (row == null || !"RUNNING".equals(row[0])) {
                statusHolder[0] = row == null ? "NOT_FOUND" : (String) row[0];
                return;
            }

            int stepIndex = (int) row[1];
            Map<String, Object> context = fromJson((String) row[2]);

            if (stepIndex >= STEPS.size()) {
                jdbc.sql("UPDATE sagas SET status = 'COMPLETED', updated_at = now() WHERE id = :id")
                    .param("id", sagaId)
                    .update();
                statusHolder[0] = "COMPLETED";
                return;
            }

            SagaStep step = STEPS.get(stepIndex);
            try {
                Map<String, Object> result = stepExecutor.execute(step.name(), context);
                context.put(step.name(), result);

                jdbc.sql("INSERT INTO saga_log (saga_id, step, action, result) VALUES (:sagaId, :step, 'execute', :result::jsonb)")
                    .param("sagaId", sagaId)
                    .param("step", step.name())
                    .param("result", toJson(result))
                    .update();

                jdbc.sql("UPDATE sagas SET step_index = :stepIndex, context = :context::jsonb, updated_at = now() WHERE id = :id")
                    .param("stepIndex", stepIndex + 1)
                    .param("context", toJson(context))
                    .param("id", sagaId)
                    .update();

                statusHolder[0] = "RUNNING";
            } catch (Exception e) {
                log.error("Step {} failed: {} -- starting compensation", step.name(), e.getMessage());

                jdbc.sql("INSERT INTO saga_log (saga_id, step, action, result) VALUES (:sagaId, :step, 'failed', :result::jsonb)")
                    .param("sagaId", sagaId)
                    .param("step", step.name())
                    .param("result", toJson(Map.of("error", e.getMessage())))
                    .update();

                jdbc.sql("UPDATE sagas SET status = 'COMPENSATING', updated_at = now() WHERE id = :id")
                    .param("id", sagaId)
                    .update();

                statusHolder[0] = "COMPENSATING";
            }
        });

        if ("RUNNING".equals(statusHolder[0])) {
            advance(sagaId);
        } else if ("COMPENSATING".equals(statusHolder[0])) {
            compensate(sagaId);
        }
    }

    /**
     * Compensate completed steps in reverse order. Iterates from step_index-1 down to 0,
     * executing each step's compensate action.
     */
    private void compensate(String sagaId) {
        var row = jdbc.sql("SELECT step_index, context FROM sagas WHERE id = :id")
            .param("id", sagaId)
            .query((rs, rowNum) -> new Object[]{
                rs.getInt("step_index"),
                rs.getString("context")
            })
            .single();

        int stepIndex = (int) row[0];
        Map<String, Object> context = fromJson((String) row[1]);

        for (int i = stepIndex - 1; i >= 0; i--) {
            SagaStep step = STEPS.get(i);
            String compName = step.compensate();
            Map<String, Object> result = stepExecutor.execute(compName, context);

            jdbc.sql("INSERT INTO saga_log (saga_id, step, action, result) VALUES (:sagaId, :step, 'compensate', :result::jsonb)")
                .param("sagaId", sagaId)
                .param("step", compName)
                .param("result", toJson(result))
                .update();
        }

        jdbc.sql("UPDATE sagas SET status = 'COMPENSATED', updated_at = now() WHERE id = :id")
            .param("id", sagaId)
            .update();

        log.info("Saga {} fully compensated", sagaId);
    }

    private String toJson(Object obj) {
        try {
            return mapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to serialize to JSON", e);
        }
    }

    private Map<String, Object> fromJson(String json) {
        if (json == null || json.isEmpty()) {
            return new HashMap<>();
        }
        try {
            return mapper.readValue(json, MAP_TYPE);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to parse JSON", e);
        }
    }
}
