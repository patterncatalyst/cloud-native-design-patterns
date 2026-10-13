package com.cndp.inventory;

import java.util.concurrent.ConcurrentHashMap;

import com.cndp.proto.InventoryServiceGrpc;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.grpc.stub.StreamObserver;
import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.api.common.AttributeKey;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.metrics.LongCounter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.grpc.server.service.GrpcService;

@GrpcService
public class InventoryService extends InventoryServiceGrpc.InventoryServiceImplBase {

    private static final Logger log = LoggerFactory.getLogger(InventoryService.class);

    private final ConcurrentHashMap<String, Integer> stock = new ConcurrentHashMap<>();
    private final int initialStock;
    private final LongCounter stockReservationsCounter;

    public InventoryService(@Value("${inventory.initial-stock}") int initialStock) {
        this.initialStock = initialStock;
        // The OpenTelemetry Java agent installs the global instance and instruments the gRPC server.
        this.stockReservationsCounter = GlobalOpenTelemetry.get().getMeter("inventory-service")
                .counterBuilder("stock.reservations")
                .setDescription("Number of stock reservation attempts")
                .build();
    }

    @Override
    public void reserveStock(ReserveRequest request, StreamObserver<ReserveReply> responseObserver) {
        String sku = request.getSku();
        int qty = request.getQuantity();

        stock.putIfAbsent(sku, initialStock);

        int remaining = stock.get(sku) - qty;
        boolean confirmed;
        if (remaining >= 0) {
            stock.put(sku, remaining);
            confirmed = true;
            log.info("reserved sku={} qty={} remaining={}", sku, qty, remaining);
        } else {
            confirmed = false;
            remaining = stock.get(sku);
            log.warn("insufficient stock sku={} requested={} available={}", sku, qty, remaining);
        }

        // Record custom metric
        stockReservationsCounter.add(1, Attributes.of(
                AttributeKey.stringKey("sku"), sku,
                AttributeKey.booleanKey("confirmed"), confirmed));

        responseObserver.onNext(ReserveReply.newBuilder()
                .setConfirmed(confirmed).setRemaining(remaining).build());
        responseObserver.onCompleted();
    }
}
