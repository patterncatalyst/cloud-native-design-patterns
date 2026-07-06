package com.cndp.order;

import java.util.List;
import java.util.Map;

import org.springframework.graphql.data.method.annotation.Argument;
import org.springframework.graphql.data.method.annotation.QueryMapping;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Controller;

@Controller
public class OrderGraphqlController {

    private final JdbcClient jdbc;

    public OrderGraphqlController(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @QueryMapping
    public List<Map<String, Object>> orders(@Argument int limit) {
        return jdbc.sql("SELECT id, sku, quantity, status FROM orders ORDER BY id LIMIT ?")
                .param(limit)
                .query().listOfRows();
    }

    @QueryMapping
    public Map<String, Object> order(@Argument String id) {
        var rows = jdbc.sql("SELECT id, sku, quantity, status FROM orders WHERE id = ?")
                .param(id)
                .query().listOfRows();
        return rows.isEmpty() ? null : rows.getFirst();
    }
}
