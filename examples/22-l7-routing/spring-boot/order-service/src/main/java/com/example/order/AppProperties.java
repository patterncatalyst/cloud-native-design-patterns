package com.example.order;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/** The version label this replica reports; the Envoy route weights pick between v1 and v2. */
@ConfigurationProperties("app")
public record AppProperties(@DefaultValue("v1") String version) {
}
