package com.cndp.order;

import com.fasterxml.jackson.annotation.JsonProperty;

/** Body of the order.placed outbox row; Debezium relays it unchanged to Kafka. */
public record OrderPlacedPayload(@JsonProperty("order_id") String orderId, String sku, int quantity, String status) {}
