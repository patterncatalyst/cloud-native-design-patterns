// main.cpp — Composition root for the REST driving adapter.
//
// This is where we wire everything together: create the infrastructure
// (connection pool), create the adapters (repository, event publisher),
// create the use case (injecting the adapters), and register the HTTP
// handlers (injecting the use case).
//
// This is the ONLY file that knows about all the concrete types. The domain
// layer and the adapters only know about interfaces.

#include "domain/service.hpp"
#include "adapters/pg_repository.hpp"
#include "adapters/log_publisher.hpp"
#include "pg_pool.hpp"
#include <drogon/HttpAppFramework.h>
#include <spdlog/spdlog.h>
#include <cstdlib>
#include <string>

using namespace drogon;

namespace cndp::adapters {
    void register_rest_handlers(domain::PlaceOrderUseCase& use_case,
                                domain::OrderRepository& repository);
}

int main() {
    // Configure logging
    spdlog::set_level(spdlog::level::info);
    spdlog::set_pattern("[%Y-%m-%d %H:%M:%S.%e] [%^%l%$] %v");

    // Read configuration from environment
    const char* conninfo_env = std::getenv("PG_CONNINFO");
    std::string conninfo = conninfo_env ? conninfo_env
        : "postgresql://appuser:apppass@localhost:5432/appdb";

    const char* pool_size_env = std::getenv("PG_POOL_SIZE");
    std::size_t pool_size = pool_size_env ? std::stoul(pool_size_env) : 4;

    spdlog::info("Starting order-service (DDD/Hexagonal demo)");
    spdlog::info("PG_CONNINFO: {}", conninfo);
    spdlog::info("PG_POOL_SIZE: {}", pool_size);

    try {
        // Infrastructure layer: connection pool
        cndp::PgPool pool(conninfo, pool_size);
        spdlog::info("PostgreSQL connection pool ready ({} connections)", pool_size);

        // Adapters layer: concrete implementations of ports
        cndp::adapters::PgOrderRepository repository(pool);
        cndp::adapters::LogEventPublisher event_publisher;

        // Application layer: use case with injected dependencies
        cndp::domain::PlaceOrderUseCase use_case(repository, event_publisher);

        // Driving adapter: REST endpoints
        cndp::adapters::register_rest_handlers(use_case, repository);

        // Configure Drogon
        auto& drogon_app = app();
        drogon_app.setUploadPath("/tmp");
        drogon_app.addListener("0.0.0.0", 8080);
        drogon_app.setLogLevel(trantor::Logger::kInfo);
        drogon_app.setThreadNum(4);

        spdlog::info("Server listening on 0.0.0.0:8080");
        drogon_app.run();

    } catch (const std::exception& e) {
        spdlog::error("Startup failed: {}", e.what());
        return 1;
    }

    return 0;
}
