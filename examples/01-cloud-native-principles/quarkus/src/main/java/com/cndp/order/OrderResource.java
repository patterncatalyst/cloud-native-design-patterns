package com.cndp.order;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import javax.sql.DataSource;

import io.quarkus.logging.Log;
import jakarta.inject.Inject;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

import org.jboss.resteasy.reactive.RestQuery;

@Path("/orders")
@Produces(MediaType.APPLICATION_JSON)
public class OrderResource {

    @Inject
    DataSource dataSource;

    @GET
    public List<Map<String, Object>> listOrders() throws Exception {
        var rows = new ArrayList<Map<String, Object>>();
        try (var conn = dataSource.getConnection();
             var stmt = conn.createStatement();
             var rs = stmt.executeQuery("SELECT id, customer, total FROM orders ORDER BY id")) {
            while (rs.next()) {
                var row = new LinkedHashMap<String, Object>();
                row.put("id", rs.getInt("id"));
                row.put("customer", rs.getString("customer"));
                row.put("total", rs.getBigDecimal("total"));
                rows.add(row);
            }
        }
        return rows;
    }

    @POST
    public Map<String, Object> createOrder(@RestQuery String customer,
                                           @RestQuery BigDecimal total) throws Exception {
        var row = new LinkedHashMap<String, Object>();
        try (var conn = dataSource.getConnection();
             var stmt = conn.prepareStatement(
                     "INSERT INTO orders (customer, total) VALUES (?, ?) RETURNING id, customer, total")) {
            stmt.setString(1, customer);
            stmt.setBigDecimal(2, total);
            try (var rs = stmt.executeQuery()) {
                rs.next();
                row.put("id", rs.getInt("id"));
                row.put("customer", rs.getString("customer"));
                row.put("total", rs.getBigDecimal("total"));
            }
        }
        Log.infof("order_created id=%s customer=%s total=%s", row.get("id"), customer, total);
        return row;
    }
}
