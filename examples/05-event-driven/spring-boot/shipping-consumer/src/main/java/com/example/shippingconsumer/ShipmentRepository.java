package com.example.shippingconsumer;

import org.springframework.data.jpa.repository.JpaRepository;

public interface ShipmentRepository extends JpaRepository<Shipment, Long> {

    boolean existsByOrderId(String orderId);
}
