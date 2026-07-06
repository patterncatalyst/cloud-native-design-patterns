package com.cndp.gateway;

import com.cndp.proto.InventoryGrpc;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import jakarta.annotation.PreDestroy;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.web.client.RestClient;

@SpringBootApplication
public class GatewayApplication {

    @Value("${inventory.addr}")
    private String inventoryAddr;

    @Value("${orderapi.url}")
    private String orderApiUrl;

    private ManagedChannel channel;

    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }

    @Bean
    public InventoryGrpc.InventoryBlockingStub inventoryStub() {
        String[] parts = inventoryAddr.split(":");
        channel = ManagedChannelBuilder.forAddress(parts[0], Integer.parseInt(parts[1]))
                .usePlaintext()
                .build();
        return InventoryGrpc.newBlockingStub(channel);
    }

    @Bean
    public RestClient orderApiClient() {
        return RestClient.builder()
                .baseUrl(orderApiUrl)
                .build();
    }

    @PreDestroy
    public void shutdownChannel() {
        if (channel != null) channel.shutdown();
    }
}
