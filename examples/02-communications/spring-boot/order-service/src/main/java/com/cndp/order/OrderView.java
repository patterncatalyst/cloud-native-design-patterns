package com.cndp.order;

/** Order as returned by the REST API, the GraphQL schema and the order.placed event. */
public record OrderView(String id, String sku, int quantity, String status) {
}
