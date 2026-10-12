package com.cndp.order;

/** Order as returned by the REST API. */
public record OrderView(String id, String sku, int quantity, String status) {
}
