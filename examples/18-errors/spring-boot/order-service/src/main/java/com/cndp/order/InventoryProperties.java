package com.cndp.order;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/** How long a reservation may take; the channel itself is spring.grpc.client.channel.inventory. */
@ConfigurationProperties("inventory")
public record InventoryProperties(@DefaultValue("3000") long deadlineMs) {
}
