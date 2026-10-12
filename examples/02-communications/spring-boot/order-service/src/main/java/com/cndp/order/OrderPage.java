package com.cndp.order;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonProperty;

/** Keyset page: {@code next_cursor} is null on the last page. */
public record OrderPage(List<OrderView> items, @JsonProperty("next_cursor") String nextCursor) {
}
