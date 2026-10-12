package com.cndp.inventory;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

@ConfigurationProperties("inventory")
public record InventoryProperties(
        @DefaultValue("10") int initialStock,
        @DefaultValue("none") String failMode) {
}
