package com.cndp.order;

import jakarta.enterprise.context.Dependent;
import jakarta.inject.Inject;

import com.cndp.order.domain.Order;
import com.cndp.order.domain.PlaceOrderCmd;
import com.cndp.order.domain.PlaceOrderUseCase;
import io.quarkus.runtime.QuarkusApplication;

/** CLI driving adapter: the same use case and the same Panache repository as the REST adapter. */
@Dependent
public class CliPlaceOrder implements QuarkusApplication {

    @Inject
    PlaceOrderUseCase useCase;

    @Override
    public int run(String... args) {
        if (args.length < 2) {
            System.err.println("Usage: cli-place-order <sku> <quantity>");
            return 1;
        }

        Order order = useCase.execute(new PlaceOrderCmd(args[0], Integer.parseInt(args[1])));
        System.out.printf("CLI_ORDER_CREATED id=%s sku=%s qty=%d status=%s%n",
                order.id(), order.sku(), order.quantity(), order.status());
        return 0;
    }
}
