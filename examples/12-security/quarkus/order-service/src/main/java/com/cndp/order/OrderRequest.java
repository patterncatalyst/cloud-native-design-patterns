package com.cndp.order;

public record OrderRequest(String sku, int quantity, String tenant) {
}
