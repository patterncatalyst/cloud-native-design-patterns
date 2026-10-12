package com.example.stub;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/** The name this stub reports as the {@code source} of its responses. */
@ConfigurationProperties("service")
public record ServiceProperties(@DefaultValue("unknown") String name) {
}
