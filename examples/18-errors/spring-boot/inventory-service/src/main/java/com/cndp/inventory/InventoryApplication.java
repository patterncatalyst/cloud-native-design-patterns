package com.cndp.inventory;

import io.grpc.Server;
import io.grpc.ServerBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class InventoryApplication implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(InventoryApplication.class);

    public static void main(String[] args) {
        SpringApplication.run(InventoryApplication.class, args);
    }

    @Override
    public void run(String... args) throws Exception {
        int initialStock = Integer.parseInt(System.getenv().getOrDefault("INITIAL_STOCK", "10"));
        String failMode = System.getenv().getOrDefault("FAIL_MODE", "none");

        log.info("inventory-service starting on :50051 (stock={}, fail_mode={})", initialStock, failMode);

        Server server = ServerBuilder.forPort(50051)
                .addService(new InventoryServiceImpl(initialStock, failMode))
                .build()
                .start();

        log.info("inventory-service started on :50051");

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            log.info("shutting down inventory-service");
            server.shutdown();
        }));

        server.awaitTermination();
    }
}
