package com.cndp.inventory;

import java.util.concurrent.ConcurrentHashMap;

import com.cndp.proto.InventoryGrpc;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.grpc.Server;
import io.grpc.ServerBuilder;
import io.grpc.stub.StreamObserver;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class InventoryServiceApplication extends InventoryGrpc.InventoryImplBase implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(InventoryServiceApplication.class);

    private final ConcurrentHashMap<String, Integer> stock = new ConcurrentHashMap<>();

    @Value("${inventory.initial-stock}")
    private int initialStock;

    @Value("${grpc.port}")
    private int grpcPort;

    private Server server;

    public static void main(String[] args) {
        SpringApplication.run(InventoryServiceApplication.class, args);
    }

    @Override
    public void run(String... args) throws Exception {
        server = ServerBuilder.forPort(grpcPort)
                .addService(this)
                .build()
                .start();
        log.info("inventory gRPC server listening on :{}", grpcPort);
        server.awaitTermination();
    }

    @PreDestroy
    public void stopGrpcServer() {
        if (server != null) server.shutdown();
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
