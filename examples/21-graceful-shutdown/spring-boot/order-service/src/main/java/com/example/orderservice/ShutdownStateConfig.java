package com.example.orderservice;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Exposes the ShutdownState singleton as a Spring bean so it can be injected
 * into controllers and other components.
 */
@Configuration
public class ShutdownStateConfig {

    @Bean
    public ShutdownState shutdownState() {
        return ShutdownState.getInstance();
    }
}
