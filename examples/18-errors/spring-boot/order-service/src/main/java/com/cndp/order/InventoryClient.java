package com.cndp.order;

import java.util.concurrent.TimeUnit;

import com.cndp.proto.InventoryGrpc;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import org.springframework.grpc.client.GrpcChannelFactory;
import org.springframework.stereotype.Component;

@Component
public class InventoryClient {

    private final InventoryGrpc.InventoryBlockingStub stub;
    private final long deadlineMs;

    /** The "inventory" channel comes from spring.grpc.client.channel.inventory.target; Spring gRPC owns it. */
    public InventoryClient(GrpcChannelFactory channels, InventoryProperties properties) {
        this.stub = InventoryGrpc.newBlockingStub(channels.createChannel("inventory"));
        this.deadlineMs = properties.deadlineMs();
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
