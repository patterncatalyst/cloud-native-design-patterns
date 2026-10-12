package com.cndp.order;

import java.math.BigDecimal;

public record OrderDto(int id, String customer, BigDecimal total) {

    static OrderDto of(Order order) {
        return new OrderDto(order.id, order.customer, order.total);
    }
}
