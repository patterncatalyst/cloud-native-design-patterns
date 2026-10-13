package com.cndp.gateway;

import com.cndp.proto.InventoryGrpc;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.grpc.client.GrpcChannelFactory;
import org.springframework.web.client.RestClient;

@SpringBootApplication
public class GatewayApplication {

    @Value("${orderapi.url}")
    private String orderApiUrl;

    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }

    /** The "inventory" channel comes from spring.grpc.client.channel.inventory.target; Spring gRPC owns its lifecycle. */
    @Bean
    InventoryGrpc.InventoryBlockingStub inventoryStub(GrpcChannelFactory channels) {
        return InventoryGrpc.newBlockingStub(channels.createChannel("inventory"));
    }

    @Bean
    public RestClient orderApiClient() {
        return RestClient.builder()
                .baseUrl(orderApiUrl)
                .build();
    }
}
