#include <fmt/ranges.h>
#include <grpcpp/grpcpp.h>
#include <spdlog/spdlog.h>
#include "inventory.grpc.pb.h"
#include <unordered_map>
#include <atomic>

static std::unordered_map<std::string, int> g_stock = {
    {"widget-a", 42},
    {"widget-b", 17},
    {"gadget-x", 100},
    {"gadget-y", 0},
};
static std::atomic<int> g_call_count{0};

class InventoryServiceImpl final : public inventory::Inventory::Service {
    grpc::Status GetStock(grpc::ServerContext*,
                          const inventory::GetStockRequest* req,
                          inventory::GetStockReply* reply) override {
        int count = ++g_call_count;
        auto it = g_stock.find(req->sku());
        int available = (it != g_stock.end()) ? it->second : 0;
        reply->set_sku(req->sku());
        reply->set_available(available);
        spdlog::info("GetStock sku={} available={} (call #{})", req->sku(), available, count);
        return grpc::Status::OK;
    }

    grpc::Status GetStockBatch(grpc::ServerContext*,
                               const inventory::GetStockBatchRequest* req,
                               inventory::GetStockBatchReply* reply) override {
        int count = ++g_call_count;
        for (const auto& sku : req->skus()) {
            auto* item = reply->add_items();
            item->set_sku(sku);
            auto it = g_stock.find(sku);
            item->set_available((it != g_stock.end()) ? it->second : 0);
        }
        spdlog::info("GetStockBatch skus=[{}] (call #{})", fmt::join(req->skus(), ", "), count);
        return grpc::Status::OK;
    }
};

int main() {
    std::string addr("0.0.0.0:50051");
    InventoryServiceImpl service;
    grpc::ServerBuilder builder;
    builder.AddListeningPort(addr, grpc::InsecureServerCredentials());
    builder.RegisterService(&service);
    auto server = builder.BuildAndStart();
    spdlog::info("inventory gRPC server listening on {}", addr);
    server->Wait();
    return 0;
}
