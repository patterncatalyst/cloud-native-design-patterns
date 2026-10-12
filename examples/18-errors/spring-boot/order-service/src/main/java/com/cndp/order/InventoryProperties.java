package com.cndp.order;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/** Where the inventory gRPC service is and how long a reservation may take. */
@ConfigurationProperties("inventory")
public record InventoryProperties(
        @DefaultValue("inventory:50051") String addr,
        @DefaultValue("3000") long deadlineMs) {
}
