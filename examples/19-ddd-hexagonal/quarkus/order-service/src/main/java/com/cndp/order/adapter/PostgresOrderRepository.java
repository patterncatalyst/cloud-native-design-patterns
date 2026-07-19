package com.cndp.order.adapter;

import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import javax.sql.DataSource;

import io.quarkus.logging.Log;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import com.cndp.order.domain.Order;
import com.cndp.order.domain.OrderRepository;

@ApplicationScoped
public class PostgresOrderRepository implements OrderRepository {

    @Inject
    DataSource dataSource;

    @Override
    public void save(Order order) {
        try (var conn = dataSource.getConnection();
             var ps = conn.prepareStatement(
                     "INSERT INTO orders (id, sku, quantity, status, created_at) VALUES (?, ?, ?, ?, ?)")) {
            ps.setString(1, order.id());
            ps.setString(2, order.sku());
            ps.setInt(3, order.quantity());
            ps.setString(4, order.status());
            ps.setTimestamp(5, Timestamp.from(order.createdAt()));
            ps.executeUpdate();
        } catch (Exception e) {
            throw new RuntimeException("save failed", e);
        }
    }

    @Override
    public Optional<Order> findById(String id) {
        try (var conn = dataSource.getConnection();
             var ps = conn.prepareStatement(
                     "SELECT id, sku, quantity, status, created_at FROM orders WHERE id = ?")) {
            ps.setString(1, id);
            try (var rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return Optional.empty();
                }
                return Optional.of(new Order(
                        rs.getString("id"),
                        rs.getString("sku"),
                        rs.getInt("quantity"),
                        rs.getString("status"),
                        rs.getTimestamp("created_at").toInstant()
                ));
            }
        } catch (Exception e) {
            throw new RuntimeException("findById failed", e);
        }
    }

    @Override
    public List<Order> listAll() {
        try (var conn = dataSource.getConnection();
             var ps = conn.prepareStatement(
                     "SELECT id, sku, quantity, status, created_at FROM orders ORDER BY created_at")) {
            try (var rs = ps.executeQuery()) {
                var orders = new ArrayList<Order>();
                while (rs.next()) {
                    orders.add(new Order(
                            rs.getString("id"),
                            rs.getString("sku"),
                            rs.getInt("quantity"),
                            rs.getString("status"),
                            rs.getTimestamp("created_at").toInstant()
                    ));
                }
                return orders;
            }
        } catch (Exception e) {
            throw new RuntimeException("listAll failed", e);
        }
    }
}
