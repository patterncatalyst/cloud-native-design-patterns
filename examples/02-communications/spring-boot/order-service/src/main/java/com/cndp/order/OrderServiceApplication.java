package com.cndp.order;

import com.cndp.proto.InventoryGrpc;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
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

    @Bean
    public InventoryGrpc.InventoryBlockingStub inventoryStub() {
        String[] parts = inventoryAddr.split(":");
        channel = ManagedChannelBuilder.forAddress(parts[0], Integer.parseInt(parts[1]))
                .usePlaintext()
                .build();
        return InventoryGrpc.newBlockingStub(channel);
    }

    @PreDestroy
    public void shutdownChannel() {
        if (channel != null) channel.shutdown();
    }
}
