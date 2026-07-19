package com.cndp.order;

import com.cndp.proto.InventoryGrpc;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.quarkus.grpc.GrpcClient;
import jakarta.enterprise.context.ApplicationScoped;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.util.concurrent.TimeUnit;

@ApplicationScoped
public class InventoryClient {

    @GrpcClient("inventory")
    InventoryGrpc.InventoryBlockingStub stub;

    @ConfigProperty(name = "grpc.deadline.ms", defaultValue = "3000")
    long deadlineMs;

    public ReserveReply reserveStock(String sku, int quantity) {
        ReserveRequest request = ReserveRequest.newBuilder()
                .setSku(sku)
                .setQuantity(quantity)
                .build();
        return stub.withDeadlineAfter(deadlineMs, TimeUnit.MILLISECONDS)
                .reserveStock(request);
    }
}
