package com.cndp.order;

import io.quarkus.runtime.Quarkus;
import io.quarkus.runtime.annotations.QuarkusMain;

/**
 * One entry point, two driving adapters. Without arguments the HTTP service runs; with arguments
 * (cli-place-order starts the jar under the "cli" profile, which turns the HTTP server off) the
 * CLI adapter runs the same use case and exits.
 */
@QuarkusMain
public class OrderServiceApp {

    public static void main(String... args) {
        if (args.length > 0) {
            Quarkus.run(CliPlaceOrder.class, args);
        } else {
            Quarkus.run(args);
        }
    }
}
