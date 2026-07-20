package com.cndp.saga.service;

import com.cndp.saga.model.Saga;
import com.cndp.saga.model.SagaLogEntry;
import com.cndp.saga.model.SagaRequest;
import com.cndp.saga.model.SagaStep;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.agroal.api.AgroalDataSource;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.jboss.logging.Logger;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.*;

@ApplicationScoped
public class SagaService {
    private static final Logger LOG = Logger.getLogger(SagaService.class);

    private static final List<SagaStep> STEPS = List.of(
        new SagaStep("charge_payment", "refund_payment"),
        new SagaStep("reserve_stock", "release_stock"),
        new SagaStep("book_shipping", "cancel_shipping")
    );

    @Inject
    AgroalDataSource dataSource;

    @Inject
    ObjectMapper objectMapper;

    @Inject
    StepExecutor stepExecutor;

    public Saga createAndRun(SagaRequest request) throws Exception {
        String sagaId = UUID.randomUUID().toString();

        Map<String, Object> context = new HashMap<>();
        context.put("order_id", request.orderId());
        context.put("sku", request.sku());
        context.put("total", request.total());
        if (request.failShipping() != null) {
            context.put("fail_shipping", request.failShipping());
        }

        String contextJson = objectMapper.writeValueAsString(context);

        try (Connection conn = dataSource.getConnection();
             PreparedStatement ps = conn.prepareStatement(
                 "INSERT INTO sagas (id, status, step_index, context) VALUES (?, 'RUNNING', 0, ?::jsonb)")) {
            ps.setString(1, sagaId);
            ps.setString(2, contextJson);
            ps.executeUpdate();
        }

        LOG.infof("Created saga: %s", sagaId);
        advance(sagaId);
        return getSaga(sagaId);
    }

