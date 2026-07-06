package com.cndp.inventory;

import java.util.concurrent.ConcurrentHashMap;

import com.cndp.proto.InventoryServiceGrpc;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.grpc.Server;
import io.grpc.ServerBuilder;
import io.grpc.ServerInterceptors;
import io.grpc.stub.StreamObserver;
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.common.AttributeKey;
import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.metrics.LongCounter;
import io.opentelemetry.api.metrics.Meter;
import io.opentelemetry.instrumentation.grpc.v1_6.GrpcTelemetry;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class InventoryServiceApplication extends InventoryServiceGrpc.InventoryServiceImplBase implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(InventoryServiceApplication.class);

    private final ConcurrentHashMap<String, Integer> stock = new ConcurrentHashMap<>();
    private final OpenTelemetry openTelemetry;

    @Value("${inventory.initial-stock}")
    private int initialStock;

    @Value("${grpc.port}")
    private int grpcPort;

    private Server server;
    private LongCounter stockReservationsCounter;

    public InventoryServiceApplication(OpenTelemetry openTelemetry) {
        this.openTelemetry = openTelemetry;
    }

    public static void main(String[] args) {
        SpringApplication.run(InventoryServiceApplication.class, args);
    }

    @Override
    public void run(String... args) throws Exception {
        Meter meter = openTelemetry.getMeter("inventory-service");
        stockReservationsCounter = meter.counterBuilder("stock.reservations")
                .setDescription("Number of stock reservation attempts")
                .build();

        GrpcTelemetry grpcTelemetry = GrpcTelemetry.create(openTelemetry);

        server = ServerBuilder.forPort(grpcPort)
                .addService(ServerInterceptors.intercept(this, grpcTelemetry.newServerInterceptor()))
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
