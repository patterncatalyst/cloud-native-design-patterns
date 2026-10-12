package com.cndp.order;

import org.springframework.boot.Banner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;

/**
 * CLI driving adapter entry point: the same application with no web server and the {@code cli}
 * profile, which activates {@link PlaceOrderRunner}. It reuses the JPA repository adapter.
 */
public class CliPlaceOrder {

    public static void main(String[] args) {
        var context = new SpringApplicationBuilder(OrderServiceApplication.class)
                .web(WebApplicationType.NONE)
                .bannerMode(Banner.Mode.OFF)
                .profiles("cli")
                .run(args);
        System.exit(SpringApplication.exit(context));
    }
}
