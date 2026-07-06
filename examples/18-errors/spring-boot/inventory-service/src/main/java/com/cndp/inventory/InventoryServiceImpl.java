package com.cndp.inventory;

import com.cndp.proto.InventoryGrpc;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.grpc.Status;
import io.grpc.stub.StreamObserver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.ConcurrentHashMap;

public class InventoryServiceImpl extends InventoryGrpc.InventoryImplBase {

    private static final Logger log = LoggerFactory.getLogger(InventoryServiceImpl.class);

    private final int initialStock;
    private final String failMode;
    private final ConcurrentHashMap<String, Integer> stock = new ConcurrentHashMap<>();

    public InventoryServiceImpl(int initialStock, String failMode) {
        this.initialStock = initialStock;
        this.failMode = failMode;
    }

    @Override
    public void reserveStock(ReserveRequest request, StreamObserver<ReserveReply> responseObserver) {
        String sku = request.getSku();
        int quantity = request.getQuantity();

        // Handle fail modes
        if ("timeout".equalsIgnoreCase(failMode)) {
            log.info("FAIL_MODE=timeout: sleeping 10s for sku={}", sku);
            try {
                Thread.sleep(10000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                responseObserver.onError(
                        Status.INTERNAL.withDescription("interrupted during timeout simulation").asRuntimeException());
                return;
            }
        }

        if ("error".equalsIgnoreCase(failMode)) {
            log.info("FAIL_MODE=error: throwing for sku={}", sku);
            responseObserver.onError(
                    Status.INTERNAL.withDescription("simulated internal error").asRuntimeException());
            return;
        }

        // Initialize stock for sku if not present
        stock.putIfAbsent(sku, initialStock);

        int current = stock.get(sku);
        if (current < quantity) {
            log.info("insufficient stock for sku={}: have={}, need={}", sku, current, quantity);
            responseObserver.onError(
                    Status.RESOURCE_EXHAUSTED
                            .withDescription("insufficient stock for " + sku + ": have " + current + ", need " + quantity)
                            .asRuntimeException());
            return;
        }

        int remaining = stock.compute(sku, (k, v) -> {
            if (v == null || v < quantity) {
                return v;
            }
            return v - quantity;
        });

        // Check if compute actually decremented (race condition guard)
        if (remaining == current) {
            responseObserver.onError(
                    Status.RESOURCE_EXHAUSTED
                            .withDescription("insufficient stock for " + sku)
                            .asRuntimeException());
            return;
        }

        log.info("reserved sku={} qty={} remaining={}", sku, quantity, remaining);
        responseObserver.onNext(ReserveReply.newBuilder()
                .setReserved(true)
                .setRemaining(remaining)
                .build());
        responseObserver.onCompleted();
    }
}
