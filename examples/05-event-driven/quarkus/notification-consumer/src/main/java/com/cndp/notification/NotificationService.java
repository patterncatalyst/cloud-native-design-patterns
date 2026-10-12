package com.cndp.notification;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.transaction.Transactional;

@ApplicationScoped
public class NotificationService {

    /** Returns false when the order was already recorded. Flushes so a constraint violation surfaces here. */
    @Transactional
    public boolean record(String orderId) {
        if (NotificationEntity.count("orderId", orderId) > 0) {
            return false;
        }
        var row = new NotificationEntity();
        row.orderId = orderId;
        row.channel = "email";
        row.persistAndFlush();
        return true;
    }
}
