package com.cndp.order;

import io.agroal.api.AgroalDataSource;
import jakarta.inject.Inject;
import org.eclipse.microprofile.graphql.GraphQLApi;
import org.eclipse.microprofile.graphql.Name;
import org.eclipse.microprofile.graphql.Query;
import org.jboss.logging.Logger;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

@GraphQLApi
public class OrderGraphql {

    private static final Logger LOG = Logger.getLogger(OrderGraphql.class);

    @Inject
    AgroalDataSource dataSource;

    @Query("orders")
    public List<Order> orders(@Name("limit") int limit) {
        List<Order> orders = new ArrayList<>();
        String sql = "SELECT id, sku, quantity, status FROM orders ORDER BY id LIMIT ?";

        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            stmt.setInt(1, limit);

            try (ResultSet rs = stmt.executeQuery()) {
                while (rs.next()) {
                    orders.add(new Order(
                            rs.getString("id"),
                            rs.getString("sku"),
                            rs.getInt("quantity"),
                            rs.getString("status")
                    ));
                }
            }
        } catch (SQLException e) {
            LOG.error("Error querying orders", e);
            throw new RuntimeException("Error querying orders", e);
        }

        return orders;
    }

    @Query("order")
    public Order order(@Name("id") String id) {
        String sql = "SELECT id, sku, quantity, status FROM orders WHERE id = ?";

        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            stmt.setString(1, id);

            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    return new Order(
                            rs.getString("id"),
                            rs.getString("sku"),
                            rs.getInt("quantity"),
                            rs.getString("status")
                    );
                }
            }
        } catch (SQLException e) {
            LOG.error("Error querying order", e);
            throw new RuntimeException("Error querying order", e);
        }

        return null;
    }
}
