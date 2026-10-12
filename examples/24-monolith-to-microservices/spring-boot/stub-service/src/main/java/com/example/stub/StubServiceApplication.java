package com.example.stub;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class StubServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(StubServiceApplication.class, args);
    }
}
