package com.cndp.order;

import java.util.List;

import io.quarkus.panache.common.Sort;
import org.eclipse.microprofile.graphql.GraphQLApi;
import org.eclipse.microprofile.graphql.Name;
import org.eclipse.microprofile.graphql.Query;

import jakarta.transaction.Transactional;

@GraphQLApi
public class OrderGraphql {

    @Query("orders")
    @Transactional
    public List<Order> orders(@Name("limit") int limit) {
        return OrderEntity.<OrderEntity>findAll(Sort.by("id")).page(0, limit).list()
                .stream().map(OrderEntity::toDto).toList();
    }

    @Query("order")
    @Transactional
    public Order order(@Name("id") String id) {
        OrderEntity entity = OrderEntity.findById(id);
        return entity == null ? null : entity.toDto();
    }
}
