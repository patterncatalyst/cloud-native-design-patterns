package com.cndp.inventory;

import java.util.concurrent.ConcurrentHashMap;

import com.cndp.proto.InventoryGrpc;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.grpc.stub.StreamObserver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.grpc.server.service.GrpcService;

@GrpcService
public class InventoryService extends InventoryGrpc.InventoryImplBase {

    private static final Logger log = LoggerFactory.getLogger(InventoryService.class);

    private final ConcurrentHashMap<String, Integer> stock = new ConcurrentHashMap<>();
    private final int initialStock;

    public InventoryService(@Value("${inventory.initial-stock}") int initialStock) {
        this.initialStock = initialStock;
    }

    @Override
    public void reserveStock(ReserveRequest request, StreamObserver<ReserveReply> responseObserver) {
        String sku = request.getSku();
        int qty = request.getQuantity();

        stock.putIfAbsent(sku, initialStock);

        int remaining = stock.get(sku) - qty;
        if (remaining >= 0) {
            stock.put(sku, remaining);
            log.info("reserved sku={} qty={} remaining={}", sku, qty, remaining);
            responseObserver.onNext(ReserveReply.newBuilder()
                    .setReserved(true).setRemaining(remaining).build());
        } else {
            log.warn("insufficient stock sku={} requested={} available={}", sku, qty, stock.get(sku));
            responseObserver.onNext(ReserveReply.newBuilder()
                    .setReserved(false).setRemaining(stock.get(sku)).build());
        }
        responseObserver.onCompleted();
    }
}
