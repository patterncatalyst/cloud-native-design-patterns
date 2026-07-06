package com.cndp.order.domain;

import java.util.List;
import java.util.Optional;

/**
 * Port — the repository contract the domain depends on.
 * Driven adapters (Postgres, in-memory, etc.) implement this interface.
 */
public interface OrderRepository {

    void save(Order order);

    Optional<Order> findById(String id);

    List<Order> listAll();
}
