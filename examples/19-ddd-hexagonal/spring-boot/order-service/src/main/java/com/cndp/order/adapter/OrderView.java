package com.cndp.order.adapter;

import com.cndp.order.domain.Order;

/** Order as returned by the REST adapter. */
record OrderView(String id, String sku, int quantity, String status) {

    static OrderView of(Order o) {
        return new OrderView(o.id(), o.sku(), o.quantity(), o.status());
    }
}
