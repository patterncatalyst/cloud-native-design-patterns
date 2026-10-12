package com.cndp.order;

import java.util.concurrent.TimeUnit;

import com.cndp.proto.InventoryGrpc;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class InventoryClient {

    private static final Logger log = LoggerFactory.getLogger(InventoryClient.class);

    private final ManagedChannel channel;
    private final InventoryGrpc.InventoryBlockingStub stub;
    private final long deadlineMs;

    public InventoryClient(InventoryProperties properties) {
        String[] parts = properties.addr().split(":");
        log.info("connecting to inventory at {}:{}", parts[0], parts[1]);
        this.channel = ManagedChannelBuilder.forAddress(parts[0], Integer.parseInt(parts[1]))
                .usePlaintext()
                .build();
        this.stub = InventoryGrpc.newBlockingStub(channel);
        this.deadlineMs = properties.deadlineMs();
    }

    @PreDestroy
    public void shutdown() {
        channel.shutdown();
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
