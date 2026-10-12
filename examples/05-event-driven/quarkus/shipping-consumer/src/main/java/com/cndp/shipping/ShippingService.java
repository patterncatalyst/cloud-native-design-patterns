package com.cndp.shipping;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.transaction.Transactional;

@ApplicationScoped
public class ShippingService {

    /** Returns false when the order was already recorded. Flushes so a constraint violation surfaces here. */
    @Transactional
    public boolean record(String orderId) {
        if (ShipmentEntity.count("orderId", orderId) > 0) {
            return false;
        }
        var row = new ShipmentEntity();
        row.orderId = orderId;
        row.status = "scheduled";
        row.persistAndFlush();
        return true;
    }
}
