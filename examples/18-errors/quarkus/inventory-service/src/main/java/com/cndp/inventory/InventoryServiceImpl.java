package com.cndp.inventory;

import com.cndp.proto.Inventory;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.grpc.Status;
import io.quarkus.grpc.GrpcService;
import io.quarkus.logging.Log;
import io.smallrye.mutiny.Uni;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.time.Duration;
import java.util.concurrent.ConcurrentHashMap;

@GrpcService
public class InventoryServiceImpl implements Inventory {

    @ConfigProperty(name = "initial.stock", defaultValue = "10")
    int initialStock;

    @ConfigProperty(name = "fail.mode", defaultValue = "none")
    String failMode;

    private final ConcurrentHashMap<String, Integer> stock = new ConcurrentHashMap<>();

    @Override
    public Uni<ReserveReply> reserveStock(ReserveRequest request) {
        String sku = request.getSku();
        int quantity = request.getQuantity();

        if ("timeout".equalsIgnoreCase(failMode)) {
            Log.infof("FAIL_MODE=timeout: delaying for sku=%s", sku);
            return Uni.createFrom().item(ReserveReply.getDefaultInstance())
                    .onItem().delayIt().by(Duration.ofSeconds(10));
        }

        if ("error".equalsIgnoreCase(failMode)) {
            Log.infof("FAIL_MODE=error: throwing for sku=%s", sku);
            return Uni.createFrom().failure(
                    Status.INTERNAL.withDescription("simulated internal error").asRuntimeException());
        }

        stock.putIfAbsent(sku, initialStock);
        int current = stock.get(sku);

        if (current < quantity) {
            Log.infof("insufficient stock for sku=%s: have=%d, need=%d", sku, current, quantity);
            return Uni.createFrom().failure(
                    Status.RESOURCE_EXHAUSTED
                            .withDescription("insufficient stock for " + sku + ": have " + current + ", need " + quantity)
                            .asRuntimeException());
        }

        int remaining = stock.compute(sku, (k, v) -> {
            if (v == null || v < quantity) {
                return v;
            }
            return v - quantity;
        });

        if (remaining == current) {
            return Uni.createFrom().failure(
                    Status.RESOURCE_EXHAUSTED
                            .withDescription("insufficient stock for " + sku)
                            .asRuntimeException());
        }

        Log.infof("reserved sku=%s qty=%d remaining=%d", sku, quantity, remaining);
        return Uni.createFrom().item(
                ReserveReply.newBuilder()
                        .setReserved(true)
                        .setRemaining(remaining)
                        .build());
    }
}
