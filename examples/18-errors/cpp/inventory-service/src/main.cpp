#include <grpcpp/grpcpp.h>
#include <inventory.grpc.pb.h>
#include <spdlog/spdlog.h>
#include <unordered_map>
#include <mutex>
#include <memory>

class InventoryServiceImpl final : public inventory::InventoryService::Service {
private:
    std::unordered_map<std::string, int> stock_;
    std::mutex mutex_;

public:
    InventoryServiceImpl() {
        // Pre-seed limited stock
        stock_["limited"] = 5;
    }

    grpc::Status ReserveStock(grpc::ServerContext* context,
                              const inventory::ReserveRequest* request,
                              inventory::ReserveResponse* response) override {
        std::lock_guard<std::mutex> lock(mutex_);

        const std::string& sku = request->sku();
        int quantity = request->quantity();

        spdlog::info("ReserveStock called: sku={}, quantity={}", sku, quantity);

        // Check if SKU exists in stock map
        auto it = stock_.find(sku);

        if (it != stock_.end()) {
            // SKU exists - check if we have enough
            int available = it->second;

            if (available >= quantity) {
                // Reserve the stock
                it->second -= quantity;
                response->set_confirmed(true);
                response->set_remaining(it->second);
                spdlog::info("Stock reserved: sku={}, remaining={}", sku, it->second);
            } else {
                // Insufficient stock
                response->set_confirmed(false);
                response->set_remaining(available);
                spdlog::warn("Insufficient stock: sku={}, requested={}, available={}",
                           sku, quantity, available);
            }
        } else {
            // Unknown SKU - treat as unlimited stock
            response->set_confirmed(true);
            response->set_remaining(9999);
            spdlog::info("Unknown SKU (unlimited): sku={}", sku);
        }

        return grpc::Status::OK;
    }
};

void RunServer() {
    std::string server_address("0.0.0.0:50051");
    InventoryServiceImpl service;

    grpc::ServerBuilder builder;
    builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
    builder.RegisterService(&service);

    std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
    spdlog::info("Inventory service listening on {}", server_address);
    server->Wait();
}

int main() {
    spdlog::set_level(spdlog::level::info);
    RunServer();
    return 0;
}
