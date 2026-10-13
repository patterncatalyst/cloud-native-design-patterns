package com.cndp.order;

import com.cndp.proto.InventoryGrpc;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.grpc.client.GrpcChannelFactory;

@SpringBootApplication
public class OrderServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(OrderServiceApplication.class, args);
    }

    /** The "inventory" channel comes from spring.grpc.client.channel.inventory.target; Spring gRPC owns its lifecycle. */
    @Bean
    InventoryGrpc.InventoryBlockingStub inventoryStub(GrpcChannelFactory channels) {
        return InventoryGrpc.newBlockingStub(channels.createChannel("inventory"));
    }
}
