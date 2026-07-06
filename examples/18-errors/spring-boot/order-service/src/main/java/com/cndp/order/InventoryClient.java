package com.cndp.order;

import com.cndp.proto.InventoryGrpc;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

@Component
public class InventoryClient {

    private static final Logger log = LoggerFactory.getLogger(InventoryClient.class);

    @Value("${inventory.addr}")
    private String inventoryAddr;

    @Value("${grpc.deadline.ms}")
    private long deadlineMs;

    private ManagedChannel channel;
    private InventoryGrpc.InventoryBlockingStub stub;

    @PostConstruct
    public void init() {
        String[] parts = inventoryAddr.split(":");
        String host = parts[0];
        int port = Integer.parseInt(parts[1]);

        log.info("connecting to inventory at {}:{}", host, port);
        channel = ManagedChannelBuilder.forAddress(host, port)
                .usePlaintext()
                .build();
        stub = InventoryGrpc.newBlockingStub(channel);
    }

    @PreDestroy
    public void shutdown() {
        if (channel != null) {
            channel.shutdown();
        }
    }

    public ReserveReply reserveStock(String sku, int quantity) {
        ReserveRequest request = ReserveRequest.newBuilder()
                .setSku(sku)
                .setQuantity(quantity)
                .build();

        return stub.withDeadlineAfter(deadlineMs, TimeUnit.MILLISECONDS)
                .reserveStock(request);
    }
}
