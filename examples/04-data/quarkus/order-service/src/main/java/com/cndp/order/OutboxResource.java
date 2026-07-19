package com.cndp.order;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.agroal.api.AgroalDataSource;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;

import java.sql.*;
import java.util.*;

@Path("/outbox")
@Produces(MediaType.APPLICATION_JSON)
public class OutboxResource {

    @Inject
    AgroalDataSource dataSource;

    @Inject
    ObjectMapper objectMapper;

    public static class OutboxEvent {
        public long id;
        public String aggregate_id;
        public String event_type;
        public Map<String, Object> payload;
        public String created_at;
    }

    @GET
    @SuppressWarnings("unchecked")
    public List<OutboxEvent> listOutbox() throws Exception {
        List<OutboxEvent> events = new ArrayList<>();

        try (Connection conn = dataSource.getConnection();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT id, aggregate_id, event_type, payload, created_at FROM outbox ORDER BY created_at DESC")) {

            while (rs.next()) {
                OutboxEvent event = new OutboxEvent();
                event.id = rs.getLong("id");
                event.aggregate_id = rs.getString("aggregate_id");
                event.event_type = rs.getString("event_type");
                event.payload = objectMapper.readValue(rs.getString("payload"), Map.class);
                event.created_at = rs.getString("created_at");
                events.add(event);
            }
        }

        return events;
    }
}
