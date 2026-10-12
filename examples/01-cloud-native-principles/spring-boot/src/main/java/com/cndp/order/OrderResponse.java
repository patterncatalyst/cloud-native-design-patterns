package com.cndp.order;

import java.math.BigDecimal;

public record OrderResponse(int id, String customer, BigDecimal total) {

    static OrderResponse of(Order order) {
        return new OrderResponse(order.getId(), order.getCustomer(), order.getTotal());
    }
}
