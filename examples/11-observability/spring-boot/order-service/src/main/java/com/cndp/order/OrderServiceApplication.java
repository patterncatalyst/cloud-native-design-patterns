package com.cndp.order;

import com.cndp.proto.InventoryServiceGrpc;
import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.metrics.LongCounter;
import io.opentelemetry.api.metrics.Meter;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.grpc.client.GrpcChannelFactory;

@SpringBootApplication
public class OrderServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(OrderServiceApplication.class, args);
    }

    // The OpenTelemetry Java agent installs the global instance and instruments the gRPC client.
    @Bean
    public OpenTelemetry openTelemetry() {
        return GlobalOpenTelemetry.get();
    }

    /** The "inventory" channel comes from spring.grpc.client.channel.inventory.target; Spring gRPC owns its lifecycle. */
    @Bean
    InventoryServiceGrpc.InventoryServiceBlockingStub inventoryStub(GrpcChannelFactory channels) {
        return InventoryServiceGrpc.newBlockingStub(channels.createChannel("inventory"));
    }

    @Bean
    public LongCounter ordersPlacedCounter(OpenTelemetry openTelemetry) {
        Meter meter = openTelemetry.getMeter("order-service");
        return meter.counterBuilder("orders.placed")
                .setDescription("Number of orders placed")
                .build();
    }
}
