package com.cndp.order.adapter;

import java.util.List;
import java.util.Optional;

import io.quarkus.panache.common.Sort;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.transaction.Transactional;

import com.cndp.order.domain.Order;
import com.cndp.order.domain.OrderRepository;

@ApplicationScoped
@Transactional
public class PostgresOrderRepository implements OrderRepository {

    @Override
    public void save(Order order) {
        OrderEntity.from(order).persist();
    }

    @Override
    public Optional<Order> findById(String id) {
        return OrderEntity.<OrderEntity>findByIdOptional(id).map(OrderEntity::toDomain);
    }

    @Override
    public List<Order> listAll() {
        return OrderEntity.<OrderEntity>listAll(Sort.by("createdAt"))
                .stream().map(OrderEntity::toDomain).toList();
    }
}
