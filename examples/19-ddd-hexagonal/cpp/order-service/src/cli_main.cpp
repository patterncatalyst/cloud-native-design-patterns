// cli_main.cpp — CLI driving adapter entry point.
//
// Demonstrates replaceability: the SAME use case, driven by a different
// adapter (command line instead of HTTP). The CLI adapter and the REST
// adapter both depend on PlaceOrderUseCase, proving the hexagonal architecture
// works — the core is independent of its delivery mechanism.

#include "domain/service.hpp"
#include "adapters/pg_repository.hpp"
#include "adapters/log_publisher.hpp"
#include "pg_pool.hpp"
#include <iostream>
#include <cstdlib>
#include <string>

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr << "Usage: cli-place-order <sku> <quantity>\n";
        return 1;
    }

    std::string sku = argv[1];
    int quantity = std::stoi(argv[2]);

    // Read configuration from environment
    const char* conninfo_env = std::getenv("PG_CONNINFO");
    std::string conninfo = conninfo_env ? conninfo_env
        : "postgresql://appuser:apppass@localhost:5432/appdb";

    const char* pool_size_env = std::getenv("PG_POOL_SIZE");
    std::size_t pool_size = pool_size_env ? std::stoul(pool_size_env) : 1;

    try {
        // Infrastructure layer: connection pool (just 1 conn for CLI)
        cndp::PgPool pool(conninfo, pool_size);

        // Adapters layer: concrete implementations of ports
        cndp::adapters::PgOrderRepository repository(pool);
        cndp::adapters::LogEventPublisher event_publisher;

        // Application layer: use case with injected dependencies
        cndp::domain::PlaceOrderUseCase use_case(repository, event_publisher);

        // Execute the use case
        cndp::domain::PlaceOrderCmd cmd;
        cmd.sku = sku;
        cmd.quantity = quantity;

        auto order = use_case.execute(cmd);

        // Output in the format expected by verify.sh
        std::cout << "CLI_ORDER_CREATED id=" << order.id
                  << " sku=" << order.sku
                  << " qty=" << order.quantity << "\n";

        return 0;

    } catch (const std::invalid_argument& e) {
        std::cerr << "Validation error: " << e.what() << "\n";
        return 1;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
}
