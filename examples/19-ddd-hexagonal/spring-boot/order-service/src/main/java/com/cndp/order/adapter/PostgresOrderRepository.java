package com.cndp.order.adapter;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import com.cndp.order.domain.Order;
import com.cndp.order.domain.OrderRepository;

/**
 * Driven adapter — persists Orders in Postgres via Spring's JdbcClient.
 */
@Repository
public class PostgresOrderRepository implements OrderRepository {

    private final JdbcClient jdbc;

    public PostgresOrderRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public void save(Order order) {
        jdbc.sql("INSERT INTO orders (id, sku, quantity, status, created_at) VALUES (?, ?, ?, ?, ?)")
                .param(order.id())
                .param(order.sku())
                .param(order.quantity())
                .param(order.status())
                .param(java.sql.Timestamp.from(order.createdAt()))
                .update();
    }

    @Override
    public Optional<Order> findById(String id) {
        return jdbc.sql("SELECT id, sku, quantity, status, created_at FROM orders WHERE id = ?")
                .param(id)
                .query((rs, rowNum) -> new Order(
                        rs.getString("id"),
                        rs.getString("sku"),
                        rs.getInt("quantity"),
                        rs.getString("status"),
                        rs.getTimestamp("created_at").toInstant()
                ))
                .optional();
    }

    @Override
    public List<Order> listAll() {
        return jdbc.sql("SELECT id, sku, quantity, status, created_at FROM orders ORDER BY created_at")
                .query((rs, rowNum) -> new Order(
                        rs.getString("id"),
                        rs.getString("sku"),
                        rs.getInt("quantity"),
                        rs.getString("status"),
                        rs.getTimestamp("created_at").toInstant()
                ))
                .list();
    }
}
