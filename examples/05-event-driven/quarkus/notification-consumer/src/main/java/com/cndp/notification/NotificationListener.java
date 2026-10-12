package com.cndp.notification;

import io.quarkus.logging.Log;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.persistence.PersistenceException;
import org.eclipse.microprofile.reactive.messaging.Incoming;
import org.hibernate.exception.ConstraintViolationException;

@ApplicationScoped
public class NotificationListener {

    private static final String UNIQUE_VIOLATION = "23505";

    private final NotificationService service;

    NotificationListener(NotificationService service) {
        this.service = service;
    }

    /**
     * Idempotent consumer: the service checks for the order first, and the UNIQUE (order_id)
     * constraint is the backstop when two deliveries race. The transaction lives in the service,
     * so a rolled-back duplicate is handled here and the offset still commits.
     */
    @Incoming("order-placed")
    public void onOrderPlaced(OrderPlaced event) {
        Log.infof("Received order.placed: orderId=%s", event.id());
        try {
            if (service.record(event.id())) {
                Log.infof("Notification recorded for orderId=%s", event.id());
            } else {
                Log.info("Duplicate notification, skipping (idempotent)");
            }
        } catch (PersistenceException e) {
            if (e instanceof ConstraintViolationException cve && UNIQUE_VIOLATION.equals(cve.getSQLState())) {
                Log.info("Duplicate notification, skipping (idempotent)");
            } else {
                throw e;
            }
        }
    }
}
