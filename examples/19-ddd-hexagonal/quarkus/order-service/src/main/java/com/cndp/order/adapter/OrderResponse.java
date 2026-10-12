package com.cndp.order.adapter;

import com.cndp.order.domain.Order;

public record OrderResponse(String id, String sku, int quantity, String status) {

    static OrderResponse of(Order order) {
        return new OrderResponse(order.id(), order.sku(), order.quantity(), order.status());
    }
}
