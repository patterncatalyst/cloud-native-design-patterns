package com.cndp.inventory;

import com.cndp.proto.Inventory;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.quarkus.grpc.GrpcService;
import io.smallrye.mutiny.Uni;
import org.jboss.logging.Logger;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.eclipse.microprofile.config.inject.ConfigProperty;

@GrpcService
public class InventoryService implements Inventory {

    private static final Logger LOG = Logger.getLogger(InventoryService.class);

    @ConfigProperty(name = "initial.stock", defaultValue = "100")
    int initialStock;

    private final Map<String, Integer> stock = new ConcurrentHashMap<>();

    @Override
    public Uni<ReserveReply> reserveStock(ReserveRequest request) {
        String sku = request.getSku();
        int quantity = request.getQuantity();

        LOG.infof("Reserve request: sku=%s, quantity=%d", sku, quantity);

        return Uni.createFrom().item(() -> {
            int current = stock.computeIfAbsent(sku, k -> initialStock);
            int remaining = current - quantity;

            if (remaining >= 0) {
                stock.put(sku, remaining);
                LOG.infof("Reserved %d of %s, remaining=%d", quantity, sku, remaining);
                return ReserveReply.newBuilder()
                        .setReserved(true)
                        .setRemaining(remaining)
                        .build();
            } else {
                LOG.infof("Insufficient stock for %s: requested=%d, available=%d", sku, quantity, current);
                return ReserveReply.newBuilder()
                        .setReserved(false)
                        .setRemaining(current)
                        .build();
            }
        });
    }
}
