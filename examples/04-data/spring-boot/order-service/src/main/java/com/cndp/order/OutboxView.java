package com.cndp.order;

import java.time.Instant;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonProperty;

/** Outbox row as returned by GET /outbox; the payload is the JSON that Debezium publishes. */
public record OutboxView(
        long id,
        @JsonProperty("aggregate_id") String aggregateId,
        @JsonProperty("event_type") String eventType,
        Map<String, Object> payload,
        @JsonProperty("created_at") Instant createdAt) {
}
