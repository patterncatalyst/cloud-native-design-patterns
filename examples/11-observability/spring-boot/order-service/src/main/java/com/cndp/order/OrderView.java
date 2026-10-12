package com.cndp.order;

/** Order as returned by POST /orders and published as the order.placed event. */
public record OrderView(String id, String sku, int quantity, String status) {
}
