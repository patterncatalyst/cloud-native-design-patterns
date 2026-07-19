package com.cndp.inventory;

import com.cndp.proto.GetStockBatchReply;
import com.cndp.proto.GetStockBatchRequest;
import com.cndp.proto.GetStockReply;
import com.cndp.proto.GetStockRequest;
import com.cndp.proto.Inventory;
import io.quarkus.grpc.GrpcService;
import io.smallrye.mutiny.Uni;

import java.util.Map;
import java.util.logging.Logger;

@GrpcService
public class InventoryService implements Inventory {

    private static final Logger log = Logger.getLogger(InventoryService.class.getName());

    private static final Map<String, Integer> STOCK = Map.of(
        "widget-a", 42,
        "widget-b", 17,
        "gadget-x", 100,
        "gadget-y", 0
    );

    @Override
    public Uni<GetStockReply> getStock(GetStockRequest request) {
        String sku = request.getSku();
        int available = STOCK.getOrDefault(sku, 0);
        log.info("GetStock: " + sku + " -> " + available);
        return Uni.createFrom().item(GetStockReply.newBuilder()
                .setSku(sku)
                .setAvailable(available)
                .build());
    }

    @Override
    public Uni<GetStockBatchReply> getStockBatch(GetStockBatchRequest request) {
        log.info("GetStockBatch: " + request.getSkusCount() + " SKUs");
        GetStockBatchReply.Builder replyBuilder = GetStockBatchReply.newBuilder();
        for (String sku : request.getSkusList()) {
            int available = STOCK.getOrDefault(sku, 0);
            replyBuilder.addItems(GetStockReply.newBuilder()
                    .setSku(sku)
                    .setAvailable(available)
                    .build());
        }
        return Uni.createFrom().item(replyBuilder.build());
    }
}
