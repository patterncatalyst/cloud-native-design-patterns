package com.cndp.order;

import com.cndp.proto.InventoryServiceGrpc;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.metrics.LongCounter;
import io.opentelemetry.api.metrics.Meter;
import jakarta.annotation.PreDestroy;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class OrderServiceApplication {

    @Value("${inventory.addr}")
    private String inventoryAddr;

    private ManagedChannel channel;

    public static void main(String[] args) {
        SpringApplication.run(OrderServiceApplication.class, args);
    }

    // The OpenTelemetry Java agent installs the global instance and instruments the gRPC client.
    @Bean
    public OpenTelemetry openTelemetry() {
        return GlobalOpenTelemetry.get();
    }

    @Bean
    public InventoryServiceGrpc.InventoryServiceBlockingStub inventoryStub() {
        String[] parts = inventoryAddr.split(":");
        channel = ManagedChannelBuilder.forAddress(parts[0], Integer.parseInt(parts[1]))
                .usePlaintext()
                .build();
        return InventoryServiceGrpc.newBlockingStub(channel);
    }

    @Bean
    public LongCounter ordersPlacedCounter(OpenTelemetry openTelemetry) {
        Meter meter = openTelemetry.getMeter("order-service");
        return meter.counterBuilder("orders.placed")
                .setDescription("Number of orders placed")
                .build();
    }

    @PreDestroy
    public void shutdownChannel() {
        if (channel != null) channel.shutdown();
    }
}
