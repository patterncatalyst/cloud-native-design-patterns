package com.cndp.inventory;

import com.cndp.proto.InventoryService;
import com.cndp.proto.ReserveReply;
import com.cndp.proto.ReserveRequest;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.quarkus.grpc.GrpcService;
import io.smallrye.mutiny.Uni;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.jboss.logging.Logger;

import java.util.concurrent.ConcurrentHashMap;

@GrpcService
public class InventoryGrpcService implements InventoryService {

    private static final Logger log = Logger.getLogger(InventoryGrpcService.class);

    private final ConcurrentHashMap<String, Integer> stock = new ConcurrentHashMap<>();

    @ConfigProperty(name = "initial.stock", defaultValue = "100")
    int initialStock;

    @Inject
    MeterRegistry meterRegistry;

    @Override
    public Uni<ReserveReply> reserveStock(ReserveRequest request) {
        String sku = request.getSku();
        int qty = request.getQuantity();

        stock.putIfAbsent(sku, initialStock);

        int remaining = stock.get(sku) - qty;
        boolean confirmed;
        if (remaining >= 0) {
            stock.put(sku, remaining);
            confirmed = true;
            log.infof("reserved sku=%s qty=%d remaining=%d", sku, qty, remaining);
        } else {
            confirmed = false;
            remaining = stock.get(sku);
            log.warnf("insufficient stock sku=%s requested=%d available=%d", sku, qty, remaining);
        }

        Counter.builder("stock.reservations")
                .description("Number of stock reservation attempts")
                .tag("sku", sku)
                .tag("confirmed", String.valueOf(confirmed))
                .register(meterRegistry)
                .increment();

        return Uni.createFrom().item(ReserveReply.newBuilder()
                .setConfirmed(confirmed)
                .setRemaining(remaining)
                .build());
    }
}
