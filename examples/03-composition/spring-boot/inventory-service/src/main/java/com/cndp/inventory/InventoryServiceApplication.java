package com.cndp.inventory;

import java.util.Map;

import com.cndp.proto.GetStockBatchReply;
import com.cndp.proto.GetStockBatchRequest;
import com.cndp.proto.GetStockReply;
import com.cndp.proto.GetStockRequest;
import com.cndp.proto.InventoryGrpc;
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

    private static final Map<String, Integer> STOCK = Map.of(
            "widget-a", 42,
            "widget-b", 17,
            "gadget-x", 100,
            "gadget-y", 0
    );

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
    public void getStock(GetStockRequest request, StreamObserver<GetStockReply> responseObserver) {
        String sku = request.getSku();
        int available = STOCK.getOrDefault(sku, 0);
        log.info("GetStock sku={} available={}", sku, available);
        responseObserver.onNext(GetStockReply.newBuilder()
                .setSku(sku)
                .setAvailable(available)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getStockBatch(GetStockBatchRequest request, StreamObserver<GetStockBatchReply> responseObserver) {
        GetStockBatchReply.Builder builder = GetStockBatchReply.newBuilder();
        for (String sku : request.getSkusList()) {
            int available = STOCK.getOrDefault(sku, 0);
            builder.addItems(GetStockReply.newBuilder()
                    .setSku(sku)
                    .setAvailable(available)
                    .build());
        }
        log.info("GetStockBatch skus={}", request.getSkusList());
        responseObserver.onNext(builder.build());
        responseObserver.onCompleted();
    }
}