    public Saga getSaga(String id) throws Exception {
        try (Connection conn = dataSource.getConnection();
             PreparedStatement ps = conn.prepareStatement(
                 "SELECT id, status, step_index, context FROM sagas WHERE id = ?")) {
            ps.setString(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    String contextJson = rs.getString("context");
                    Map<String, Object> context = objectMapper.readValue(
                        contextJson, new TypeReference<Map<String, Object>>() {});
                    return new Saga(
                        rs.getString("id"),
                        rs.getString("status"),
                        rs.getInt("step_index"),
                        context
                    );
                }
            }
        }
        return null;
    }

    public List<SagaLogEntry> getSagaLog(String id) throws Exception {
        List<SagaLogEntry> entries = new ArrayList<>();
        try (Connection conn = dataSource.getConnection();
             PreparedStatement ps = conn.prepareStatement(
                 "SELECT step, action, result FROM saga_log WHERE saga_id = ? ORDER BY id")) {
            ps.setString(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    String resultJson = rs.getString("result");
                    Map<String, Object> result = resultJson != null
                        ? objectMapper.readValue(resultJson, new TypeReference<Map<String, Object>>() {})
                        : null;
                    entries.add(new SagaLogEntry(
                        rs.getString("step"),
                        rs.getString("action"),
                        result
                    ));
                }
            }
        }
        return entries;
    }

    public void resumeRunningSagas() {
        try (Connection conn = dataSource.getConnection();
             PreparedStatement ps = conn.prepareStatement(
                 "SELECT id FROM sagas WHERE status = 'RUNNING'");
             ResultSet rs = ps.executeQuery()) {
            List<String> runningIds = new ArrayList<>();
            while (rs.next()) {
                runningIds.add(rs.getString("id"));
            }
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

    public void advance(String sagaId) throws Exception {
        Connection conn = null;
        try {
            conn = dataSource.getConnection();
            conn.setAutoCommit(false);

            // Lock the saga row
            Saga saga;
            try (PreparedStatement ps = conn.prepareStatement(
                    "SELECT id, status, step_index, context FROM sagas WHERE id = ? FOR UPDATE")) {
                ps.setString(1, sagaId);
                try (ResultSet rs = ps.executeQuery()) {
                    if (!rs.next()) {
                        conn.rollback();
                        return;
                    }
                    String contextJson = rs.getString("context");
                    Map<String, Object> context = objectMapper.readValue(
                        contextJson, new TypeReference<Map<String, Object>>() {});
                    saga = new Saga(
                        rs.getString("id"),
                        rs.getString("status"),
                        rs.getInt("step_index"),
                        context
                    );
                }
            }

            // If all steps completed, mark as COMPLETED
            if (saga.stepIndex() >= STEPS.size()) {
                try (PreparedStatement ps = conn.prepareStatement(
                        "UPDATE sagas SET status = 'COMPLETED', updated_at = now() WHERE id = ?")) {
                    ps.setString(1, sagaId);
                    ps.executeUpdate();
                }
                conn.commit();
                LOG.infof("Saga completed: %s", sagaId);
                return;
            }

            SagaStep step = STEPS.get(saga.stepIndex());
            Map<String, Object> context = new HashMap<>(saga.context());

            try {
                // Execute the step
                Map<String, Object> result = stepExecutor.execute(step.name(), context);

                // Log success
                logStep(conn, sagaId, step.name(), "execute", result);

                // Update context and advance
                context.put(step.name(), result);
                String contextJson = objectMapper.writeValueAsString(context);

                try (PreparedStatement ps = conn.prepareStatement(
                        "UPDATE sagas SET step_index = ?, context = ?::jsonb, updated_at = now() WHERE id = ?")) {
                    ps.setInt(1, saga.stepIndex() + 1);
                    ps.setString(2, contextJson);
                    ps.setString(3, sagaId);
                    ps.executeUpdate();
                }

                conn.commit();

                // Recurse to next step
                advance(sagaId);

            } catch (Exception e) {
                // Log failure
                logStep(conn, sagaId, step.name(), "failed", Map.of("error", e.getMessage()));

                // Mark as COMPENSATING
                try (PreparedStatement ps = conn.prepareStatement(
                        "UPDATE sagas SET status = 'COMPENSATING', updated_at = now() WHERE id = ?")) {
                    ps.setString(1, sagaId);
                    ps.executeUpdate();
                }

                conn.commit();

                // Start compensation
                compensate(sagaId);
            }

        } finally {
            if (conn != null) {
                try {
                    conn.close();
                } catch (SQLException e) {
                    LOG.error("Failed to close connection", e);
                }
            }
        }
    }

    public void compensate(String sagaId) throws Exception {
        Saga saga = getSaga(sagaId);
        if (saga == null) {
            return;
        }

        Map<String, Object> context = saga.context();

        // Compensate in reverse order, only for completed steps
        for (int i = saga.stepIndex() - 1; i >= 0; i--) {
            SagaStep step = STEPS.get(i);
            try {
                Map<String, Object> result = stepExecutor.execute(step.compensate(), context);
                logStepDirect(sagaId, step.compensate(), "compensate", result);
            } catch (Exception e) {
                LOG.errorf(e, "Compensation failed for step: %s", step.compensate());
                logStepDirect(sagaId, step.compensate(), "failed", Map.of("error", e.getMessage()));
            }
        }

        // Mark as COMPENSATED
        try (Connection conn = dataSource.getConnection();
             PreparedStatement ps = conn.prepareStatement(
                 "UPDATE sagas SET status = 'COMPENSATED', updated_at = now() WHERE id = ?")) {
            ps.setString(1, sagaId);
            ps.executeUpdate();
        }

        LOG.infof("Saga compensated: %s", sagaId);
    }

    private void logStep(Connection conn, String sagaId, String step, String action, Map<String, Object> result) throws Exception {
        String resultJson = result != null ? objectMapper.writeValueAsString(result) : null;
        try (PreparedStatement ps = conn.prepareStatement(
                "INSERT INTO saga_log (saga_id, step, action, result) VALUES (?, ?, ?, ?::jsonb)")) {
            ps.setString(1, sagaId);
            ps.setString(2, step);
            ps.setString(3, action);
            ps.setString(4, resultJson);
            ps.executeUpdate();
        }
    }

    private void logStepDirect(String sagaId, String step, String action, Map<String, Object> result) throws Exception {
        String resultJson = result != null ? objectMapper.writeValueAsString(result) : null;
        try (Connection conn = dataSource.getConnection();
             PreparedStatement ps = conn.prepareStatement(
                 "INSERT INTO saga_log (saga_id, step, action, result) VALUES (?, ?, ?, ?::jsonb)")) {
            ps.setString(1, sagaId);
            ps.setString(2, step);
            ps.setString(3, action);
            ps.setString(4, resultJson);
            ps.executeUpdate();
        }
    }
}
