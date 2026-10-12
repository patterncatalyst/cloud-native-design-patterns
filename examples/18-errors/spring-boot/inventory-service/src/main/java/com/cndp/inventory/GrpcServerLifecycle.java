package com.cndp.inventory;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

import io.grpc.Server;
import io.grpc.ServerBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.SmartLifecycle;
import org.springframework.stereotype.Component;

/** Starts the gRPC server with the application context and drains it on shutdown. */
@Component
class GrpcServerLifecycle implements SmartLifecycle {

    private static final Logger log = LoggerFactory.getLogger(GrpcServerLifecycle.class);
    private static final int PORT = 50051;

    private final InventoryProperties properties;
    private Server server;

    GrpcServerLifecycle(InventoryProperties properties) {
        this.properties = properties;
    }

    @Override
    public void start() {
        log.info("inventory-service starting on :{} (stock={}, fail_mode={})",
                PORT, properties.initialStock(), properties.failMode());
        try {
            server = ServerBuilder.forPort(PORT)
                    .addService(new InventoryServiceImpl(properties.initialStock(), properties.failMode()))
                    .build()
                    .start();
        } catch (IOException e) {
            throw new IllegalStateException("cannot start the gRPC server on :" + PORT, e);
        }
        log.info("inventory-service started on :{}", PORT);
    }

    @Override
    public void stop() {
        log.info("shutting down inventory-service");
        server.shutdown();
        try {
            server.awaitTermination(5, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    @Override
    public boolean isRunning() {
        return server != null && !server.isShutdown();
    }
}
