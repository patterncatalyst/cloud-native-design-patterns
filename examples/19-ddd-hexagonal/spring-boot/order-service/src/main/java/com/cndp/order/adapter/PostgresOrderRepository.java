package com.cndp.order.adapter;

import java.util.List;
import java.util.Optional;

import org.springframework.stereotype.Repository;

import com.cndp.order.domain.Order;
import com.cndp.order.domain.OrderRepository;

/**
 * Driven adapter — implements the domain's {@link OrderRepository} port on Spring Data JPA.
 */
@Repository
public class PostgresOrderRepository implements OrderRepository {

    private final OrderJpaRepository jpa;

    public PostgresOrderRepository(OrderJpaRepository jpa) {
        this.jpa = jpa;
    }

    @Override
    public void save(Order order) {
        jpa.save(new OrderJpaEntity(order));
    }

    @Override
    public Optional<Order> findById(String id) {
        return jpa.findById(id).map(OrderJpaEntity::toDomain);
    }

    @Override
    public List<Order> listAll() {
        return jpa.findAllByOrderByCreatedAtAsc().stream().map(OrderJpaEntity::toDomain).toList();
    }
}
