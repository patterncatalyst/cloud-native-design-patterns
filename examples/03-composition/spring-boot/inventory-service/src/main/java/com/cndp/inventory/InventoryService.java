package com.cndp.inventory;

import java.util.Map;

import com.cndp.proto.GetStockBatchReply;
import com.cndp.proto.GetStockBatchRequest;
import com.cndp.proto.GetStockReply;
import com.cndp.proto.GetStockRequest;
import com.cndp.proto.InventoryGrpc;
import io.grpc.stub.StreamObserver;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.grpc.server.service.GrpcService;

@GrpcService
public class InventoryService extends InventoryGrpc.InventoryImplBase {

    private static final Logger log = LoggerFactory.getLogger(InventoryService.class);

    private static final Map<String, Integer> STOCK = Map.of(
            "widget-a", 42,
            "widget-b", 17,
            "gadget-x", 100,
            "gadget-y", 0
    );

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
