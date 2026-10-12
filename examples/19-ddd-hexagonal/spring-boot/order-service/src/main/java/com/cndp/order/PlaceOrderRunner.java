package com.cndp.order;

import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.ExitCodeGenerator;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

import com.cndp.order.domain.Order;
import com.cndp.order.domain.OrderRepository;
import com.cndp.order.domain.PlaceOrderCmd;
import com.cndp.order.domain.PlaceOrderUseCase;

/** Places one order from the command line: {@code CliPlaceOrder <sku> <quantity>}. Output goes to stdout. */
@Component
@Profile("cli")
class PlaceOrderRunner implements ApplicationRunner, ExitCodeGenerator {

    private final OrderRepository repo;
    private int exitCode;

    PlaceOrderRunner(OrderRepository repo) {
        this.repo = repo;
    }

    @Override
    public void run(ApplicationArguments args) {
        var operands = args.getNonOptionArgs();
        if (operands.size() < 2) {
            System.err.println("Usage: CliPlaceOrder <sku> <quantity>");
            exitCode = 1;
            return;
        }

        // The same use case as the REST adapter; only the event publisher differs.
        var useCase = new PlaceOrderUseCase(repo, event ->
                System.out.printf("EVENT OrderPlaced order_id=%s sku=%s%n", event.orderId(), event.sku()));

        Order order = useCase.execute(new PlaceOrderCmd(operands.get(0), Integer.parseInt(operands.get(1))));
        System.out.printf("CLI_ORDER_CREATED id=%s sku=%s qty=%d status=%s%n",
                order.id(), order.sku(), order.quantity(), order.status());
    }

    @Override
    public int getExitCode() {
        return exitCode;
    }
}
