package com.cndp.order;

import java.util.concurrent.TimeUnit;

import com.cndp.proto.InventoryGrpc;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.grpc.StatusRuntimeException;
import io.quarkus.grpc.GrpcClient;
import io.quarkus.logging.Log;
import jakarta.enterprise.context.ApplicationScoped;
import org.eclipse.microprofile.config.inject.ConfigProperty;

@ApplicationScoped
public class InventoryClient {

    @GrpcClient("inventory")
    InventoryGrpc.InventoryBlockingStub stub;

    @ConfigProperty(name = "grpc.deadline.ms", defaultValue = "3000")
    long deadlineMs;

    /** Calls inventory and translates gRPC failures into ProblemException. */
    public ReserveReply reserveStock(String sku, int quantity) {
        ReserveRequest request = ReserveRequest.newBuilder()
                .setSku(sku)
                .setQuantity(quantity)
                .build();
        try {
            return stub.withDeadlineAfter(deadlineMs, TimeUnit.MILLISECONDS)
                    .reserveStock(request);
        } catch (StatusRuntimeException e) {
            throw toProblem(e, sku);
        }
    }

    private ProblemException toProblem(StatusRuntimeException e, String sku) {
        return switch (e.getStatus().getCode()) {
            case RESOURCE_EXHAUSTED -> {
                String detail = e.getStatus().getDescription();
                if (detail == null) {
                    detail = "insufficient stock for " + sku;
                }
                yield new ProblemException(409, "STOCK_UNAVAILABLE",
                        "insufficient stock for " + sku, detail, false, null);
            }
            case DEADLINE_EXCEEDED, UNAVAILABLE -> new ProblemException(503, "INVENTORY_UNAVAILABLE",
                    "inventory service is temporarily unavailable",
                    "gRPC " + e.getStatus().getCode().name().toLowerCase(), true, 5);
            default -> {
                Log.errorf(e, "unexpected gRPC error from inventory: status=%s desc=%s",
                        e.getStatus().getCode(), e.getStatus().getDescription());
                yield new ProblemException(500, "INTERNAL_ERROR",
                        "unexpected error from inventory service",
                        e.getStatus().getDescription(), false, null);
            }
        };
    }
}
