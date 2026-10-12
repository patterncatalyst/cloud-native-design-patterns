package com.cndp.order;

/** Kafka payload for order.placed: {"id","sku","quantity","status"}, serialized by the Jackson serializer. */
public record OrderPlaced(String id, String sku, int quantity, String status) {}
