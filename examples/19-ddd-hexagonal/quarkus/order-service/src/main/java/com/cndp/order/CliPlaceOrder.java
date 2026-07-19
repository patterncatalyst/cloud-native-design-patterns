package com.cndp.order;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

import com.cndp.order.domain.EventPublisher;
import com.cndp.order.domain.Order;
import com.cndp.order.domain.OrderPlaced;
import com.cndp.order.domain.OrderRepository;
import com.cndp.order.domain.PlaceOrderCmd;
import com.cndp.order.domain.PlaceOrderUseCase;

public class CliPlaceOrder {

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("Usage: CliPlaceOrder <sku> <quantity>");
            System.exit(1);
        }

        String sku = args[0];
        int quantity = Integer.parseInt(args[1]);

        String dbUrl = System.getenv("DATABASE_URL");
        if (dbUrl == null || dbUrl.isEmpty()) {
            dbUrl = "postgres://appuser:apppass@postgres:5432/appdb";
        }
        String jdbcUrl = dbUrl
                .replaceFirst("^postgres://", "jdbc:postgresql://")
                .replaceFirst("^postgresql://", "jdbc:postgresql://");

        String user = "appuser";
        String password = "apppass";
        if (jdbcUrl.contains("@")) {
            String auth = jdbcUrl.substring(jdbcUrl.indexOf("//") + 2, jdbcUrl.indexOf("@"));
            if (auth.contains(":")) {
                user = auth.substring(0, auth.indexOf(":"));
                password = auth.substring(auth.indexOf(":") + 1);
            }
            jdbcUrl = jdbcUrl.substring(0, jdbcUrl.indexOf("//") + 2)
                    + jdbcUrl.substring(jdbcUrl.indexOf("@") + 1);
        }

        Connection conn = DriverManager.getConnection(jdbcUrl, user, password);

        OrderRepository repo = new JdbcOrderRepository(conn);
        EventPublisher events = new StdoutEventPublisher();
        PlaceOrderUseCase useCase = new PlaceOrderUseCase(repo, events);

        Order order = useCase.execute(new PlaceOrderCmd(sku, quantity));
        System.out.printf("CLI_ORDER_CREATED id=%s sku=%s qty=%d status=%s%n",
                order.id(), order.sku(), order.quantity(), order.status());

        conn.close();
    }

    private static class JdbcOrderRepository implements OrderRepository {
        private final Connection conn;

        JdbcOrderRepository(Connection conn) {
            this.conn = conn;
        }

        @Override
        public void save(Order order) {
            try {
                PreparedStatement ps = conn.prepareStatement(
                        "INSERT INTO orders (id, sku, quantity, status, created_at) VALUES (?, ?, ?, ?, ?)");
                ps.setString(1, order.id());
                ps.setString(2, order.sku());
                ps.setInt(3, order.quantity());
                ps.setString(4, order.status());
                ps.setTimestamp(5, Timestamp.from(order.createdAt()));
                ps.executeUpdate();
                ps.close();
            } catch (Exception e) {
                throw new RuntimeException("save failed", e);
            }
        }

        @Override
        public Optional<Order> findById(String id) {
            try {
                PreparedStatement ps = conn.prepareStatement(
                        "SELECT id, sku, quantity, status, created_at FROM orders WHERE id = ?");
                ps.setString(1, id);
                ResultSet rs = ps.executeQuery();
                if (!rs.next()) {
                    rs.close();
                    ps.close();
                    return Optional.empty();
                }
                Order order = new Order(
                        rs.getString("id"),
                        rs.getString("sku"),
                        rs.getInt("quantity"),
                        rs.getString("status"),
                        rs.getTimestamp("created_at").toInstant()
                );
                rs.close();
                ps.close();
                return Optional.of(order);
            } catch (Exception e) {
                throw new RuntimeException("findById failed", e);
            }
        }

        @Override
        public List<Order> listAll() {
            try {
                PreparedStatement ps = conn.prepareStatement(
                        "SELECT id, sku, quantity, status, created_at FROM orders ORDER BY created_at");
                ResultSet rs = ps.executeQuery();
                List<Order> orders = new java.util.ArrayList<>();
                while (rs.next()) {
                    orders.add(new Order(
                            rs.getString("id"),
                            rs.getString("sku"),
                            rs.getInt("quantity"),
                            rs.getString("status"),
                            rs.getTimestamp("created_at").toInstant()
                    ));
                }
                rs.close();
                ps.close();
                return orders;
            } catch (Exception e) {
                throw new RuntimeException("listAll failed", e);
            }
        }
    }

    private static class StdoutEventPublisher implements EventPublisher {
        @Override
        public void publish(OrderPlaced event) {
            System.out.printf("EVENT OrderPlaced order_id=%s sku=%s%n",
                    event.orderId(), event.sku());
        }
    }
}
