package com.cndp.notification;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.agroal.api.AgroalDataSource;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.reactive.messaging.Incoming;
import org.jboss.logging.Logger;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;

@ApplicationScoped
public class NotificationListener {

    private static final Logger log = Logger.getLogger(NotificationListener.class);

    @Inject
    AgroalDataSource dataSource;

    @Inject
    ObjectMapper objectMapper;

    @Incoming("order-placed")
    public void onOrderPlaced(String message) {
        try {
            JsonNode event = objectMapper.readTree(message);
            String orderId = event.get("id").asText();
            log.infof("Received order.placed: orderId=%s", orderId);

            try (Connection conn = dataSource.getConnection();
                 PreparedStatement ps = conn.prepareStatement(
                     "INSERT INTO notifications (order_id, channel) VALUES (?, 'email')")) {
                ps.setString(1, orderId);
                ps.executeUpdate();
                log.infof("Notification recorded for orderId=%s", orderId);
            }
        } catch (SQLException e) {
            if (e.getSQLState() != null && e.getSQLState().equals("23505")) {
                log.infof("Duplicate notification, skipping (idempotent)");
            } else {
                throw new RuntimeException(e);
            }
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
