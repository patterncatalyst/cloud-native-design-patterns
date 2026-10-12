package com.cndp.order;

import com.fasterxml.jackson.annotation.JsonProperty;

public record OutboxView(long id,
                         @JsonProperty("aggregate_id") String aggregateId,
                         @JsonProperty("event_type") String eventType,
                         OrderPlacedPayload payload,
                         @JsonProperty("created_at") String createdAt) {}
