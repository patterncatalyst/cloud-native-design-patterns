package com.cndp.order;

/** Response of POST /orders and the order.placed Kafka payload: {"id","sku","quantity","status"}. */
public record Order(String id, String sku, int quantity, String status) {}
